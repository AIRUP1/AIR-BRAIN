import hashlib
import hmac
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from air_agents_api.config import Settings
from air_agents_api.main import create_app
from air_agents_api.repository import Repository

ADMIN_KEY = "admin-secret-key-that-is-long-enough"
OPERATOR_KEY = "operator-secret-key-that-is-long-enough"
VIEWER_KEY = "viewer-secret-key-that-is-long-enough"
GITHUB_WEBHOOK_SECRET = "github-webhook-secret-that-is-long-enough"


@pytest.fixture()
def client(tmp_path: Path):
    settings = Settings(
        environment="test",
        database_path=str(tmp_path / "air_agents_test.db"),
        api_keys={ADMIN_KEY: "admin", OPERATOR_KEY: "operator", VIEWER_KEY: "viewer"},
        cors_origins=["https://airagentsllc.co"],
        github_webhook_secret=GITHUB_WEBHOOK_SECRET,
        workspace_ui_session_secret="workspace-ui-session-secret-that-is-long-enough",
        enable_public_intake=True,
    )
    app = create_app(settings=settings, repository=Repository(settings.database_path))
    with TestClient(app) as test_client:
        yield test_client


def auth(key: str = OPERATOR_KEY) -> dict[str, str]:
    return {"X-API-Key": key}


def public_lead() -> dict:
    return {
        "full_name": "Jordan Taylor",
        "email": "jordan@example.com",
        "company": "Taylor Studio",
        "service_interest": "creative_launchpad",
        "message": "We want a campaign system.",
        "consent_to_contact": True,
    }


def github_delivery_headers(raw_body: bytes, *, delivery_id: str = "delivery-123") -> dict[str, str]:
    signature = "sha256=" + hmac.new(GITHUB_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-GitHub-Delivery": delivery_id,
        "X-GitHub-Event": "push",
        "X-Hub-Signature-256": signature,
    }


def test_health_and_docs_are_public(client: TestClient):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200
    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["x-request-id"]


def test_public_intake_captures_consent_aware_lead(client: TestClient):
    response = client.post("/v1/public/lead-intake", json=public_lead())
    assert response.status_code == 201
    assert "received" in response.json()["message"].lower()

    leads = client.get("/v1/workspace/leads", headers=auth(VIEWER_KEY))
    assert leads.status_code == 200
    payload = leads.json()
    assert payload["total"] == 1
    assert payload["items"][0]["email"] == "jordan@example.com"
    assert payload["items"][0]["consent_to_contact"] is True


def test_public_intake_requires_explicit_consent(client: TestClient):
    data = public_lead()
    data["consent_to_contact"] = False
    response = client.post("/v1/public/lead-intake", json=data)
    assert response.status_code == 422


def test_workspace_requires_api_key_and_enforces_roles(client: TestClient):
    assert client.get("/v1/workspace/leads").status_code == 401
    assert client.get("/v1/workspace/leads", headers={"X-API-Key": "wrong"}).status_code == 401

    payload = {"title": "Contact new lead"}
    forbidden = client.post("/v1/workspace/tasks", json=payload, headers=auth(VIEWER_KEY))
    assert forbidden.status_code == 403


def test_workspace_crud_and_audit_trail(client: TestClient):
    created = client.post(
        "/v1/workspace/partners",
        json={"name": "Northstar Studio", "category": "creative_partner", "status": "active"},
        headers=auth(),
    )
    assert created.status_code == 201
    partner = created.json()

    updated = client.patch(
        f"/v1/workspace/partners/{partner['id']}",
        json={"status": "paused", "notes": "Review in Q4."},
        headers=auth(),
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "paused"

    audit = client.get("/v1/workspace/audit-events", headers=auth(ADMIN_KEY))
    assert audit.status_code == 200
    assert audit.json()["total"] == 2
    assert {event["action"] for event in audit.json()["items"]} == {"created", "updated"}


def test_lending_case_remains_coordination_only(client: TestClient):
    response = client.post(
        "/v1/workspace/lending-cases",
        json={
            "business_name": "Taylor Studio LLC",
            "contact_name": "Jordan Taylor",
            "email": "jordan@example.com",
            "funding_goal": "Equipment and working capital readiness",
            "requested_amount": 25000,
            "authorized_partner_contact": True,
        },
        headers=auth(),
    )
    assert response.status_code == 201
    case = response.json()
    assert case["readiness_status"] == "intake"
    assert "decision" not in json.dumps(case).lower()


def test_campaign_channels_round_trip(client: TestClient):
    response = client.post(
        "/v1/workspace/campaign-briefs",
        json={
            "title": "Fall launch",
            "objective": "Drive qualified discovery calls.",
            "audience": "Founder-led service businesses.",
            "primary_message": "Production-ready AI operating systems.",
            "channels": ["web", "linkedin"],
        },
        headers=auth(),
    )
    assert response.status_code == 201
    assert response.json()["channels"] == ["web", "linkedin"]


def test_honeypot_returns_nonconfirming_success(client: TestClient):
    data = public_lead()
    data["website"] = "https://spam.example"
    response = client.post("/v1/public/lead-intake", json=data)
    assert response.status_code == 201
    leads = client.get("/v1/workspace/leads", headers=auth(VIEWER_KEY))
    assert leads.json()["total"] == 0


def test_preview_mode_blocks_public_intake(tmp_path: Path):
    settings = Settings(
        environment="preview",
        database_path=str(tmp_path / "preview.db"),
        api_keys={},
        cors_origins=["https://airagentsllc.co"],
        enable_public_intake=False,
    )
    app = create_app(settings=settings, repository=Repository(settings.database_path))
    with TestClient(app) as preview_client:
        response = preview_client.post("/v1/public/lead-intake", json=public_lead())
    assert response.status_code == 503


def test_github_webhook_verifies_signature_and_deduplicates_deliveries(client: TestClient):
    raw_body = json.dumps(
        {
            "action": "completed",
            "repository": {"full_name": "AIRUP1/AIR-BRAIN"},
            "installation": {"id": 132782399},
        },
        separators=(",", ":"),
    ).encode()
    headers = github_delivery_headers(raw_body)

    accepted = client.post("/v1/webhooks/github", content=raw_body, headers=headers)
    assert accepted.status_code == 202
    assert accepted.json() == {"delivery_id": "delivery-123", "event": "push", "duplicate": False}

    duplicate = client.post("/v1/webhooks/github", content=raw_body, headers=headers)
    assert duplicate.status_code == 202
    assert duplicate.json()["duplicate"] is True

    audit = client.get("/v1/workspace/audit-events", headers=auth(ADMIN_KEY))
    assert audit.json()["total"] == 1
    assert audit.json()["items"][0]["action"] == "github_webhook_received"
    assert "payload_sha256" in audit.json()["items"][0]["metadata"]


def test_github_webhook_rejects_unsigned_or_invalid_deliveries(client: TestClient):
    raw_body = b'{"action":"opened"}'
    missing_signature = client.post(
        "/v1/webhooks/github",
        content=raw_body,
        headers={"X-GitHub-Delivery": "delivery-missing", "X-GitHub-Event": "issues"},
    )
    assert missing_signature.status_code == 401

    invalid_signature = client.post(
        "/v1/webhooks/github",
        content=raw_body,
        headers={
            "X-GitHub-Delivery": "delivery-invalid",
            "X-GitHub-Event": "issues",
            "X-Hub-Signature-256": "sha256=" + "0" * 64,
        },
    )
    assert invalid_signature.status_code == 401


def test_github_webhook_requires_valid_json_after_signature_verification(client: TestClient):
    raw_body = b"not-json"
    response = client.post("/v1/webhooks/github", content=raw_body, headers=github_delivery_headers(raw_body))
    assert response.status_code == 400


def test_github_webhook_is_disabled_without_a_configured_secret(tmp_path: Path):
    settings = Settings(
        environment="preview",
        database_path=str(tmp_path / "webhook-preview.db"),
        api_keys={},
        cors_origins=["https://airagentsllc.co"],
        enable_public_intake=False,
    )
    app = create_app(settings=settings, repository=Repository(settings.database_path))
    with TestClient(app) as preview_client:
        response = preview_client.post("/v1/webhooks/github", content=b"{}")
    assert response.status_code == 503


def create_investor_blueprint(client: TestClient) -> dict:
    response = client.post(
        "/v1/workspace/investor-blueprints",
        json={"title": "AIR AGENTS Investor Blueprint", "as_of_date": "2026-09-27", "currency": "USD"},
        headers=auth(ADMIN_KEY),
    )
    assert response.status_code == 201
    return response.json()


def create_investor_kpi(client: TestClient, blueprint_id: str, **overrides: object) -> dict:
    payload = {
        "category": "revenue",
        "label": "Monthly recurring revenue",
        "actual_value": 90000,
        "target_value": 100000,
        "unit": "currency",
        "owner": "Jordan Taylor",
        "target_date": "2026-12-31",
    }
    payload.update(overrides)
    response = client.post(
        f"/v1/workspace/investor-blueprints/{blueprint_id}/kpis",
        json=payload,
        headers=auth(ADMIN_KEY),
    )
    assert response.status_code == 201
    return response.json()


def test_investor_blueprint_calculates_kpi_progress_and_enforces_admin_edits(client: TestClient):
    blueprint = create_investor_blueprint(client)
    revenue = create_investor_kpi(client, blueprint["id"])
    retention = create_investor_kpi(
        client,
        blueprint["id"],
        category="retention",
        label="Net revenue retention",
        actual_value=68,
        target_value=90,
        unit="percent",
        owner="Avery Morgan",
    )
    growth = create_investor_kpi(
        client,
        blueprint["id"],
        category="growth",
        label="Enterprise pipeline",
        actual_value=12,
        target_value=12,
        unit="count",
        owner="Riley Chen",
    )

    snapshot = client.get(f"/v1/workspace/investor-blueprints/{blueprint['id']}", headers=auth(VIEWER_KEY))
    assert snapshot.status_code == 200
    kpis = {kpi["id"]: kpi for kpi in snapshot.json()["kpis"]}
    assert kpis[revenue["id"]]["status"] == "on_track"
    assert kpis[revenue["id"]]["progress_percent"] == 90.0
    assert kpis[retention["id"]]["status"] == "watch"
    assert kpis[growth["id"]]["status"] == "achieved"

    forbidden = client.patch(
        f"/v1/workspace/investor-blueprints/{blueprint['id']}/kpis/{revenue['id']}",
        json={"owner": "Jordan Smith", "target_value": 80000},
        headers=auth(),
    )
    assert forbidden.status_code == 403

    updated = client.patch(
        f"/v1/workspace/investor-blueprints/{blueprint['id']}/kpis/{revenue['id']}",
        json={"owner": "Jordan Smith", "target_value": 80000},
        headers=auth(ADMIN_KEY),
    )
    assert updated.status_code == 200
    assert updated.json()["owner"] == "Jordan Smith"
    assert updated.json()["status"] == "achieved"

    audit = client.get("/v1/workspace/audit-events", headers=auth(ADMIN_KEY)).json()
    edited = next(event for event in audit["items"] if event["entity_id"] == revenue["id"] and event["action"] == "updated")
    assert edited["metadata"]["changed_fields"] == ["owner", "target_value"]


def test_investor_export_and_same_origin_admin_editor(client: TestClient):
    blueprint = create_investor_blueprint(client)
    revenue = create_investor_kpi(client, blueprint["id"])
    create_investor_kpi(
        client,
        blueprint["id"],
        category="retention",
        label="Gross revenue retention",
        actual_value=96,
        target_value=95,
        unit="percent",
    )
    create_investor_kpi(
        client,
        blueprint["id"],
        category="growth",
        label="Launch milestones",
        actual_value=3,
        target_value=5,
        unit="count",
    )

    export = client.get(
        f"/v1/workspace/investor-blueprints/{blueprint['id']}/export",
        headers=auth(VIEWER_KEY),
    )
    assert export.status_code == 200
    assert export.headers["content-type"].startswith("text/html")
    assert "Investor operating snapshot" in export.text
    assert "Revenue milestones" in export.text
    assert "role=\"progressbar\"" in export.text
    assert "Edit blueprint" not in export.text

    ui = client.get(
        f"/v1/workspace/investor-blueprints/{blueprint['id']}/ui",
        headers=auth(ADMIN_KEY),
    )
    assert ui.status_code == 200
    assert "Edit blueprint" in ui.text
    assert "Save owner & target changes" in ui.text
    assert ADMIN_KEY not in ui.text
    assert "HttpOnly" in ui.headers["set-cookie"]
    csrf_token = re.search(r'"csrfToken":"([^"]+)"', ui.text)
    assert csrf_token

    missing_csrf = client.patch(
        f"/v1/workspace/investor-blueprints/{blueprint['id']}/kpis/{revenue['id']}",
        json={"owner": "Morgan Lee"},
    )
    assert missing_csrf.status_code == 403

    saved = client.patch(
        f"/v1/workspace/investor-blueprints/{blueprint['id']}/kpis/{revenue['id']}",
        json={"owner": "Morgan Lee", "target_value": 85000},
        headers={"X-CSRF-Token": csrf_token.group(1)},
    )
    assert saved.status_code == 200
    assert saved.json()["owner"] == "Morgan Lee"
    assert saved.json()["target_value"] == 85000
