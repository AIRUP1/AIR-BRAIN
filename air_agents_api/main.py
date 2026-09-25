"""Versioned FastAPI service for AIR AGENTS operating workflows."""
# ruff: noqa: B008
# FastAPI declares request dependencies in endpoint signature defaults.

from __future__ import annotations

import json
import logging
import secrets
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader

from .config import ConfigurationError, Settings, get_settings
from .github_webhooks import (
    GitHubWebhookSignatureError,
    payload_sha256,
    summarize_github_event,
    verify_github_signature,
)
from .repository import Repository
from .schemas import (
    CampaignBriefCreate,
    CampaignBriefResponse,
    CampaignBriefUpdate,
    GitHubWebhookResponse,
    HealthResponse,
    LeadCreate,
    LeadIntakeRequest,
    LeadResponse,
    LeadUpdate,
    LendingCaseCreate,
    LendingCaseResponse,
    LendingCaseUpdate,
    MessageResponse,
    OverviewResponse,
    Page,
    PartnerCreate,
    PartnerResponse,
    PartnerUpdate,
    ServiceCatalogItem,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)

logger = logging.getLogger("air_agents_api")
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)
RoleName = Literal["viewer", "operator", "admin"]

SERVICE_CATALOG = [
    ServiceCatalogItem(
        id="ai_growth_systems",
        name="AI growth systems",
        description="Lead intelligence, CRM operating design, campaign strategy, and contextual AI support.",
    ),
    ServiceCatalogItem(
        id="partnered_operations",
        name="Partnered operations",
        description="Vendor onboarding, shared tasks, documents, media, and accountable follow-through.",
    ),
    ServiceCatalogItem(
        id="voice_agent_automation",
        name="Voice-agent automation",
        description="Consent-aware voice workflows that connect approved outreach and permitted outcomes.",
    ),
    ServiceCatalogItem(
        id="media_production",
        name="Media & production systems",
        description="Cinematic web experiences and managed creative operations tied to conversion objectives.",
    ),
    ServiceCatalogItem(
        id="lending_coordination",
        name="Business-lending coordination",
        description="Readiness information, package documentation, and authorized partner communication—not credit decisions.",
    ),
    ServiceCatalogItem(
        id="creative_launchpad",
        name="Creative launchpad",
        description="Campaign concepts, visual direction, and production-ready briefs.",
    ),
]


class Principal:
    """Authenticated workspace identity, intentionally limited to a role."""

    def __init__(self, role: RoleName):
        self.role = role


ROLE_ORDER = {"viewer": 1, "operator": 2, "admin": 3}


def _serializable_values(model: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    """Convert Pydantic values into safe SQLite scalar values."""

    values = model.model_dump(exclude_unset=exclude_unset, exclude_none=False)
    values.pop("website", None)
    for key, value in list(values.items()):
        if isinstance(value, datetime):
            values[key] = value.astimezone(UTC).isoformat()
        elif isinstance(value, list):
            values[key] = json.dumps(value, separators=(",", ":")) if key == "channels" else value
        elif hasattr(value, "__str__") and value.__class__.__name__ == "EmailStr":
            values[key] = str(value)
    if "channels" in values:
        values["channels_json"] = values.pop("channels")
    return values


def _page(items: list[dict[str, Any]], total: int, limit: int, offset: int) -> Page:
    return Page(items=items, total=total, limit=limit, offset=offset)


def _not_found(entity: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity} not found.")


def create_app(
    settings: Settings | None = None,
    repository: Repository | None = None,
) -> FastAPI:
    """Build a configured service instance for production or integration tests."""

    settings = settings or get_settings()
    repository = repository or Repository(settings.database_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        repository.initialize()
        app.state.settings = settings
        app.state.repository = repository
        logger.info("AIR AGENTS API initialized", extra={"environment": settings.environment})
        yield

    app = FastAPI(
        title="AIR AGENTS API",
        summary="Secure operating workflows for leads, partners, tasks, readiness, and creative production.",
        description=(
            "AIR AGENTS API provides a versioned operating layer for the AIR AGENTS portfolio. "
            "Workspace endpoints require an `X-API-Key` header. The Lending Desk supports operational "
            "coordination only; it does not issue a credit offer, underwriting decision, financial advice, "
            "or guarantee of funding."
        ),
        version=settings.service_version,
        license_info={"name": "Proprietary"},
        contact={"name": "AIR AGENTS LLC", "url": "https://airagentsllc.co"},
        openapi_tags=[
            {"name": "System", "description": "Service availability and discovery."},
            {"name": "Public intake", "description": "Low-friction, consent-aware website intake."},
            {"name": "Workspace", "description": "Authenticated operating records."},
            {"name": "Compliance", "description": "Role-restricted audit trail."},
            {"name": "Webhooks", "description": "Signed machine-to-machine provider deliveries."},
        ],
        lifespan=lifespan,
    )

    # CORS is deliberately restricted to the portfolio domain by default. Set
    # AIR_AGENTS_CORS_ORIGINS for an approved custom frontend or local testing.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next: Callable[..., Any]) -> Response:
        request_id = request.headers.get("X-Request-ID") or secrets.token_urlsafe(12)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:  # pragma: no cover - defensive production barrier
            logger.exception("Unhandled API exception", extra={"request_id": request_id, "path": request.url.path})
            response = JSONResponse(status_code=500, content={"detail": "Internal server error."})
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store"
        logger.info(
            "API request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        return response

    @app.exception_handler(ConfigurationError)
    async def configuration_error_handler(_: Request, exc: ConfigurationError) -> JSONResponse:
        logger.error("Invalid service configuration")
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    async def get_principal(api_key: str | None = Depends(api_key_scheme)) -> Principal:
        if not settings.api_keys:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Workspace authentication is not configured.",
            )
        if not api_key or api_key not in settings.api_keys:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Valid X-API-Key required.",
                headers={"WWW-Authenticate": "ApiKey"},
            )
        return Principal(settings.api_keys[api_key])

    def require_role(minimum_role: RoleName):
        async def dependency(principal: Principal = Depends(get_principal)) -> Principal:
            if ROLE_ORDER[principal.role] < ROLE_ORDER[minimum_role]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This API key does not have permission for that action.",
                )
            return principal

        return dependency

    @app.get("/", tags=["System"], response_model=MessageResponse, include_in_schema=False)
    async def root() -> MessageResponse:
        return MessageResponse(message="AIR AGENTS API is available. See /docs for the API reference.")

    @app.get("/health", tags=["System"], response_model=HealthResponse)
    @app.get("/v1/health", tags=["System"], response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service="air-agents-api",
            version=settings.service_version,
            environment=settings.environment,
            timestamp=datetime.now(UTC),
        )

    @app.get("/v1/public/services", tags=["Public intake"], response_model=list[ServiceCatalogItem])
    async def public_services() -> list[ServiceCatalogItem]:
        return SERVICE_CATALOG

    @app.post(
        "/v1/public/lead-intake",
        tags=["Public intake"],
        response_model=MessageResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_public_lead(payload: LeadIntakeRequest) -> MessageResponse:
        if not settings.enable_public_intake:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Public intake is not enabled for this environment.",
            )
        if payload.website:
            # A silent success response slows unsophisticated form spam without
            # confirming which field triggered detection.
            return MessageResponse(message="Thank you. Your request has been received.")
        if not payload.consent_to_contact:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Consent to contact is required to submit a request.",
            )
        lead = repository.create_entity("leads", _serializable_values(payload))
        repository.record_audit(
            actor_role="public",
            action="created",
            entity_type="lead",
            entity_id=lead["id"],
            metadata={"source": lead["source"], "service_interest": lead["service_interest"]},
        )
        return MessageResponse(message="Thank you. Your request has been received.")

    @app.post(
        "/v1/webhooks/github",
        tags=["Webhooks"],
        response_model=GitHubWebhookResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def receive_github_webhook(request: Request) -> GitHubWebhookResponse:
        """Verify and acknowledge a GitHub delivery without logging its raw payload."""

        if not settings.github_webhook_secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="GitHub webhook delivery is not configured for this environment.",
            )

        raw_body = await request.body()
        try:
            verify_github_signature(
                raw_body=raw_body,
                secret=settings.github_webhook_secret,
                signature_header=request.headers.get("X-Hub-Signature-256"),
            )
        except GitHubWebhookSignatureError as exc:
            logger.warning("Rejected GitHub webhook signature", extra={"path": request.url.path})
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Webhook authentication failed.",
            ) from exc

        delivery_id = request.headers.get("X-GitHub-Delivery")
        event_name = request.headers.get("X-GitHub-Event")
        if not delivery_id or not event_name or len(delivery_id) > 128 or len(event_name) > 120:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GitHub delivery metadata is missing or invalid.",
            )

        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GitHub webhook payload must be valid JSON.",
            ) from exc
        if not isinstance(payload, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GitHub webhook payload must be a JSON object.",
            )

        summary = summarize_github_event(payload)
        digest = payload_sha256(raw_body)
        inserted = repository.record_github_webhook_delivery(
            delivery_id=delivery_id,
            event_name=event_name,
            payload_sha256=digest,
            **summary,
        )
        if inserted:
            repository.record_audit(
                actor_role="system",
                action="github_webhook_received",
                entity_type="github_webhook_delivery",
                entity_id=delivery_id,
                metadata={"event": event_name, "payload_sha256": digest, **summary},
            )
            logger.info("Accepted GitHub webhook", extra={"delivery_id": delivery_id, "event": event_name})
        else:
            logger.info("Acknowledged duplicate GitHub webhook", extra={"delivery_id": delivery_id, "event": event_name})

        return GitHubWebhookResponse(delivery_id=delivery_id, event=event_name, duplicate=not inserted)

    @app.get("/v1/workspace/overview", tags=["Workspace"], response_model=OverviewResponse)
    async def workspace_overview(_: Principal = Depends(require_role("viewer"))) -> OverviewResponse:
        return OverviewResponse(**repository.overview())

    @app.get("/v1/workspace/leads", tags=["Workspace"], response_model=Page)
    async def list_leads(
        status_filter: str | None = Query(default=None, alias="status", max_length=40),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        _: Principal = Depends(require_role("viewer")),
    ) -> Page:
        items, total = repository.list_entities("leads", status=status_filter, limit=limit, offset=offset)
        return _page(items, total, limit, offset)

    @app.post("/v1/workspace/leads", tags=["Workspace"], response_model=LeadResponse, status_code=201)
    async def create_lead(payload: LeadCreate, principal: Principal = Depends(require_role("operator"))) -> dict[str, Any]:
        lead = repository.create_entity("leads", _serializable_values(payload))
        repository.record_audit(actor_role=principal.role, action="created", entity_type="lead", entity_id=lead["id"])
        return lead

    @app.get("/v1/workspace/leads/{lead_id}", tags=["Workspace"], response_model=LeadResponse)
    async def get_lead(lead_id: str, _: Principal = Depends(require_role("viewer"))) -> dict[str, Any]:
        lead = repository.get_entity("leads", lead_id)
        if not lead:
            raise _not_found("Lead")
        return lead

    @app.patch("/v1/workspace/leads/{lead_id}", tags=["Workspace"], response_model=LeadResponse)
    async def update_lead(lead_id: str, payload: LeadUpdate, principal: Principal = Depends(require_role("operator"))) -> dict[str, Any]:
        lead = repository.update_entity("leads", lead_id, _serializable_values(payload, exclude_unset=True))
        if not lead:
            raise _not_found("Lead")
        repository.record_audit(actor_role=principal.role, action="updated", entity_type="lead", entity_id=lead_id)
        return lead

    @app.get("/v1/workspace/partners", tags=["Workspace"], response_model=Page)
    async def list_partners(
        status_filter: str | None = Query(default=None, alias="status", max_length=40),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        _: Principal = Depends(require_role("viewer")),
    ) -> Page:
        items, total = repository.list_entities("partners", status=status_filter, limit=limit, offset=offset)
        return _page(items, total, limit, offset)

    @app.post("/v1/workspace/partners", tags=["Workspace"], response_model=PartnerResponse, status_code=201)
    async def create_partner(payload: PartnerCreate, principal: Principal = Depends(require_role("operator"))) -> dict[str, Any]:
        partner = repository.create_entity("partners", _serializable_values(payload))
        repository.record_audit(actor_role=principal.role, action="created", entity_type="partner", entity_id=partner["id"])
        return partner

    @app.patch("/v1/workspace/partners/{partner_id}", tags=["Workspace"], response_model=PartnerResponse)
    async def update_partner(partner_id: str, payload: PartnerUpdate, principal: Principal = Depends(require_role("operator"))) -> dict[str, Any]:
        partner = repository.update_entity("partners", partner_id, _serializable_values(payload, exclude_unset=True))
        if not partner:
            raise _not_found("Partner")
        repository.record_audit(actor_role=principal.role, action="updated", entity_type="partner", entity_id=partner_id)
        return partner

    @app.get("/v1/workspace/tasks", tags=["Workspace"], response_model=Page)
    async def list_tasks(
        status_filter: str | None = Query(default=None, alias="status", max_length=40),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        _: Principal = Depends(require_role("viewer")),
    ) -> Page:
        items, total = repository.list_entities("tasks", status=status_filter, limit=limit, offset=offset)
        return _page(items, total, limit, offset)

    @app.post("/v1/workspace/tasks", tags=["Workspace"], response_model=TaskResponse, status_code=201)
    async def create_task(payload: TaskCreate, principal: Principal = Depends(require_role("operator"))) -> dict[str, Any]:
        task = repository.create_entity("tasks", _serializable_values(payload))
        repository.record_audit(actor_role=principal.role, action="created", entity_type="task", entity_id=task["id"])
        return task

    @app.patch("/v1/workspace/tasks/{task_id}", tags=["Workspace"], response_model=TaskResponse)
    async def update_task(task_id: str, payload: TaskUpdate, principal: Principal = Depends(require_role("operator"))) -> dict[str, Any]:
        task = repository.update_entity("tasks", task_id, _serializable_values(payload, exclude_unset=True))
        if not task:
            raise _not_found("Task")
        repository.record_audit(actor_role=principal.role, action="updated", entity_type="task", entity_id=task_id)
        return task

    @app.get("/v1/workspace/lending-cases", tags=["Workspace"], response_model=Page)
    async def list_lending_cases(
        status_filter: str | None = Query(default=None, alias="status", max_length=40),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        _: Principal = Depends(require_role("viewer")),
    ) -> Page:
        items, total = repository.list_entities("lending_cases", status=status_filter, limit=limit, offset=offset)
        return _page(items, total, limit, offset)

    @app.post("/v1/workspace/lending-cases", tags=["Workspace"], response_model=LendingCaseResponse, status_code=201)
    async def create_lending_case(payload: LendingCaseCreate, principal: Principal = Depends(require_role("operator"))) -> dict[str, Any]:
        lending_case = repository.create_entity("lending_cases", _serializable_values(payload))
        repository.record_audit(actor_role=principal.role, action="created", entity_type="lending_case", entity_id=lending_case["id"])
        return lending_case

    @app.patch("/v1/workspace/lending-cases/{case_id}", tags=["Workspace"], response_model=LendingCaseResponse)
    async def update_lending_case(case_id: str, payload: LendingCaseUpdate, principal: Principal = Depends(require_role("operator"))) -> dict[str, Any]:
        lending_case = repository.update_entity("lending_cases", case_id, _serializable_values(payload, exclude_unset=True))
        if not lending_case:
            raise _not_found("Lending case")
        repository.record_audit(actor_role=principal.role, action="updated", entity_type="lending_case", entity_id=case_id)
        return lending_case

    @app.get("/v1/workspace/campaign-briefs", tags=["Workspace"], response_model=Page)
    async def list_campaign_briefs(
        status_filter: str | None = Query(default=None, alias="status", max_length=40),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        _: Principal = Depends(require_role("viewer")),
    ) -> Page:
        items, total = repository.list_entities("campaign_briefs", status=status_filter, limit=limit, offset=offset)
        return _page(items, total, limit, offset)

    @app.post("/v1/workspace/campaign-briefs", tags=["Workspace"], response_model=CampaignBriefResponse, status_code=201)
    async def create_campaign_brief(payload: CampaignBriefCreate, principal: Principal = Depends(require_role("operator"))) -> dict[str, Any]:
        campaign = repository.create_entity("campaign_briefs", _serializable_values(payload))
        repository.record_audit(actor_role=principal.role, action="created", entity_type="campaign_brief", entity_id=campaign["id"])
        return campaign

    @app.patch("/v1/workspace/campaign-briefs/{brief_id}", tags=["Workspace"], response_model=CampaignBriefResponse)
    async def update_campaign_brief(brief_id: str, payload: CampaignBriefUpdate, principal: Principal = Depends(require_role("operator"))) -> dict[str, Any]:
        campaign = repository.update_entity("campaign_briefs", brief_id, _serializable_values(payload, exclude_unset=True))
        if not campaign:
            raise _not_found("Campaign brief")
        repository.record_audit(actor_role=principal.role, action="updated", entity_type="campaign_brief", entity_id=brief_id)
        return campaign

    @app.get("/v1/workspace/audit-events", tags=["Compliance"], response_model=Page)
    async def list_audit_events(
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        _: Principal = Depends(require_role("admin")),
    ) -> Page:
        items, total = repository.list_audit_events(limit=limit, offset=offset)
        return _page(items, total, limit, offset)

    return app


app = create_app()
