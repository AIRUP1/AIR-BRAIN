---
name: lending-desk-compliance
description: Use when writing or reviewing code, copy, schemas, or docs touching the Lending Desk, lead intake, or investor blueprints in the AIR AGENTS API. Ensures no credit offers, underwriting decisions, financial advice, or funding guarantees, and that consent and role rules are respected.
---

# Lending Desk compliance rules

The Lending Desk supports **operations and authorized partner coordination only**.

When touching related code or text, verify:

1. **No credit offers, underwriting decisions, financial advice, or funding guarantees** in field names, responses, docs, or generated copy. Use neutral wording such as "readiness", "coordination", "status".
2. **Consent**: public intake (`/v1/public/lead-intake`) must record consent and stay disabled unless explicitly enabled by config.
3. **Roles** (`X-API-Key`): viewer = read, operator = read/write, admin = read/write/audit. Investor blueprint mutations are admin-only.
4. **Audit**: protected changes must emit an append-only audit event.
5. **Secrets**: workspace keys never reach browser clients; `.env` is never committed or edited (use `.env.example`).

Report violations with file and line, and propose a compliant rewrite.
