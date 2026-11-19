"""SQLite persistence: page cache (scrape memory), leads, feedback, learned scoring weights, per-domain notes."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

from .schema import Feedback, Lead, utcnow

DEFAULT_WEIGHTS = {
    "industry": 0.22,
    "location": 0.12,
    "size": 0.12,
    "keywords": 0.16,
    "signals": 0.16,
    "contact": 0.14,
    "evidence": 0.08,
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS pages (url TEXT PRIMARY KEY, fetched_at REAL, status INTEGER, source TEXT, title TEXT, text TEXT, meta TEXT);
CREATE TABLE IF NOT EXISTS leads (key TEXT PRIMARY KEY, data TEXT NOT NULL, status TEXT, score REAL, updated_at TEXT);
CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, lead_key TEXT, verdict TEXT, reason TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS weights (name TEXT PRIMARY KEY, value REAL);
CREATE TABLE IF NOT EXISTS domains (domain TEXT PRIMARY KEY, notes TEXT, updated_at TEXT);
"""


class Store:
    def __init__(self, path: str = "./data/air_brain.db") -> None:
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._db.executescript(SCHEMA)

    def _run(self, sql: str, args: tuple = ()) -> List[sqlite3.Row]:
        with self._lock:
            rows = self._db.execute(sql, args).fetchall()
            self._db.commit()
            return rows

    # --- scrape memory -------------------------------------------------
    def get_page(self, url: str, max_age_s: float) -> Optional[dict]:
        rows = self._run("SELECT * FROM pages WHERE url=?", (url,))
        if rows and time.time() - rows[0]["fetched_at"] <= max_age_s:
            row = dict(rows[0])
            row["meta"] = json.loads(row["meta"] or "{}")
            return row
        return None

    def put_page(self, url: str, status: int, source: str, title: str, text: str, meta: dict) -> None:
        self._run(
            "INSERT OR REPLACE INTO pages VALUES (?,?,?,?,?,?,?)",
            (url, time.time(), status, source, title, text, json.dumps(meta)),
        )

    def note_domain(self, domain: str, note: str) -> None:
        rows = self._run("SELECT notes FROM domains WHERE domain=?", (domain,))
        notes = (rows[0]["notes"] + "\n" if rows else "") + f"- {utcnow()} {note}"
        notes = "\n".join(notes.splitlines()[-20:])
        self._run("INSERT OR REPLACE INTO domains VALUES (?,?,?)", (domain, notes, utcnow()))

    def domain_notes(self) -> Dict[str, str]:
        return {r["domain"]: r["notes"] for r in self._run("SELECT domain, notes FROM domains")}

    # --- leads -----------------------------------------------------------
    def upsert_lead(self, lead: Lead, merge: bool = True) -> Lead:
        """Insert a lead. merge=True folds new facts into the stored lead; merge=False overwrites it as-is."""
        existing = self.get_lead(lead.key) if merge else None
        if existing:  # merge: keep earliest creation, union of list fields, prefer new non-empty scalars
            data = existing.model_dump()
            for field, value in lead.model_dump().items():
                if field in {"services", "signals"}:
                    data[field] = sorted(set(data[field]) | set(value))
                elif field in {"contacts", "evidence"}:
                    seen = {json.dumps(x, sort_keys=True) for x in data[field]}
                    data[field] += [x for x in value if json.dumps(x, sort_keys=True) not in seen]
                elif field not in {"created_at", "status", "qualification"} and value not in (None, "", []):
                    data[field] = value
            lead = Lead(**data)
        lead.updated_at = utcnow()
        self._run(
            "INSERT OR REPLACE INTO leads VALUES (?,?,?,?,?)",
            (lead.key, lead.model_dump_json(), lead.status.value, lead.qualification.score, lead.updated_at),
        )
        return lead

    def get_lead(self, key: str) -> Optional[Lead]:
        rows = self._run("SELECT data FROM leads WHERE key=?", (key,))
        return Lead.model_validate_json(rows[0]["data"]) if rows else None

    def list_leads(self, status: Optional[str] = None, min_score: float = 0, limit: int = 100) -> List[Lead]:
        sql, args = "SELECT data FROM leads WHERE score>=?", [min_score]
        if status:
            sql, args = sql + " AND status=?", args + [status]
        rows = self._run(sql + " ORDER BY score DESC LIMIT ?", tuple(args + [limit]))
        return [Lead.model_validate_json(r["data"]) for r in rows]

    # --- feedback + learned weights --------------------------------------
    def add_feedback(self, fb: Feedback) -> None:
        self._run(
            "INSERT INTO feedback (lead_key, verdict, reason, created_at) VALUES (?,?,?,?)",
            (fb.lead_key, fb.verdict, fb.reason, fb.created_at),
        )

    def list_feedback(self, limit: int = 50) -> List[Feedback]:
        rows = self._run(
            "SELECT lead_key, verdict, reason, created_at FROM feedback ORDER BY id DESC LIMIT ?", (limit,)
        )
        return [Feedback(**dict(r)) for r in rows]

    def get_weights(self) -> Dict[str, float]:
        weights = dict(DEFAULT_WEIGHTS)
        weights.update({r["name"]: r["value"] for r in self._run("SELECT name, value FROM weights")})
        return weights

    def set_weights(self, weights: Dict[str, float]) -> None:
        for name, value in weights.items():
            self._run("INSERT OR REPLACE INTO weights VALUES (?,?)", (name, value))
