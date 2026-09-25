# AIR AGENTS API

A standalone, versioned **FastAPI** service for the AIR AGENTS operating platform. It provides consent-aware public intake and protected workspace records for leads, partners, tasks, lending-readiness coordination, campaign briefs, and auditing.

> The Lending Desk supports operations and authorized partner coordination only. It does not issue credit offers, make underwriting decisions, provide financial advice, or guarantee funding.

## Start here

```bash
cp .env.example .env
# Replace every placeholder in .env with secure values.
docker compose up --build
```

- Health: `http://localhost:8000/health`
- Interactive API documentation: `http://localhost:8000/docs`
- OpenAPI specification: `http://localhost:8000/openapi.json`

Run the full validation suite with:

```bash
python -m pip install -r requirements.txt
PYTHONPATH=. pytest -q
```

## API highlights

| Route group | Purpose | Access |
|---|---|---|
| `/health`, `/v1/health`, `/docs` | Availability and contract discovery | Public |
| `/v1/public/services` | Portfolio service catalog | Public |
| `/v1/public/lead-intake` | Consent-aware website intake | Public only when explicitly enabled |
| `/v1/workspace/*` | Leads, partners, tasks, Lending Desk, Creative Launchpad | `X-API-Key` required |

The service accepts three API-key roles: **viewer** (read), **operator** (read/write), and **admin** (read/write/audit trail). Browser clients must never contain a workspace key.

## Deployment and DNS

A Vercel contract preview configuration is included for API-documentation review. It is intentionally **not** a production data host because serverless SQLite storage is ephemeral. For a durable production deployment, run the Docker image with a mounted encrypted volume and configure `api.airagentsllc.co` in the DNS account that owns the domain.

Detailed environment setup, endpoint map, deployment boundary, and exact domain-routing steps are in [docs/API_DEPLOYMENT.md](docs/API_DEPLOYMENT.md).

## Development notes

The project retains the read-only, owner-authorized Instagram Organic Growth Toolkit and its original tests. It does not scrape or publish to Instagram.

```bash
python instagram_organic_growth_toolkit.py \
  --input examples/instagram_metrics.example.json \
  --niche "home fitness" \
  --keywords "strength training,workout routine" \
  --report reports/instagram_growth_report.json
```
