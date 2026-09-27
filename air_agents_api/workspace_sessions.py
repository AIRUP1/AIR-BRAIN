"""Short-lived, signed sessions for the same-origin workspace presentation layer."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Literal, TypedDict

UI_SESSION_COOKIE = "air_agents_workspace"
UI_SESSION_TTL_SECONDS = 8 * 60 * 60
RoleName = Literal["viewer", "operator", "admin"]


class WorkspaceSession(TypedDict):
    role: RoleName
    csrf_token: str


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def issue_workspace_session(role: RoleName, secret: str, *, now: int | None = None) -> str:
    """Issue a stateless, role-scoped session token with a per-session CSRF token."""

    issued_at = int(now if now is not None else time.time())
    payload = {
        "v": 1,
        "role": role,
        "iat": issued_at,
        "exp": issued_at + UI_SESSION_TTL_SECONDS,
        "csrf": secrets.token_urlsafe(24),
    }
    encoded = _encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = hmac.new(secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).digest()
    return f"{encoded}.{_encode(signature)}"


def verify_workspace_session(token: str | None, secret: str, *, now: int | None = None) -> WorkspaceSession | None:
    """Validate a signed, unexpired workspace session without exposing auth secrets."""

    if not token or token.count(".") != 1:
        return None
    encoded, supplied_signature = token.split(".", 1)
    expected_signature = _encode(hmac.new(secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(supplied_signature, expected_signature):
        return None
    try:
        payload = json.loads(_decode(encoded))
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("v") != 1:
        return None
    role = payload.get("role")
    csrf_token = payload.get("csrf")
    expires_at = payload.get("exp")
    if role not in {"viewer", "operator", "admin"} or not isinstance(csrf_token, str) or not isinstance(expires_at, int):
        return None
    if expires_at <= int(now if now is not None else time.time()):
        return None
    return {"role": role, "csrf_token": csrf_token}
