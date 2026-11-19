"""Pydantic schemas: the single source of truth for what a lead, an ICP and feedback look like."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def domain_of(url_or_host: str) -> str:
    host = urlparse(url_or_host if "//" in url_or_host else f"//{url_or_host}").hostname or ""
    return host.lower().removeprefix("www.")


class LeadStatus(str, Enum):
    NEW = "new"
    QUALIFIED = "qualified"
    NURTURE = "nurture"
    DISQUALIFIED = "disqualified"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class Evidence(BaseModel):
    """Every claim on a lead should point at a page and a short supporting quote."""

    url: str
    quote: str = Field(max_length=400)
    retrieved_at: str = Field(default_factory=utcnow)


class Contact(BaseModel):
    """Business contact points only (role mailboxes, switchboards, named decision makers published by the business)."""

    name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    source_url: Optional[str] = None

    @field_validator("email")
    @classmethod
    def _email(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("invalid email")
        return value


class Qualification(BaseModel):
    score: float = 0.0
    tier: str = "C"  # A (hot) / B (warm) / C (cold) / DQ
    components: Dict[str, float] = Field(default_factory=dict)
    reasons: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)


class Lead(BaseModel):
    company: str
    website: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    employees: Optional[int] = None
    description: Optional[str] = None
    services: List[str] = Field(default_factory=list)
    signals: List[str] = Field(default_factory=list)  # buying signals: hiring, expansion, new funding, etc.
    contacts: List[Contact] = Field(default_factory=list)
    evidence: List[Evidence] = Field(default_factory=list)
    status: LeadStatus = LeadStatus.NEW
    qualification: Qualification = Field(default_factory=Qualification)
    notes: Optional[str] = None
    created_at: str = Field(default_factory=utcnow)
    updated_at: str = Field(default_factory=utcnow)

    @property
    def key(self) -> str:
        """Dedupe key: website domain when known, otherwise the normalised company name."""
        if self.website:
            return domain_of(self.website)
        return re.sub(r"[^a-z0-9]+", "-", self.company.lower()).strip("-")


class ICP(BaseModel):
    """Ideal customer profile used for prequalification. Edit icp.json to retarget the whole agent."""

    name: str = "default"
    target_industries: List[str] = Field(default_factory=list)
    target_locations: List[str] = Field(default_factory=list)
    min_employees: Optional[int] = None
    max_employees: Optional[int] = None
    required_keywords: List[str] = Field(default_factory=list)
    buying_signals: List[str] = Field(
        default_factory=lambda: ["hiring", "expanding", "new location", "funding", "launch", "rfp", "looking for"]
    )
    disqualifiers: List[str] = Field(default_factory=list)  # e.g. "franchise", "government", "competitor"
    qualify_threshold: float = 70.0
    nurture_threshold: float = 45.0


class Feedback(BaseModel):
    lead_key: str
    verdict: str  # accepted | rejected | needs_work
    reason: Optional[str] = None
    created_at: str = Field(default_factory=utcnow)

    @field_validator("verdict")
    @classmethod
    def _verdict(cls, value: str) -> str:
        value = value.lower()
        if value not in {"accepted", "rejected", "needs_work"}:
            raise ValueError("verdict must be accepted, rejected or needs_work")
        return value
