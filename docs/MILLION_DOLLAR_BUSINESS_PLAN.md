# AIR AGENTS — $1M Revenue Plan (Income-Driven, Multi-Platform)

**Goal:** $1,000,000 in annual recurring revenue (ARR) for AIR AGENTS LLC, working backward from income, with every platform used as a lead channel feeding one funnel.
**Status:** Planning document. Every number below is an **assumption to test**, not a forecast or guarantee. Replace them with your real data after the first 30 days.

> Compliance guardrails (from the existing platform): outreach is consent-aware, the Lending Desk is coordination only (no credit offers, underwriting, or funding guarantees), and automated actions stay behind human review.

---

## 1. Offer ladder (what actually earns the money)

These map to the services already in `SERVICE_CATALOG` (`air_agents_api/main.py`).

| Tier | Offer | Price (assumed) | Type |
|---|---|---|---|
| Entry | AI Growth Audit (lead intelligence + CRM review) | $1,500 one-time | Lead magnet that pays for itself |
| Core | AI Growth Systems retainer (CRM ops, campaigns, AI support) | $3,000/mo | Recurring |
| Core | Voice-agent automation (consent-aware outreach/follow-up) | $2,500/mo + $2,500 setup | Recurring |
| Add-on | Media & Creative Launchpad (briefs, campaigns, production) | $1,500/mo or $4,000/project | Recurring/project |
| Partner | Lending-readiness coordination (package prep, partner communication) | $1,000/mo or fee paid by the partner, per compliance review | Recurring/partner |

Blended target: **~$3,000 per client per month = $36,000 ARR per client.**

## 2. The math backward from $1M

- $1,000,000 ÷ $36,000 ≈ **28 retained clients.**
- With 20% annual churn, plan on ~**35 clients signed** over the year.
- Typical B2B service close rate on qualified calls: 20–25%, so ~**150 qualified sales calls**.
- Booking rate from outreach/inbound ~10–15%, so ~**1,200 qualified conversations/leads**.

| Quarter | New clients | Cumulative MRR | Notes |
|---|---|---|---|
| Q1 | 5 | $15K | Founder-led sales, audits to retainers |
| Q2 | 8 | $39K | Content and referrals start to compound |
| Q3 | 10 | $69K | Partner channel live |
| Q4 | 12 | $105K (≈$1.26M run-rate) | Exit the year above $1M ARR run-rate |

Realized revenue in year one will be lower than the exit run-rate. The plan is a run-rate target; hitting $1M *recognized* revenue in 12 months needs roughly 1.5x the Q1–Q2 pace.

## 3. Channel plan: every platform feeds one funnel

One funnel: **Platform content → lead magnet or DM → consent-aware intake (`/v1/public/lead-intake`) → audit call → paid audit → retainer.**

| Platform | Role | Content | Weekly effort | Target leads/mo |
|---|---|---|---|---|
| LinkedIn | Primary B2B engine | Case studies, build-in-public, founder posts, outbound to owners | 5 posts + 50 connection notes | 40 |
| Cold email + phone | Fastest revenue | Segmented lists, `AIR_AGENT_COLD_CALL_PLAYBOOK.md` | 200 sends + dials | 30 |
| Google (SEO + Business Profile) | Compounding inbound | Service and industry pages, "AI for [industry]" | 2 pages | 20 (by Q3) |
| YouTube | Authority + SEO | 1 long demo/teardown per week, cut into shorts | 1 video | 15 |
| Instagram / TikTok / Shorts | Awareness, retargeting | Clips of YouTube video, before/after (see `INSTAGRAM_ORGANIC_GROWTH_TOOLKIT.md`) | 5 clips | 10 |
| X | Credibility, network | Short threads, product updates | 7 posts | 5 |
| Newsletter | Owned audience, nurtures everything | Weekly "what we built for clients" | 1 issue | converts 5–10% of list |
| Partners/referrals (lenders, agencies, CPAs) | Highest-trust channel | Referral agreement, rev-share | 3 intro calls | 10 |
| Paid ads (Meta/Google/LinkedIn) | Scale only after proof | Retarget audit-page visitors first | $1.5–3K/mo | 15 |

**Rule:** do not run all nine at once. Start with LinkedIn + cold outreach + one video platform. Add a channel only when the current ones hit their targets.

## 4. How the existing platform supports this

| Business need | Already in repo | Gap to build next |
|---|---|---|
| Lead capture with consent | `/v1/public/lead-intake` (honeypot, consent required) | Landing page, UTM source field, enable in production |
| Lead/partner/task tracking | `/v1/workspace/*` | Pipeline stages, source attribution report |
| Investor/KPI reporting | Investor blueprints (revenue, retention, growth KPIs) | Seed a blueprint with the targets in section 2 |
| Voice outreach | Voice-agent workflows, cold call playbook | Consent log and call-outcome write-back |
| Creative production | Creative Launchpad | Content calendar and approval queue |
| Durable data | Supabase migrations (not applied) | Apply after authorization, then move off SQLite |

Suggested first build: add a `source`/`utm_*` field to lead intake and a weekly funnel report (leads → calls → audits → retainers) so every platform's return is measured.

## 5. 90-day execution plan

**Days 1–14 — Foundation**
- Pick **one niche** with budget and pain (suggested: home services, med spas, or small B2B firms with a CRM mess). A niche lifts close rates.
- Publish the audit offer page; enable lead intake in production.
- Build a prospect list of 500 in the niche; seed the KPI blueprint.

**Days 15–45 — Revenue first**
- Outreach: 200/week email + calls. Goal: 15 audit calls/week.
- LinkedIn: 5 posts/week; start the weekly video.
- Sell 5 audits; convert at least 2 to retainers.

**Days 46–90 — Systemize**
- Turn the first 2–3 client wins into case studies, then into content on all platforms.
- Launch the newsletter and 3 referral partners.
- Review the funnel report; double down on the 2 best channels, cut the rest.
- Goal by day 90: **$15K MRR, 5 clients.**

## 6. KPIs to track weekly

Leads by source · Booked calls · Show rate · Close rate · Audit → retainer conversion · MRR · Churn · CAC by channel · Payback (target < 3 months).

## 7. Risks and honest caveats

- **$1M is not guaranteed.** It depends on close rates and retention, which are assumptions here.
- **Delivery capacity:** 28 clients at this scope needs 2–4 delivery staff or strong automation by Q3.
- **Compliance:** call and text outreach is subject to TCPA/DNC and state rules; email to CAN-SPAM; lending-adjacent work to applicable lending and advertising regulations. Get counsel review before scaling outreach or the lending offer.
- **Platform dependence:** keep an owned list (newsletter/CRM) so a platform ban does not stop revenue.
- **Founder bottleneck:** document the sales and delivery playbooks before hiring.

## 8. Decisions needed from you

1. Which niche first?
2. Confirm pricing, or give me real numbers and I'll recompute section 2.
3. Should I build the funnel tracking (UTM source + weekly funnel report) in the API next?
