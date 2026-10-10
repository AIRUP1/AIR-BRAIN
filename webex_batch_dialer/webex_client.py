"""Minimal Webex Calling REST client (Call Control + Call History).

Required integration scopes: ``spark:calls_write`` and ``spark:calls_read``.
Docs: https://developer.webex.com/docs/api/v1/call-controls
"""

from __future__ import annotations

import time
from typing import Any

import requests

API = "https://webexapis.com/v1"


class WebexError(RuntimeError):
    def __init__(self, status: int, message: str):
        super().__init__(f"Webex API {status}: {message}")
        self.status = status


class WebexClient:
    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        refresh_token: str | None = None,
        access_token: str | None = None,
        session: requests.Session | None = None,
    ):
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._access_token = access_token
        self._expires_at = 0.0 if refresh_token else float("inf")
        self._http = session or requests.Session()

    # -- auth ---------------------------------------------------------
    def _token(self) -> str:
        if self._access_token and time.time() < self._expires_at - 60:
            return self._access_token
        if not (self._client_id and self._client_secret and self._refresh_token):
            if self._access_token:
                return self._access_token
            raise WebexError(401, "no access token or refresh credentials configured")
        resp = self._http.post(
            f"{API}/access_token",
            data={
                "grant_type": "refresh_token",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
            },
            timeout=30,
        )
        if resp.status_code != 200:
            raise WebexError(resp.status_code, resp.text[:300])
        body = resp.json()
        self._access_token = body["access_token"]
        self._refresh_token = body.get("refresh_token", self._refresh_token)
        self._expires_at = time.time() + int(body.get("expires_in", 3600))
        return self._access_token

    def _request(self, method: str, path: str, **kw: Any) -> Any:
        for attempt in range(4):
            resp = self._http.request(
                method,
                f"{API}{path}",
                headers={"Authorization": f"Bearer {self._token()}"},
                timeout=30,
                **kw,
            )
            if resp.status_code == 429:
                time.sleep(int(resp.headers.get("Retry-After", 2 ** attempt)))
                continue
            if resp.status_code >= 400:
                raise WebexError(resp.status_code, resp.text[:300])
            return resp.json() if resp.content else {}
        raise WebexError(429, "rate limited after retries")

    # -- call control -------------------------------------------------
    def dial(self, destination: str) -> dict:
        """Start an outbound call from the authorized user. Returns callId/callSessionId."""
        return self._request("POST", "/telephony/calls/dial", json={"destination": destination})

    def hangup(self, call_id: str) -> None:
        self._request("POST", "/telephony/calls/hangup", json={"callId": call_id})

    def active_calls(self) -> list[dict]:
        return self._request("GET", "/telephony/calls").get("items", [])

    def call_history(self, call_type: str = "placed") -> list[dict]:
        return self._request("GET", "/telephony/calls/history", params={"type": call_type}).get("items", [])
