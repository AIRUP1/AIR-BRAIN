"""Per-business research memory, stored as JSON lines so it can be audited."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


class ResearchMemory:
    """Append-only notes about a business, keyed by E.164 phone number."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def add(self, phone: str, summary: str, sources: List[str], pos_hint: str = "") -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "phone": phone,
            "summary": summary,
            "sources": sources,
            "pos_hint": pos_hint,
            "verified": False,
            "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")

    def latest(self, phone: str) -> Optional[Dict[str, object]]:
        if not self.path.exists():
            return None
        found = None
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("phone") == phone:
                found = record
        return found
