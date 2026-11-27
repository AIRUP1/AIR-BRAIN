# Merchant Lead Call Pipeline

A small, dependency-free pipeline that takes a merchant sheet, researches each business on the public web, briefs the AI voice agent on that business, and writes call results back to CSV or XML.

It follows [AIR_AGENT_COLD_CALL_PLAYBOOK.md](AIR_AGENT_COLD_CALL_PLAYBOOK.md): the agent discloses it is automated, asks permission, stops at the first opt-out, and collects only a first name and callback number.

**It never dials.** `prepare` writes call bodies; a person places each call (for example through the Speko `sessions_phone_create` tool) and then records the result.

## Sheet columns

| Column | Meaning |
|---|---|
| Merchant Business Name | Required. The agent confirms this on the call. |
| Phone number | Required. Any US format is normalized to E.164. |
| POS / DM | Point-of-sale system or decision-maker. Research may fill it, marked `(unverified)`. |
| Owner / Pre-Qualification | Filled from what the person says on the call. |
| called, connected, failed, voicemail, interested, connect_live_agent | Outcome flags (`yes` or blank). |
| opt_out | Set when the person asks not to be called. Such leads are never prepared again. |
| scraper_source, research_summary, session_id, notes | Provenance and results. |

CSV and XML (`<leads><lead>…</lead></leads>`) are both read and written, chosen by file extension. Header names are matched loosely, so `Merchant Business Name` and `POS / DM` work as written.

## Workflow

```bash
# 1. Clean the sheet: normalize phones, drop duplicates and bad rows
python -m lead_pipeline import merchants.csv --out lead_data/clean.csv

# 2. Optional: public-web research into memory (needs BROWSERLESS_API_KEY)
python -m lead_pipeline research lead_data/clean.csv --city "San Antonio" --limit 25

# 3. Write call bodies for eligible leads only (nothing is dialed)
python -m lead_pipeline prepare lead_data/clean.csv \
  --agent-id agent_XXXX --offer offer.md --dnc dnc.txt --limit 10 --out lead_data/calls.jsonl

# 4. After a call: fold the Speko session and transcript back into the sheet
python -m lead_pipeline record lead_data/clean.csv --phone +12105550142 \
  --session session.json --transcript transcript.json --out lead_data/results.xml
```

`offer.md` is required and is the only thing the agent may say about your product. Nothing about pricing, results or integrations is assumed.

`lead_data/` is git-ignored because it holds contact details.

## Research and "dorks"

`research.py` builds operator queries (`site:`, quoted names, OR groups) restricted to public business-profile facts: hours, phone, profile pages, an apparent POS vendor, and a named owner. It does not build exposed-file, credential or personal-record searches, and a test enforces that.

- Pages are fetched through the repo's `BrowserlessClient`. Automated Google searches can hit CAPTCHAs and conflict with Google's terms; expect gaps, and swap the fetcher for a permitted search API if needed.
- Findings are saved to `research_memory.jsonl` with `verified: false` and fed to the agent as hints. The prompt tells the agent to treat them as possibly wrong, never state them as fact, and accept corrections.
- The Spokeo and other people-search scrapers in `browserless_integration.py` are not used.

## Outcome rules

`outcomes.py` classifies from the session and the merchant's own words:

- **connected**: answered, not voicemail, and a person spoke.
- **failed**: not answered. **voicemail**: machine detected.
- **interested**: positive phrases with no refusal or opt-out. **connect_live_agent**: asked for a person or a callback.
- **opt_out**: "stop calling", "do not call", "remove me" and similar. An opt-out overrides interest.

These are keyword heuristics. Review calls flagged interested or opt-out before acting on them.

## Before any real calls

- Honor do-not-call rules and consent for your jurisdiction, including rules on automated or AI-voiced calls and mobile numbers. Keep the `--dnc` file current.
- Call only in permitted local hours.
- Keep the AI disclosure; do not remove it from the opening line.
- Do not reuse an agent whose saved prompt is for a different offer. `prepare` sets the prompt per call.
- There is no live transfer. "connect live agent" means a team member calls back.
