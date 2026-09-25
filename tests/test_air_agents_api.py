import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from air_agents_api.config import Settings
from air_agents_api.main import create_app
from air_agents_api.repository import Repository

ADMIN_KEY = "admin-secret-key-that-is-long-enough"
OPERATOR_KEY = "operator-secret-key-that-is-long-enough"
VIEWER_KEY = "viewer-secret-key-that-is-long-enough"


@pytest.fixture()
def client(tmp_path: Path):
    settings = Settings(
        environment="test",
        database_path=str(tmp_path / "air_agents_test.db"),
        api_keys={ADMIN_KEY: "admin", OPERATOR_KEY: "operator", VIEWER_KEY: "viewer"},
        cors_origins=["https://airagentsllc.co"],
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
