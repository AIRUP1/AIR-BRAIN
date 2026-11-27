---
name: add-v1-route
description: Use when adding a new endpoint to the AIR AGENTS FastAPI service under /v1. Walks through schema, repository, route, role guard, audit event, and test steps following the conventions in air_agents_api/.
---

# Add a /v1 route

1. Read `air_agents_api/main.py`, `schemas.py`, and `repository.py` first and mirror existing patterns (naming, dependency-injected role guards, error shapes).
2. Add Pydantic models to `schemas.py`.
3. Add repository methods to `repository.py` (SQLite adapter; keep Supabase migration notes in `supabase/migrations/` in sync but do not apply them).
4. Add the route in `main.py` under `/v1/...` with the least-privilege role (viewer/operator/admin).
5. Emit an audit event for any write.
6. Add tests to `tests/test_air_agents_api.py` covering success, missing/invalid key, wrong role, and validation errors.
7. Run `PYTHONPATH=. pytest -q`, then apply the `lending-desk-compliance` skill to the diff.
8. Update the route table in `README.md`.
