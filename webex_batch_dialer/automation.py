"""Hands-off runner: drop call-list CSVs into an inbox folder and the dialer works them.

* Dials only inside the calling window (default 9a-8p CT, Mon-Sat); outside it, it waits.
* Auto-logs outcomes from Webex call state (answered -> connected, else no_answer).
* Keeps going file by file; finished files move to ``<inbox>/done`` and results land in ``<inbox>/results``.
* Stops if too many dials in a row fail (bad token, Webex outage) instead of burning through the list.
* A human still takes the calls: Webex rings *your* device and you talk when someone answers.
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

from .dialer import BatchDialer, load_call_list, within_calling_hours
from .webex_client import WebexClient

CT = ZoneInfo("America/Chicago")


class TooManyFailures(RuntimeError):
    pass


def window_open(now: datetime | None = None) -> bool:
    return within_calling_hours("TX", now)


def process_file(client: WebexClient, csv_path: Path, inbox: Path, dnc: list[str], max_failures: int,
                 sleep: Callable[[float], None] = time.sleep, enforce_hours: bool = True, **dialer_kw) -> dict:
    records, warnings = load_call_list(csv_path, dnc)
    state = inbox / "results" / f"{csv_path.stem}.state.jsonl"
    state.parent.mkdir(parents=True, exist_ok=True)
    d = BatchDialer(client, records, state, ask_disposition=None, sleep=sleep, enforce_hours=enforce_hours, **dialer_kw)
    streak = 0
    for r in d.records:
        if r.status != "pending":
            continue
        if enforce_hours and not window_open():
            break  # window closed mid-file: resume next time (state file remembers who is done)
        d.run(limit=1)
        streak = streak + 1 if r.disposition == "failed" else 0
        if streak >= max_failures:
            d.export(inbox / "results" / f"{csv_path.stem}.results.csv")
            raise TooManyFailures(f"{streak} dials failed in a row on {csv_path.name}: {r.note}")
    pending = sum(1 for r in d.records if r.status == "pending")
    d.export(inbox / "results" / f"{csv_path.stem}.results.csv")
    if pending == 0:
        done = inbox / "done"
        done.mkdir(exist_ok=True)
        csv_path.rename(done / csv_path.name)
    return {"file": csv_path.name, "called": sum(1 for r in d.records if r.status == "done"), "pending": pending, "warnings": warnings}


def run_inbox(client: WebexClient, inbox: str | Path, dnc: list[str] | None = None, max_failures: int = 5, once: bool = False,
              poll_seconds: float = 300, sleep: Callable[[float], None] = time.sleep, log: Callable[[str], None] = print, **kw) -> list[dict]:
    inbox = Path(inbox)
    inbox.mkdir(parents=True, exist_ok=True)
    summary: list[dict] = []
    while True:
        files = sorted(p for p in inbox.glob("*.csv"))
        if files and window_open():
            for f in files:
                res = process_file(client, f, inbox, dnc or [], max_failures, sleep=sleep, **kw)
                log(f"{res['file']}: {res['called']} called, {res['pending']} left")
                summary.append(res)
                if not window_open():
                    break
        elif files:
            log("Outside calling hours; waiting.")
        if once:
            return summary
        sleep(poll_seconds)
