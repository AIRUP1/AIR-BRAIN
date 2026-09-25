"""Runtime configuration for the AIR AGENTS API."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Role = Literal["viewer", "operator", "admin"]


class ConfigurationError(ValueError):
    """Raised when a required API setting is malformed."""


@dataclass(frozen=True)
class Settings:
    """Environment-driven service configuration.

    ``AIR_AGENTS_API_KEYS`` is a JSON object that maps a secret API key to a
    role. Example: ``{"replace-with-long-secret": "admin"}``.
    """

    environment: str
    database_path: str
    api_keys: dict[str, Role]
    cors_origins: list[str]
    enable_public_intake: bool = False
    service_version: str = "1.0.0"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}


def _parse_api_keys(raw_value: str) -> dict[str, Role]:
    if not raw_value:
        return {}

    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise ConfigurationError("AIR_AGENTS_API_KEYS must be a JSON object.") from exc

    if not isinstance(parsed, dict):
        raise ConfigurationError("AIR_AGENTS_API_KEYS must be a JSON object.")

    valid_roles = {"viewer", "operator", "admin"}
    keys: dict[str, Role] = {}
    for secret, role in parsed.items():
        if not isinstance(secret, str) or len(secret) < 16:
            raise ConfigurationError("Each API key must be a string of at least 16 characters.")
        if role not in valid_roles:
            raise ConfigurationError("Each API key role must be viewer, operator, or admin.")
        keys[secret] = role
    return keys


def get_settings() -> Settings:
    """Load validated settings without ever logging secrets."""

    environment = os.getenv("AIR_AGENTS_ENV", "development")
    default_db = "/tmp/air_agents.db" if os.getenv("VERCEL") else "./data/air_agents.db"
    database_path = os.getenv("AIR_AGENTS_DATABASE_PATH", default_db)

    # Ensure a local parent exists before the first SQLite connection. /tmp is
    # writable in serverless environments; durable deployments should mount a
    # persistent volume and set AIR_AGENTS_DATABASE_PATH explicitly.
    parent = Path(database_path).expanduser().resolve().parent
    parent.mkdir(parents=True, exist_ok=True)

    origins = [
        value.strip()
        for value in os.getenv(
            "AIR_AGENTS_CORS_ORIGINS",
            "https://airagentsllc.co,https://www.airagentsllc.co",
        ).split(",")
        if value.strip()
    ]

    return Settings(
        environment=environment,
        database_path=database_path,
        api_keys=_parse_api_keys(os.getenv("AIR_AGENTS_API_KEYS", "")),
        cors_origins=origins,
        enable_public_intake=os.getenv("AIR_AGENTS_ENABLE_PUBLIC_INTAKE", "false").lower()
        in {"1", "true", "yes"},
    )
