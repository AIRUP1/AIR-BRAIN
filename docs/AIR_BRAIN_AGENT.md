# AIR BRAIN lead-research agent

`python -m air_brain_agent` — a Claude-driven agent that finds businesses, scrapes their public sites, saves
schema-validated leads with evidence, prequalifies them against your ICP, and learns from your feedback.

## Run

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...   # required
export FIRECRAWL_API_KEY=...   # optional: web_search + JS-rendered pages
python -m air_brain_agent run "find 10 commercial HVAC contractors in Tampa FL that are hiring"
python -m air_brain_agent report --min-score 45
python -m air_brain_agent feedback acmehvac.com rejected "too small, residential only"
python -m air_brain_agent export --fmt csv > leads.csv
```

Data lives in `./data/air_brain/` (`air_brain.db`, `icp.json`, `memories/`, `exports/`). Edit `icp.json` to retarget.

## How the pieces map to the request

| Capability | Where |
|---|---|
| Layered scraper (cache → robots-aware HTTP → Firecrawl rendering, JSON-LD/email/phone extraction, per-domain throttle, SSRF guard) | `scraper.py` |
| Search anything | `web_search` tool (Firecrawl) + `scrape_url` on seed URLs |
| Scraping memory | SQLite page cache + per-domain notes (`store.py`) |
| Claude memory | Anthropic memory tool on `data/air_brain/memories/`; `memory.py` mirrors scraping notes, ICP, weights and feedback there each run |
| Schema | Pydantic `Lead`, `Contact`, `Evidence`, `ICP`, `Feedback` (`schema.py`); the model's tool input is validated before saving |
| Organise leads | Dedupe by domain, merge new facts, status lifecycle (new/qualified/nurture/disqualified/accepted/rejected) |
| Prequalify | Explainable 0–100 score + tier A/B/C/DQ with reasons and missing fields (`qualify.py`) |
| Process feedback | `record_feedback` updates status and re-weights scoring; humans' accepted/rejected decisions are never overwritten |
| Output | Markdown report, CSV/JSON export (`report.py`) |

## Guardrails (by design)

- Obeys `robots.txt`, rate-limits per domain, never bypasses logins/CAPTCHAs/paywalls.
- Refuses LinkedIn, Meta/X/TikTok and people-search sites (terms forbid scraping or they hold private-person data); use official APIs for those.
- Collects business contact information only; every claim needs evidence (url + quote); unknown fields stay null.
- Scraped text is passed to Claude as untrusted data (prompt-injection hardening).
- Outreach is out of scope: before contacting leads, check CAN-SPAM / TCPA / GDPR rules and consent for your use case.
