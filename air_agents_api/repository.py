"""Small, dependency-free SQLite repository for the AIR AGENTS workspace."""

from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ENTITY_TABLES = {
    "leads": "leads",
    "partners": "partners",
    "tasks": "tasks",
    "lending_cases": "lending_cases",
    "campaign_briefs": "campaign_briefs",
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class Repository:
    """Per-operation SQLite connections with transaction-safe mutations."""

    def __init__(self, database_path: str):
        self.database_path = str(Path(database_path).expanduser())

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS leads (
            id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            company TEXT,
            service_interest TEXT NOT NULL,
            message TEXT,
            source TEXT NOT NULL DEFAULT 'website',
            status TEXT NOT NULL DEFAULT 'new',
            priority TEXT NOT NULL DEFAULT 'normal',
            owner TEXT,
            consent_to_contact INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_leads_status_created ON leads(status, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);

        CREATE TABLE IF NOT EXISTS partners (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            contact_name TEXT,
            email TEXT,
            phone TEXT,
            status TEXT NOT NULL DEFAULT 'prospect',
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_partners_status ON partners(status);

        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            priority TEXT NOT NULL DEFAULT 'normal',
            assignee TEXT,
            due_at TEXT,
            related_type TEXT,
            related_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_tasks_status_due ON tasks(status, due_at);

        CREATE TABLE IF NOT EXISTS lending_cases (
            id TEXT PRIMARY KEY,
            business_name TEXT NOT NULL,
            contact_name TEXT NOT NULL,
            email TEXT NOT NULL,
            funding_goal TEXT,
            requested_amount INTEGER,
            readiness_status TEXT NOT NULL DEFAULT 'intake',
            documents_status TEXT NOT NULL DEFAULT 'not_requested',
            authorized_partner_contact INTEGER NOT NULL DEFAULT 0,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_lending_cases_status ON lending_cases(readiness_status);

        CREATE TABLE IF NOT EXISTS campaign_briefs (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            objective TEXT NOT NULL,
            audience TEXT NOT NULL,
            primary_message TEXT NOT NULL,
            channels_json TEXT NOT NULL DEFAULT '[]',
            visual_direction TEXT,
            call_to_action TEXT,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_campaign_briefs_status ON campaign_briefs(status);

        CREATE TABLE IF NOT EXISTS audit_events (
            id TEXT PRIMARY KEY,
            actor_role TEXT NOT NULL,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_audit_events_created ON audit_events(created_at DESC);
        """
        with self.connection() as connection:
            connection.executescript(schema)

    @staticmethod
    def _serialize_row(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        for key in ("consent_to_contact", "authorized_partner_contact"):
            if key in result:
                result[key] = bool(result[key])
        if "channels_json" in result:
            result["channels"] = json.loads(result.pop("channels_json"))
        return result

    @staticmethod
    def _table(entity_type: str) -> str:
        try:
            return ENTITY_TABLES[entity_type]
        except KeyError as exc:
            raise ValueError(f"Unsupported entity type: {entity_type}") from exc

    def list_entities(
        self,
        entity_type: str,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        table = self._table(entity_type)
        filters: list[str] = []
        params: list[Any] = []
        if status:
            filters.append("status = ?" if table != "lending_cases" else "readiness_status = ?")
            params.append(status)
        where = f" WHERE {' AND '.join(filters)}" if filters else ""
        with self.connection() as connection:
            total = connection.execute(f"SELECT COUNT(*) FROM {table}{where}", params).fetchone()[0]
            rows = connection.execute(
                f"SELECT * FROM {table}{where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                [*params, limit, offset],
            ).fetchall()
        return [self._serialize_row(row) for row in rows], total

    def get_entity(self, entity_type: str, entity_id: str) -> dict[str, Any] | None:
        table = self._table(entity_type)
        with self.connection() as connection:
            row = connection.execute(f"SELECT * FROM {table} WHERE id = ?", (entity_id,)).fetchone()
        return self._serialize_row(row) if row else None

    def create_entity(self, entity_type: str, values: dict[str, Any]) -> dict[str, Any]:
        table = self._table(entity_type)
        entity_id = str(uuid.uuid4())
        timestamp = utc_now()
        columns = ["id", *values.keys(), "created_at", "updated_at"]
        placeholders = ", ".join("?" for _ in columns)
        params = [entity_id, *values.values(), timestamp, timestamp]
        with self.connection() as connection:
            connection.execute(
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
                params,
            )
        entity = self.get_entity(entity_type, entity_id)
        assert entity is not None
        return entity

    def update_entity(self, entity_type: str, entity_id: str, values: dict[str, Any]) -> dict[str, Any] | None:
        if not values:
            return self.get_entity(entity_type, entity_id)
        table = self._table(entity_type)
        values["updated_at"] = utc_now()
        assignment = ", ".join(f"{column} = ?" for column in values)
        with self.connection() as connection:
            cursor = connection.execute(
                f"UPDATE {table} SET {assignment} WHERE id = ?",
                [*values.values(), entity_id],
            )
            if cursor.rowcount == 0:
                return None
        return self.get_entity(entity_type, entity_id)

    def record_audit(
        self,
        *,
        actor_role: str,
        action: str,
        entity_type: str,
        entity_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO audit_events (id, actor_role, action, entity_type, entity_id, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    actor_role,
                    action,
                    entity_type,
                    entity_id,
                    utc_now(),
                    json.dumps(metadata or {}, separators=(",", ":")),
                ),
            )

    def list_audit_events(self, *, limit: int = 100, offset: int = 0) -> tuple[list[dict[str, Any]], int]:
        with self.connection() as connection:
            total = connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]
            rows = connection.execute(
                "SELECT * FROM audit_events ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        events = []
        for row in rows:
            event = dict(row)
            event["metadata"] = json.loads(event.pop("metadata_json"))
            events.append(event)
        return events, total

    def overview(self) -> dict[str, int]:
        with self.connection() as connection:
            return {
                "new_leads": connection.execute("SELECT COUNT(*) FROM leads WHERE status = 'new'").fetchone()[0],
                "active_partners": connection.execute("SELECT COUNT(*) FROM partners WHERE status = 'active'").fetchone()[0],
                "open_tasks": connection.execute("SELECT COUNT(*) FROM tasks WHERE status != 'completed'").fetchone()[0],
                "lending_cases_in_progress": connection.execute(
                    "SELECT COUNT(*) FROM lending_cases WHERE readiness_status NOT IN ('closed', 'not_proceeding')"
                ).fetchone()[0],
                "campaigns_in_production": connection.execute(
                    "SELECT COUNT(*) FROM campaign_briefs WHERE status IN ('approved', 'in_production')"
                ).fetchone()[0],
            }
