"""Progressive batch dialer: one human agent, one call at a time, dialed via Webex.

This is a *preview/progressive* dialer, not a predictive autodialer: the next
number is only dialed after the previous call ended and the agent logged a
disposition (or the auto-advance timer elapsed).  It enforces a do-not-call
list and local calling hours.
"""

from __future__ import annotations

import csv
import json
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, time as dtime
from pathlib import Path
from typing import Callable, Iterable
from zoneinfo import ZoneInfo

from .webex_client import WebexClient, WebexError

E164 = re.compile(r"^\+[1-9]\d{7,14}$")
STATE_TZ = {
    "TX": "America/Chicago", "OK": "America/Chicago", "LA": "America/Chicago",
    "CA": "America/Los_Angeles", "NY": "America/New_York", "FL": "America/New_York",
    "CO": "America/Denver", "AZ": "America/Phoenix",
}
DISPOSITIONS = ("connected", "voicemail", "no_answer", "busy", "wrong_number", "callback", "not_interested", "dnc", "failed")


def normalize_e164(raw: str, default_country: str = "1") -> str | None:
    """Return E.164 for ``raw`` or None. 10-digit numbers get the default country code."""
    raw = (raw or "").strip()
    digits = re.sub(r"\D", "", raw)
    if raw.startswith("+"):
        cand = "+" + digits
    elif len(digits) == 10:
        cand = f"+{default_country}{digits}"
    elif len(digits) == 11 and digits.startswith(default_country):
        cand = "+" + digits
    else:
        return None
    return cand if E164.match(cand) else None


@dataclass
class CallRecord:
    phone_e164: str
    business_name: str = ""
    contact_name: str = ""
    email: str = ""
    state: str = ""
    status: str = "pending"  # pending | done | skipped
    disposition: str = ""
    call_id: str = ""
    started_at: str = ""
    duration_s: int = 0
    note: str = ""
    extra: dict = field(default_factory=dict)


def load_call_list(path: str | Path, dnc: Iterable[str] = ()) -> tuple[list[CallRecord], list[str]]:
    """Load the New Call List CSV. Returns (records, warnings). Dedupes and drops DNC/invalid numbers."""
    dnc_set = {normalize_e164(n) or n for n in dnc}
    seen: set[str] = set()
    records: list[CallRecord] = []
    warnings: list[str] = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for i, row in enumerate(csv.DictReader(fh), start=2):
            phone = normalize_e164(row.get("phone_e164") or row.get("phone") or "")
            name = row.get("business_name", "")
            if not phone:
                warnings.append(f"row {i} {name!r}: invalid phone, skipped")
            elif phone in dnc_set:
                warnings.append(f"row {i} {name!r}: on do-not-call list, skipped")
            elif phone in seen:
                warnings.append(f"row {i} {name!r}: duplicate number, skipped")
            else:
                seen.add(phone)
                records.append(CallRecord(
                    phone_e164=phone, business_name=name,
                    contact_name=row.get("contact_name", ""), email=row.get("email", ""),
                    state=(row.get("state") or "").upper(),
                    extra={k: v for k, v in row.items() if k not in {"phone_e164", "business_name", "contact_name", "email", "state"}},
                ))
    return records, warnings


def within_calling_hours(state: str, now: datetime | None = None, start=dtime(9, 0), end=dtime(20, 0)) -> bool:
    tz = ZoneInfo(STATE_TZ.get(state, "America/Chicago"))
    local = (now or datetime.now(tz)).astimezone(tz)
    return start <= local.time() < end and local.weekday() < 6  # Mon-Sat


class BatchDialer:
    def __init__(
        self,
        client: WebexClient,
        records: list[CallRecord],
        state_file: str | Path = "dialer_state.jsonl",
        ask_disposition: Callable[[CallRecord], tuple[str, str]] | None = None,
        gap_seconds: float = 5,
        ring_timeout: float = 5,
        poll_seconds: float = 2,
        sleep: Callable[[float], None] = time.sleep,
        enforce_hours: bool = True,
    ):
        self.client, self.records = client, records
        self.state_file = Path(state_file)
        self.ask = ask_disposition or (lambda r: ("", ""))
        self.gap, self.ring_timeout, self.poll = gap_seconds, ring_timeout, poll_seconds
        self.sleep, self.enforce_hours = sleep, enforce_hours
        self._resume()

    # -- persistence (resume after a crash/restart) -------------------
    def _resume(self) -> None:
        if not self.state_file.exists():
            return
        done = {}
        for line in self.state_file.read_text().splitlines():
            d = json.loads(line)
            done[d["phone_e164"]] = d
        for r in self.records:
            if r.phone_e164 in done:
                r.__dict__.update({k: v for k, v in done[r.phone_e164].items() if k != "extra"})

    def _save(self, r: CallRecord) -> None:
        with self.state_file.open("a") as fh:
            fh.write(json.dumps(asdict(r)) + "\n")

    # -- core loop ----------------------------------------------------
    def run(self, limit: int | None = None) -> list[CallRecord]:
        placed = 0
        for r in self.records:
            if r.status != "pending":
                continue
            if limit is not None and placed >= limit:
                break
            if self.enforce_hours and not within_calling_hours(r.state):
                r.status, r.note = "skipped", "outside calling hours"
                continue
            self._call(r)
            placed += 1
            self.sleep(self.gap)
        return self.records

    def _call(self, r: CallRecord) -> None:
        r.started_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        t0 = time.time()
        try:
            r.call_id = self.client.dial(r.phone_e164).get("callId", "")
        except WebexError as e:
            r.status, r.disposition, r.note = "done", "failed", str(e)
            self._save(r)
            return
        # Wait for the agent's call to disappear from the active list; hang up if it rings out.
        answered = False
        while True:
            self.sleep(self.poll)
            active = {c.get("id") or c.get("callId"): c for c in self.client.active_calls()}
            call = active.get(r.call_id)
            if call is None:
                break
            if str(call.get("state", "")).lower() == "connected":
                answered = True
            elif not answered and time.time() - t0 > self.ring_timeout:
                self.client.hangup(r.call_id)
                r.disposition = "no_answer"
                break
        r.duration_s = int(time.time() - t0)
        disp, note = self.ask(r)
        r.disposition = disp or r.disposition or ("connected" if answered else "no_answer")
        r.note = note or r.note
        r.status = "done"
        self._save(r)

    # -- Webex sync ---------------------------------------------------
    def sync_history(self) -> int:
        """Reconcile results with Webex placed-call history (authoritative duration/time)."""
        by_number = {r.phone_e164: r for r in self.records if r.status == "done"}
        updated = 0
        for item in self.client.call_history("placed"):
            number = normalize_e164((item.get("phoneNumber") or "").replace("tel:", ""))
            r = by_number.get(number or "")
            if r and item.get("duration") is not None:
                r.duration_s = int(item["duration"])
                updated += 1
                self._save(r)
        return updated

    def export(self, path: str | Path) -> None:
        with open(path, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["business_name", "contact_name", "phone_e164", "email", "status", "disposition", "duration_s", "started_at", "note"])
            for r in self.records:
                w.writerow([r.business_name, r.contact_name, r.phone_e164, r.email, r.status, r.disposition, r.duration_s, r.started_at, r.note])
