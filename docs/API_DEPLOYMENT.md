# AIR AGENTS API — deployment guide

This standalone **FastAPI** service supplies a secure operating layer for `airagentsllc.co`. It is intentionally separate from the public portfolio, enabling the marketing site to call only the small public intake surface while AIR / COMMAND-style records remain behind API-key access.

## v1 surface

| Area | Paths | Access |
|---|---|---|
| Availability | `GET /health`, `GET /v1/health`, `GET /docs`, `GET /openapi.json` | Public |
| Service discovery | `GET /v1/public/services` | Public |
| Website intake | `POST /v1/public/lead-intake` | Public, consent required |
| Workspace overview | `GET /v1/workspace/overview` | Viewer+ |
| Leads | `GET/POST /v1/workspace/leads`, `GET/PATCH /v1/workspace/leads/{id}` | Viewer+ reads; Operator+ writes |
| Partners | `GET/POST /v1/workspace/partners`, `PATCH /v1/workspace/partners/{id}` | Viewer+ reads; Operator+ writes |
| Tasks | `GET/POST /v1/workspace/tasks`, `PATCH /v1/workspace/tasks/{id}` | Viewer+ reads; Operator+ writes |
| Lending Desk | `GET/POST /v1/workspace/lending-cases`, `PATCH /v1/workspace/lending-cases/{id}` | Viewer+ reads; Operator+ writes |
| Creative Launchpad | `GET/POST /v1/workspace/campaign-briefs`, `PATCH /v1/workspace/campaign-briefs/{id}` | Viewer+ reads; Operator+ writes |
| Audit trail | `GET /v1/workspace/audit-events` | Admin only |

> **Lending Desk boundary:** the API stores package-readiness and authorized-coordination records only. It does not make underwriting or credit decisions, extend an offer, provide financial advice, or guarantee funding.

## Local launch

1. Create the environment file and generate real values for each placeholder:

   ```bash
   cp .env.example .env
   ```

2. Start the container:

   ```bash
   docker compose up --build
   ```

3. Check the service and interactive contract:

   ```bash
   curl http://localhost:8000/health
   open http://localhost:8000/docs
   ```

The Compose setup persists SQLite data in the ignored `./data` directory. For a production service, mount a durable encrypted volume there (or replace the repository with a managed database adapter before horizontal scaling).

For Kubernetes, `kubernetes_deployment.yaml` includes a single-replica deployment, health probes, a persistent-volume claim, and a secret reference for API keys. Replace the image name, validate the storage class, and create the `air-agents-api-secrets` secret before applying it. Keep this SQLite configuration at **one replica**; move to a managed database before horizontal scaling.

## Required production configuration

| Variable | Required | Purpose |
|---|---:|---|
| `AIR_AGENTS_ENV` | Yes | Set to `production`. |
| `AIR_AGENTS_DATABASE_PATH` | Yes | Path on a **durable** mounted volume, e.g. `/app/data/air_agents.db`. |
| `AIR_AGENTS_API_KEYS` | Yes | JSON object mapping long random secrets to `viewer`, `operator`, or `admin`. |
| `AIR_AGENTS_ENABLE_PUBLIC_INTAKE` | Yes | Set to `true` only after a durable database is attached. |
| `AIR_AGENTS_CORS_ORIGINS` | Yes | Comma-separated approved browser origins; start with `https://airagentsllc.co,https://www.airagentsllc.co`. |

The service defaults to **no API keys** and **public intake disabled**. This prevents a preview deployment from silently receiving customer data into ephemeral storage.

Place the public endpoint behind the hosting provider’s rate limiting or Cloudflare WAF before accepting live traffic. The API includes a consent requirement and a honeypot field, but edge controls are the appropriate production defense against distributed form abuse.

### Generate keys

Use a password manager or this local command once per role; store the values only in your hosting platform’s encrypted environment settings:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Example secret mapping (do not reuse it):

```json
{"<admin-secret>": "admin", "<operator-secret>": "operator", "<viewer-secret>": "viewer"}
```

Browser applications must **never** embed any workspace API key. Have the authenticated backend proxy privileged workspace actions instead.

## Website intake example

Use the public endpoint from the existing `airagentsllc.co` contact form only after the production environment is configured:

```js
await fetch("https://api.airagentsllc.co/v1/public/lead-intake", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    full_name: "Jordan Taylor",
    email: "jordan@example.com",
    company: "Taylor Studio",
    service_interest: "creative_launchpad",
    message: "We want a campaign system.",
    consent_to_contact: true,
    source: "airagentsllc.co"
  })
});
```

## Custom-domain routing

The current Cloudflare connection inspected for this build does **not** control `airagentsllc.co`, so DNS cannot be changed from this environment. After deploying this container to your chosen host:

1. Add `api.airagentsllc.co` as a custom domain in that host.
2. In the DNS account that manages `airagentsllc.co`, add the host’s requested CNAME/ALIAS record for `api`.
3. Wait for TLS validation, then verify:

   ```bash
   curl -i https://api.airagentsllc.co/health
   curl -I https://api.airagentsllc.co/docs
   ```

4. Enable the `AIR_AGENTS_ENABLE_PUBLIC_INTAKE=true` setting only after the health check is successful and durable storage is attached.

## Preview deployment

The repository includes `app.py` and `vercel.json` for an automatic Vercel **contract preview**. Vercel’s serverless filesystem is not durable for this SQLite design, so the preview safely leaves public intake disabled and has no workspace keys. It is suitable for `/health`, `/docs`, and OpenAPI review—not production lead collection or workspace records.

## Verification checklist

```bash
pytest -q
curl -s http://localhost:8000/openapi.json | python -m json.tool | head
```

Before releasing, verify CORS is limited to approved origins, each role receives a unique long key, the data volume is backed up, and `GET /v1/workspace/audit-events` is available only to an `admin` key.
