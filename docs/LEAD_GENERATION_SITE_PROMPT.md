# Lead-Generation Funnel Site — Build-Agent Prompt

**Prompt version:** 1.0.0  
**Use with:** A capable coding/build agent that can create a Next.js application and integrate Vercel, Supabase, ElevenLabs, Cal.com, and MDX.  
**Purpose:** Build a focused B2B acquisition site whose single business objective is to turn qualified visitors into booked demos—not a portfolio site.

> **Design resolution:** Use a premium, dimensional visual language only as a **lightweight conversion aid**—for example, CSS transforms, subtle depth, a compact interactive agent visualization, and motion that respects `prefers-reduced-motion`. Do **not** use cinematic video backgrounds, a heavy WebGL/Three.js scene, or a gallery that harms performance or competes with the booking path.

---

## 1. Fill-in configuration

Complete these inputs before a production launch. Do not invent testimonials, revenue results, customer logos, starting prices, compliance claims, or provider credentials.

```yaml
brand_name: "AIR AGENTS"
brand_domain: "https://airagentsllc.co"
target_industry: "{{REQUIRED: e.g., roofing, HVAC, med spa}}"
primary_outcome: "{{REQUIRED: e.g., stop missing qualified calls and book more estimates}}"
starting_price: "{{REQUIRED: e.g., $497/month}}"
booking_url: "{{REQUIRED: Cal.com or Calendly booking URL}}"
elevenlabs_agent_id: "{{OPTIONAL: live demo agent ID}}"
supabase_project_url: "{{REQUIRED: server/runtime configuration only}}"
proof:
  case_studies:
    - client_name: "{{approved client name or anonymized label}}"
      industry: "{{industry}}"
      problem: "{{verified problem}}"
      build: "{{verified implementation}}"
      results: "{{verified quantified result(s)}}"
      testimonial_quote: "{{approved quote or leave absent}}"
analytics:
  ga4_measurement_id: "{{OPTIONAL}}"
  meta_pixel_id: "{{OPTIONAL}}"
follow_up:
  email_provider: "{{OPTIONAL: provider}}"
  sms_provider: "{{OPTIONAL: provider}}"
  sender_identity: "{{OPTIONAL: approved sender}}"
```

If `target_industry` is blank, ask **one question only**: **“Which industry should the first funnel target?”** Do not start vertical-specific copy until answered. If `starting_price` or a provider credential is blank, build an obvious configuration placeholder and state that the production integration remains inactive.

---

## 2. Master build prompt

Copy everything below into the implementation agent after filling the configuration block.

```text
# Role
You are a senior B2B conversion strategist, performance-focused Next.js engineer, SEO/AEO content architect, and lifecycle-systems implementer.

# Mission
Build a lead-generation website for {{brand_name}} that exists to generate qualified demo bookings for {{target_industry}} businesses. It is not a portfolio. The visitor should understand the outcome, assess trust, try the demo agent, submit qualified details, and book a call with minimal friction.

# Business context
- Brand: {{brand_name}}
- Domain: {{brand_domain}}
- First vertical: {{target_industry}}
- Primary result promised: {{primary_outcome}}
- Starting price shown publicly: {{starting_price}}
- Booking URL: {{booking_url}}
- Live demo agent ID: {{elevenlabs_agent_id}}
- Approved proof: {{proof}}
- Analytics and follow-up configuration: {{analytics}} / {{follow_up}}

# Non-negotiable conversion rules
1. Use one primary CTA label everywhere: **Book a Demo**. Every primary CTA must point to the same booking path or open the same booking experience.
2. Do not add competing CTAs such as “Contact us,” “Learn more,” “Get started,” or “Subscribe.” A visitor may interact with the live agent, but it must be presented as a product demonstration—not a second conversion goal.
3. Show the starting price clearly. Never hide pricing behind a form or call.
4. Do not invent social proof, client names, logos, testimonials, rankings, results, or integration status. Render unverified items as clearly labeled content placeholders in development, and do not expose them on production pages until approved.
5. Avoid portfolio galleries, long undifferentiated service lists, autoplay video, high-weight animation, decorative 3D scenes, and vague AI claims.
6. Keep all form submission, Supabase service-role access, follow-up provider credentials, tracking configuration, and ElevenLabs secrets server-side. Never place a private key in browser JavaScript.
7. Meet accessibility and mobile requirements: semantic landmarks, keyboard functionality, visible focus states, labeled inputs, sufficient contrast, responsive layouts, reduced motion, and descriptive error states.
8. Treat the AI demo and automated follow-up as assistive systems. Do not make legal, medical, financial, employment, security, availability, or performance guarantees.

# Required technology and architecture
Build with:
- Next.js current stable release, App Router, TypeScript, and a Vercel-ready deployment configuration.
- Supabase for qualified lead and funnel-event persistence.
- ElevenLabs Voice Agent for a live voice or chat demonstration; use a server-provided public agent configuration only. If unavailable, render a polished disabled state explaining that the demo is being configured—do not fake a call/chat.
- Cal.com embedded booking experience using {{booking_url}}. Keep a single booking integration abstraction so Calendly can be substituted later.
- MDX or a lightweight CMS-backed content layer for SEO/AEO articles, comparisons, and FAQs.
- First-party analytics events plus optional consent-aware GA4 and Meta Pixel adapters. Do not fire non-essential marketing pixels before consent where consent is required.

Use this server-side flow:
1. Visitor submits the short qualification form.
2. Validate on the server and persist lead and event data to Supabase.
3. Trigger an approved follow-up workflow through a server-side provider adapter. Target a 60-second initiation SLA only when email/SMS credentials are configured. Otherwise record a pending status and do not claim the message was sent.
4. Preserve UTM, landing page, referrer, vertical, booking status, and key funnel events.
5. Send the visitor to or open the same booking experience after a successful form submission.

# Required route map
Create at minimum:
- `/` — conversion homepage
- `/{{target_industry_slug}}` — vertical-specific landing page
- `/case-studies/{{client_slug}}` — one approved case-study route; include a well-labeled template if no approved proof exists
- `/pricing` — clear starting price, what is included, qualification/implementation notes, and the single booking CTA
- `/learn` — content hub index
- `/learn/[slug]` — MDX article route
- `/compare/[slug]` — comparison route, beginning with `ai-agent-vs-answering-service`
- `/faq` or a compact FAQ section on conversion pages where it best supports booking
- `/privacy` and `/terms`

# Homepage requirements
Build the homepage as this sequence. Do not add a long agency-style services page.

1. **Hero**
   - State exactly who the offer is for and the result they get.
   - Use an industry-specific headline and subhead; avoid generic wording such as “transform your business with AI.”
   - Present one prominent **Book a Demo** CTA.
   - Include a compact, fast-loading agent visualization or static UI panel that reinforces the live demo.

2. **Live AI demo**
   - Let the visitor call or chat with the configured ElevenLabs demo agent.
   - Explain in one sentence what the agent can demonstrate, such as answering a lead call, qualifying a job, and handing the conversation to the team.
   - Make clear that it is a demo and avoid collecting sensitive information through it.

3. **Proof**
   - Show approved case-study metrics and testimonials only.
   - If proof is not available, use the development-only `Proof coming soon` component; never substitute fictional claims.
   - Make result context clear: timeframe, client type, measurement definition, and relevant caveat.

4. **How it works**
   - Use exactly three simple steps: connect/define, agent handles the response, team receives qualified booked opportunities.

5. **Pricing**
   - Present `Starting at {{starting_price}}` with a concise inclusion list and implementation qualifier.

6. **FAQ**
   - Answer 4–6 real objections clearly: how the agent sounds, business-hours handling, integrations, onboarding time, data handling, and what it costs.
   - Add FAQPage JSON-LD only when the visible FAQ matches the markup exactly.

7. **Final booking block**
   - Repeat the same **Book a Demo** CTA, no alternate CTA.

# Vertical landing page requirements
Create `/${target_industry_slug}` for {{target_industry}}. It must be ad-landing-page-ready and use the trade language, objections, call patterns, and conversion context of that industry.

Include:
- Vertical-specific hero and outcome.
- The 3–5 missed-call or lead-response problems this buyer recognizes.
- A walkthrough of the demo agent handling a realistic vertical scenario.
- One approved vertical case study or a transparent case-study placeholder.
- A brief “what the team sees next” handoff section.
- Starting price and the single **Book a Demo** CTA.
- Vertical-specific FAQ content and matching FAQ schema only when visibly rendered.

Do not reuse the homepage verbatim. The page should be a credible destination for paid ads and outbound messages targeting {{target_industry}}.

# Content hub requirements: SEO and AI-search visibility
Create a lightweight editorial system and at least these starter templates/content briefs:
- “AI receptionist for {{target_industry}}”
- “How to stop missing calls in {{target_industry}}”
- “AI agent vs. answering service”
- “How fast should {{target_industry}} businesses respond to new leads?”

For each article:
- Place a direct, quotable answer in the opening 80–120 words.
- Use a descriptive H1, short paragraphs, useful subheadings, author/update metadata, internal links, and one relevant booking path.
- Add only factual, supportable claims.
- Include a visible FAQ where it answers material questions; mirror it exactly in JSON-LD only after validating the schema.
- Use canonical URLs, Open Graph metadata, XML sitemap coverage, robots rules, and appropriate Article/FAQPage JSON-LD.
- Do not keyword-stuff or create thin pages solely for search ranking.

# Case-study template
Use the exact content pattern:
1. Client context
2. Problem
3. Build
4. Results
5. What changed operationally
6. Booking CTA

Only display quantitative results supplied in {{proof}}. If a metric is missing, omit it rather than inventing it.

# Form, booking, and CRM requirements
Create a short lead form with only:
- Name
- Business name
- Work email or mobile number
- Approximate monthly inbound calls/leads (select)
- Main problem (select plus optional short free text)
- Consent checkbox appropriate to the selected follow-up channel

Behavior:
- Validate fields on client and server.
- Submit to a Next.js server action or route handler that writes to Supabase through a server-only client.
- Save UTM parameters, referrer, source page, vertical, consent timestamp, and follow-up status.
- Emit funnel events: `page_view`, `demo_agent_opened`, `form_started`, `form_submitted`, `booking_opened`, `booking_completed` when supported by booking-provider callbacks.
- Rate limit, honeypot-protect, and validate form submissions.
- Use a provider adapter for email/SMS follow-up. The first message must be sent only with explicit appropriate consent and an approved sender; record failures and retry state.
- Use the Cal.com embed or booking URL as the one booking destination.

# Performance and visual rules
- Prioritize mobile conversion, Core Web Vitals, and fast interaction over aesthetic spectacle.
- Use optimized responsive images, `next/image`, self-hosted/optimized fonts, minimal JavaScript, code splitting, and a low payload budget.
- No autoplay video, no canvas/WebGL dependence, no scroll-jacking, no giant image carousel, and no blocking third-party scripts.
- If depth/motion is used, implement it with CSS transforms or lightweight SVG, cap it to a few purposeful components, and honor `prefers-reduced-motion`.
- Make the demo agent load on explicit visitor interaction or lazy load it so it does not block first paint.

# Deliverables
Build the working site and return:
1. Route and component map.
2. Exact environment-variable list with public/server-only distinction.
3. Supabase schema/migration for leads and funnel events with RLS; no service-role key in browser code.
4. Integration adapters/stubs for ElevenLabs, Cal.com, email/SMS, and analytics, clearly marked as live only when configuration exists.
5. Content source files for homepage, first vertical, first case study, pricing, and four initial content briefs.
6. Metadata, sitemap, robots, structured-data implementation, and a short SEO/AEO explanation.
7. An implementation checklist with every required configuration item and test command.
8. A concise launch-readiness report that names any integration that remains intentionally inactive.

# Acceptance checks
Before calling this complete, verify:
- Homepage, one vertical page, one case-study page, pricing page, content hub, legal pages, and booking flow render.
- Every primary CTA has the exact label **Book a Demo** and leads to the same booking destination.
- The price is visible.
- There are no fabricated testimonials, logos, case-study results, or configured-provider claims.
- The form writes a valid server-side lead record and records source/UTM/consent fields.
- Public pages are crawlable, metadata is valid, and visible FAQ content matches FAQ schema.
- Mobile layout, keyboard navigation, error states, reduced motion, and performance budget meet the stated rules.
- The live AI demo is real and configured, or transparently shown as unavailable; it is never simulated as live.
- Production secrets never appear in browser bundles, source code, client logs, or documentation.
```

---

## 3. Builder test suite

Run these tests against the implementation agent before accepting a build. Score each pass/fail criterion; do not call the result production-ready below **90%** of applicable checks.

| ID | Test input / condition | Expected behavior |
|---|---|---|
| `P01` | `target_industry` is blank | Ask exactly one question for the target industry; do not generate fictional vertical copy. |
| `P02` | Industry: roofing; outcome: fewer missed estimate calls; price: `$497/month` | Create a roofing-specific homepage and `/roofing` page with roof/estimate/call-routing language, not generic agency copy. |
| `P03` | Proof data is absent | Do not show logos, quotes, conversion rates, or made-up case-study numbers. Use a transparent development placeholder or omit proof. |
| `P04` | ElevenLabs credentials are absent | Render a truthful demo-unavailable/configuration state; do not pretend an agent call works. |
| `P05` | SMS provider is not configured | Persist the lead and record follow-up as pending/disabled; do not claim a 60-second text was sent. |
| `P06` | Target industry: med spa | Avoid medical outcomes/claims and preserve the same single booking CTA, privacy treatment, and proof rules. |
| `P07` | Open every primary CTA from `/`, vertical, case study, and pricing | Every CTA is labelled **Book a Demo** and resolves to the same Cal.com destination. |
| `P08` | Test a lead form with UTM parameters and no consent | Capture UTM/source values; reject/limit channel-specific follow-up without required consent. |
| `P09` | Audit visible FAQ and generated JSON-LD | FAQPage schema contains only questions/answers rendered on the page. |
| `P10` | Simulate reduced motion and slow mobile network | No autoplay video or required WebGL; demo is lazy/on-demand and navigation/form remain usable. |

### Scoring rubric

Score each dimension **0–2**. A build passes only when it earns **18/20 or higher** and has no score of `0` in **conversion integrity**, **truthfulness**, **security**, or **accessibility/performance**.

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Conversion integrity | Competing CTAs or unclear path | Mostly consistent | One clear booking path everywhere |
| Vertical relevance | Generic copy | Some specific phrases | Credible industry objections, language, and case-study framing |
| Proof truthfulness | Invented claims | Ambiguous placeholders | Approved proof only; unverified proof omitted/labeled |
| Pricing clarity | Hidden or missing | Vague | Clear starting price and scope qualifier |
| Demo integrity | Fake/deceptive interaction | Partial fallback | Real integration or explicit configuration state |
| Lead lifecycle | No source/consent controls | Partial capture | Server validation, source/UTM/consent, honest follow-up state |
| SEO/AEO | Thin or keyword-stuffed | Basic metadata | Direct answers, structured visible content, robust technical SEO |
| Security/privacy | Browser secrets or over-collection | Basic protection | Server-only secrets, minimal data, consent and abuse controls |
| Accessibility/performance | Heavy/blocked/mobile-broken | Some best practices | Fast mobile experience, keyboard/a11y, reduced motion, light visuals |
| Scope discipline | Portfolio/agency drift | Minor drift | Funnel-first pages, content hub, proof pages, no bloat |

---

## 4. Recommended prompt settings

| Setting | Recommended value | Reason |
|---|---:|---|
| Model | Strong coding/reasoning model with tool access | The task spans frontend, backend integrations, SEO, and deployment. |
| Temperature | `0.2–0.4` | Keeps implementation decisions consistent and reduces invented copy/proof. |
| Max output / execution budget | High enough for multi-file implementation | The first pass includes routes, data flow, components, and integrations. |
| Execution mode | Build in phases with tests after each integration | Limits regressions and makes credential-dependent features explicit. |
| Retrieval | Provide approved proof, brand voice, legal copy, industry research, and booking configuration | Avoids factual invention and generic vertical content. |

---

## 5. Known limitations and launch prerequisites

- This prompt produces a reliable **implementation specification**, not live credentials, verified client proof, legal policies, or industry research.
- A working ElevenLabs demo, Cal.com booking widget, email/SMS follow-up, Supabase write path, and advertising pixels each require their respective credentials and explicit configuration.
- The `60 seconds` follow-up objective is an operational target, not a promise. Instrument provider delivery status and report failures transparently.
- The first page cannot be genuinely vertical-specific until `target_industry` is selected. Suggested first verticals from the brief are **roofing**, **HVAC**, or **med spa**.
