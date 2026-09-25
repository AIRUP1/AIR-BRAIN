"""GitHub webhook verification and safe event-summary helpers."""

from __future__ import annotations

import hashlib
import hmac
from typing import Any


class GitHubWebhookSignatureError(ValueError):
    """Raised when a GitHub delivery lacks a valid SHA-256 signature."""


def payload_sha256(raw_body: bytes) -> str:
    """Return a fingerprint suitable for audit/idempotency metadata, not replay."""

    return hashlib.sha256(raw_body).hexdigest()


def verify_github_signature(*, raw_body: bytes, secret: str, signature_header: str | None) -> None:
    """Validate GitHub's X-Hub-Signature-256 over unmodified request bytes."""

    if not signature_header:
        raise GitHubWebhookSignatureError("Missing GitHub webhook signature.")

    expected_signature = "sha256=" + hmac.new(
        secret.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected_signature, signature_header):
        raise GitHubWebhookSignatureError("GitHub webhook signature did not match.")


def summarize_github_event(payload: dict[str, Any]) -> dict[str, str | None]:
    """Extract bounded, non-secret metadata without retaining the raw payload."""

    repository = payload.get("repository")
    installation = payload.get("installation")
    action = payload.get("action")

    repository_full_name = repository.get("full_name") if isinstance(repository, dict) else None
    installation_id = installation.get("id") if isinstance(installation, dict) else None

    return {
        "action": str(action)[:120] if action is not None else None,
        "repository_full_name": str(repository_full_name)[:512] if repository_full_name else None,
        "installation_id": str(installation_id)[:64] if installation_id is not None else None,
    }
