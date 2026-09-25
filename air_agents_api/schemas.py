"""Pydantic contracts exposed by the versioned AIR AGENTS API."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=8_000)]
OptionalText = Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=8_000)]
PaginationLimit = Annotated[int, Field(ge=1, le=100)]


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ServiceCatalogItem(APIModel):
    id: str
    name: str
    description: str


class LeadIntakeRequest(APIModel):
    full_name: ShortText
    email: EmailStr
    company: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=160)] = None
    phone: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=40)] = None
    service_interest: Literal[
        "ai_growth_systems",
        "partnered_operations",
        "voice_agent_automation",
        "media_production",
        "lending_coordination",
        "creative_launchpad",
        "other",
    ]
    message: OptionalText = None
    consent_to_contact: bool
    source: Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)] = "website"
    website: str | None = Field(default=None, max_length=200, exclude=True, description="Spam trap; leave blank.")


class LeadCreate(LeadIntakeRequest):
    status: Literal["new", "qualified", "nurturing", "closed_won", "closed_lost"] = "new"
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    owner: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=120)] = None


class LeadUpdate(APIModel):
    status: Literal["new", "qualified", "nurturing", "closed_won", "closed_lost"] | None = None
    priority: Literal["low", "normal", "high", "urgent"] | None = None
    owner: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=120)] = None
    message: OptionalText = None
    consent_to_contact: bool | None = None


class LeadResponse(APIModel):
    id: str
    full_name: str
    email: EmailStr
    phone: str | None
    company: str | None
    service_interest: str
    message: str | None
    source: str
    status: str
    priority: str
    owner: str | None
    consent_to_contact: bool
    created_at: datetime
    updated_at: datetime


class PartnerCreate(APIModel):
    name: ShortText
    category: Literal["vendor", "lending_partner", "creative_partner", "technology", "referral", "other"]
    contact_name: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=160)] = None
    email: EmailStr | None = None
    phone: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=40)] = None
    status: Literal["prospect", "active", "inactive", "paused"] = "prospect"
    notes: OptionalText = None


class PartnerUpdate(APIModel):
    category: Literal["vendor", "lending_partner", "creative_partner", "technology", "referral", "other"] | None = None
    contact_name: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=160)] = None
    email: EmailStr | None = None
    phone: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=40)] = None
    status: Literal["prospect", "active", "inactive", "paused"] | None = None
    notes: OptionalText = None


class PartnerResponse(APIModel):
    id: str
    name: str
    category: str
    contact_name: str | None
    email: EmailStr | None
    phone: str | None
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime


class TaskCreate(APIModel):
    title: ShortText
    description: OptionalText = None
    status: Literal["open", "in_progress", "blocked", "completed"] = "open"
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    assignee: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=120)] = None
    due_at: datetime | None = None
    related_type: Literal["lead", "partner", "lending_case", "campaign_brief"] | None = None
    related_id: str | None = Field(default=None, max_length=64)


class TaskUpdate(APIModel):
    title: ShortText | None = None
    description: OptionalText = None
    status: Literal["open", "in_progress", "blocked", "completed"] | None = None
    priority: Literal["low", "normal", "high", "urgent"] | None = None
    assignee: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=120)] = None
    due_at: datetime | None = None


class TaskResponse(APIModel):
    id: str
    title: str
    description: str | None
    status: str
    priority: str
    assignee: str | None
    due_at: datetime | None
    related_type: str | None
    related_id: str | None
    created_at: datetime
    updated_at: datetime


class LendingCaseCreate(APIModel):
    business_name: ShortText
    contact_name: ShortText
    email: EmailStr
    funding_goal: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=1_000)] = None
    requested_amount: Annotated[int | None, Field(ge=0, le=100_000_000)] = None
    readiness_status: Literal["intake", "documents_requested", "package_ready", "partner_follow_up", "closed", "not_proceeding"] = "intake"
    documents_status: Literal["not_requested", "requested", "partial", "complete"] = "not_requested"
    authorized_partner_contact: bool = False
    notes: OptionalText = None


class LendingCaseUpdate(APIModel):
    funding_goal: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=1_000)] = None
    requested_amount: Annotated[int | None, Field(ge=0, le=100_000_000)] = None
    readiness_status: Literal["intake", "documents_requested", "package_ready", "partner_follow_up", "closed", "not_proceeding"] | None = None
    documents_status: Literal["not_requested", "requested", "partial", "complete"] | None = None
    authorized_partner_contact: bool | None = None
    notes: OptionalText = None


class LendingCaseResponse(APIModel):
    id: str
    business_name: str
    contact_name: str
    email: EmailStr
    funding_goal: str | None
    requested_amount: int | None
    readiness_status: str
    documents_status: str
    authorized_partner_contact: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime


class CampaignBriefCreate(APIModel):
    title: ShortText
    objective: LongText
    audience: LongText
    primary_message: LongText
    channels: list[Literal["web", "email", "instagram", "tiktok", "youtube", "linkedin", "paid_media", "other"]] = Field(default_factory=list, max_length=12)
    visual_direction: OptionalText = None
    call_to_action: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=500)] = None
    status: Literal["draft", "review", "approved", "in_production", "complete", "archived"] = "draft"


class CampaignBriefUpdate(APIModel):
    objective: LongText | None = None
    audience: LongText | None = None
    primary_message: LongText | None = None
    channels: list[Literal["web", "email", "instagram", "tiktok", "youtube", "linkedin", "paid_media", "other"]] | None = Field(default=None, max_length=12)
    visual_direction: OptionalText = None
    call_to_action: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=500)] = None
    status: Literal["draft", "review", "approved", "in_production", "complete", "archived"] | None = None


class CampaignBriefResponse(APIModel):
    id: str
    title: str
    objective: str
    audience: str
    primary_message: str
    channels: list[str]
    visual_direction: str | None
    call_to_action: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class Page(APIModel):
    items: list
    total: int
    limit: int
    offset: int


class OverviewResponse(APIModel):
    new_leads: int
    active_partners: int
    open_tasks: int
    lending_cases_in_progress: int
    campaigns_in_production: int


class AuditEventResponse(APIModel):
    id: str
    actor_role: str
    action: str
    entity_type: str
    entity_id: str
    created_at: datetime
    metadata: dict


class MessageResponse(APIModel):
    message: str


class HealthResponse(APIModel):
    status: Literal["ok"]
    service: str
    version: str
    environment: str
    timestamp: datetime
