# AIR AGENTS Software & Deluxe Merchant Services
## Detailed Business-Support Feature Comparison

**Status:** Evidence-based comparison of the current AIR-BRAIN repository and public Deluxe Merchant Services materials  
**As of:** September 30, 2026  
**Audience:** Business owners, operators, and implementation teams evaluating workflow software alongside payment acceptance

> **Important scope:** No single software configuration or payment provider is automatically right for every business. This comparison shows where **AIR AGENTS / AIR-BRAIN** and **Deluxe Merchant Services** can support a broad range of operating models. Final fit depends on the business’s industry, payment channels, current systems, risk profile, written pricing, eligibility, contract terms, implementation scope, and required controls.

## Executive view

| Solution | Primary role | Best use |
|---|---|---|
| **AIR AGENTS / AIR-BRAIN** | A tailored software, workflow, and operations layer. The current repository documents consent-aware intake, protected workspace records, AI/data workflow concepts, API patterns, tasking, partner coordination, and campaign-brief operations. | Organizing work around the customer journey: lead intake, follow-up, operational tasks, approved integrations, data workflows, monitoring, and custom automation. |
| **Deluxe Merchant Services** | A merchant-services and payment-acceptance solution. Public materials describe POS and smart terminals, online payment pages, virtual terminal, mobile payments, ACH/eCheck options, reporting, and business-software integrations. | Accepting and managing payments in person, online, through mobile devices, and through invoicing or remote workflows. |
| **Eliot Management Group by Deluxe** | A merchant-services channel that publicly describes Deluxe payment products and selected programs, including gift/loyalty, device-dependent surcharge/cash-discount options, and next-day funding availability. | Merchant discovery, payment solution evaluation, and a current written offer tailored to the business. |

**Bottom line:** AIR AGENTS can support the **workflow around the business**; Deluxe can support the **payment transaction and checkout layer**. A combined design may support many business models, but the repository does **not** currently contain a live Deluxe/Eliot integration. Any connection requires a defined API/export/webhook scope, security review, explicit authorization, and a human-owned implementation plan.

---

## Detailed feature comparison

| Business need / feature | AIR AGENTS / AIR-BRAIN support | Deluxe Merchant Services support | What this means for a business |
|---|---|---|---|
| **Customer discovery and needs assessment** | Supports tailored intake, lead context, customer workflow mapping, and AI-assisted discovery concepts. | Merchant-services consultation and payment-solution evaluation; exact advisory process must be confirmed. | Use AIR AGENTS to capture the broader business problem; use Deluxe/Eliot to evaluate the payment-specific solution. |
| **Website lead intake** | Current architecture documents consent-aware public lead intake, validation, anti-spam handling, and assignment to an accountable operator. | Not positioned in the cited materials as a lead-CRM or public inquiry platform. | AIR AGENTS can own the pre-sale inquiry workflow; Deluxe can be a selected downstream payment partner. |
| **CRM-style lead, partner, and task operations** | Current workspace model includes leads, partners, tasks, campaign briefs, ownership, status tracking, and audit events. | Not described as a CRM/work-management system in the cited public merchant-services materials. | AIR AGENTS can coordinate people and follow-up around a merchant evaluation or customer journey. |
| **In-store card acceptance** | Not a payment processor and does not accept card payments. | Public materials describe POS systems, smart terminals, and in-person tap, dip, swipe, and digital-wallet acceptance. | Deluxe is the payment layer; AIR AGENTS may support surrounding operations only. |
| **Online checkout** | Can support custom workflow/API design; no built-in payment checkout is verified. | Public materials describe customized online payment pages and credit, debit, and ACH options. | Deluxe is a fit candidate for payment acceptance; AIR AGENTS could support intake, marketing, or related workflows after approved integration design. |
| **Mobile payment acceptance** | Can support mobile-oriented workflow design; no payment-acquiring capability is documented. | Public materials describe the dlxPAY app and contactless/EMV payment capability. | Field teams and mobile merchants should validate device availability, app eligibility, and workflow fit directly with Deluxe/Eliot. |
| **Virtual terminal / remote payments** | No payment terminal is documented. | Public materials describe a browser-based virtual terminal for remote or phone payments, cards, ACH eChecks, recurring payments, and invoicing. | Suitable for businesses that invoice, accept remote orders, or collect payment after service—subject to a current offer and policy review. |
| **ACH and eCheck** | Can organize workflow, follow-up, and approved data movement; it must not handle bank credentials or raw payment data. | Public materials describe ACH in online checkout and ACH eCheck through virtual-terminal workflows. | Payment-method availability and pricing must be confirmed for the merchant’s use case. |
| **Recurring payments and invoicing** | Can coordinate customer-success tasks, notifications, and approved system handoffs; no billing engine is verified. | Public materials describe online invoice viewing/payment and recurring-payment/invoicing options through the virtual terminal. | Deluxe may cover billing acceptance while AIR AGENTS supports non-payment workflow and communication. |
| **POS, inventory, and employee operations** | Can evaluate or integrate a custom operating workflow; no packaged POS/inventory module is represented as live. | Public materials describe POS features including inventory management, employee time management, and cloud-based reporting analytics. | Retail, restaurant, and service businesses should verify exact POS feature availability and migration requirements. |
| **Payment reporting and business insights** | Can support data-pipeline, analytics, and dashboard concepts around approved business data. | Public materials describe transaction reporting, sales tracking, trend monitoring, and business insights. | Deluxe can provide payment-system reporting; AIR AGENTS may combine approved aggregates with other operational data for broader analysis. |
| **AI workflow orchestration** | Current materials describe a tailored orchestration concept for routing work, model selection, agent delegation, recovery, and monitored automation. | Not described as an AI workflow-orchestration product. | AIR AGENTS is the relevant layer for custom AI/data-process design; exact scope is discovery- and implementation-dependent. |
| **Data collection and transformation** | Current materials describe data-ingestion, validation, transformation, and analysis concepts, plus controlled public-web collection. | Payment data/reporting is available within the merchant-services product scope; custom data access must be validated. | Use only approved, minimum-necessary aggregates. Do not move payment credentials or cardholder data into an AIR workflow. |
| **Creative, campaign, and customer communications** | Current service catalog includes AI growth systems, creative launchpad, media/production systems, and campaign briefs tied to conversion objectives. | Not described as a campaign-production or CRM platform. | AIR AGENTS can support customer acquisition and campaign operations; Deluxe handles checkout/payment functions. |
| **API, webhooks, and custom integrations** | Architecture documents FastAPI/MCP-compatible patterns, verified webhooks, signed events, audit logging, and approved integrations. | Public materials state that integrated software solutions are available; dlxPAY materials mention custom-app SDK integration. | A live connection requires technical validation, signed/authenticated access, a data map, testing, and approved commercial terms. |
| **Consent, access control, and auditability** | Architecture documents explicit contact consent, role-based access, private storage, append-only audit events, and secure integration boundaries. | Public materials describe cardholder-data protection and fraud/security features but do not replace a business’s own governance review. | AIR AGENTS can coordinate protected operational records; payment data must remain in approved payment environments and within applicable security obligations. |
| **Customer support** | Current repo describes accountable owners, workflow tasks, and escalation patterns; it does not claim a 24/7 product-support service. | Public materials state 24/7/365 merchant support. | Support expectations, response times, and escalation ownership should be documented in the written agreement. |
| **Funding and settlement** | Does not fund or settle payment transactions. | Deluxe/Eliot publicly describe payment processing and Eliot’s next-day funding availability; eligibility, cutoff times, and terms must be confirmed. | Never promise funding timing without a merchant-specific written confirmation. |
| **Gift cards and loyalty** | Can support related campaign or operations workflows if scoped; no native gift-card/loyalty product is verified. | Eliot publicly describes gift-card and loyalty programs. | Confirm product availability, pricing, redemption rules, and POS/device compatibility. |
| **Surcharge or cash-discount programs** | Can support customer-communication and process design only; it must not determine legal/compliance eligibility. | Eliot publicly describes a surcharge program on Dejavoo devices and a cash-discount option on Sound POS. | This is device- and merchant-dependent. Obtain a written program description and qualified compliance review before adoption. |
| **Merchant-pricing analysis** | Can organize a side-by-side cost model based on approved, redacted statement/quote data; it must not invent savings. | Eliot publicly states it will review written competitor offers; actual merchant rate, fees, and terms require a current written quote. | Compare effective cost, fee categories, equipment, term length, early-termination conditions, and funding terms—not only headline rates. |
| **Business-lending coordination** | Current service catalog includes business-lending coordination, expressly limited to readiness and authorized partner communication—not credit decisions or offers. | Merchant services is distinct from business lending in the cited material. | Keep lending and payment-processing decisions separate and human-owned. |
| **Implementation model** | Tailored discovery, pilot, implementation, or integration conversation; the repository is not described as a single fixed, generally available packaged product. | Merchant-services deployment should be defined in a merchant-specific written offer, including hardware, onboarding, migration, pricing, and support. | The combined solution should begin with one narrow workflow and an implementation checklist. |
| **Pricing** | No published, universal AIR AGENTS price is established in the current repository. Scope must be defined. | Public merchant-services pages describe capabilities, not a universal public rate card for every merchant. | Treat both as quote/scoping conversations. Do not claim a rate, savings figure, free equipment, or outcome without current written evidence. |

---

## Fit across common business models

| Business model | How AIR AGENTS may help | How Deluxe Merchant Services may help | First validation questions |
|---|---|---|---|
| **Local retail** | Lead intake, customer follow-up workflows, campaign briefs, operational tasks, and optional reporting integrations. | In-store POS/smart terminal, card and digital-wallet acceptance, inventory-oriented POS capabilities, and reporting. | Number of locations, current POS, inventory needs, average ticket, and desired loyalty/gift-card experience. |
| **Restaurant, café, or food service** | Campaign workflow, local customer communications, approved operational analytics, and tailored integration design. | In-person acceptance and POS options; verify restaurant-specific features, online ordering, tips, and integrations. | Service model, table/quick service needs, online ordering, delivery tools, peak volume, and existing POS. |
| **Professional services** | Lead/CRM workflows, appointment or proposal follow-up, document/task coordination, and custom data workflows. | Invoice payment, virtual terminal, ACH/eCheck, and recurring-payment capabilities where available. | Invoice cadence, remote/phone payments, recurring billing, accounting integration, and payment authorization workflow. |
| **E-commerce** | Customer-acquisition workflows, campaign/creative operations, data-pipeline design, and integration planning. | Online payment page, credit/debit/ACH options, and integrated software support. | Store platform, checkout requirements, subscriptions, chargeback concerns, and API/SDK needs. |
| **Field service or mobile business** | Mobile lead intake, scheduling/dispatch workflow design, quote follow-up, and task accountability. | Mobile payment acceptance via dlxPAY and compatible device options, subject to merchant-specific confirmation. | Service territory, offline needs, ticket size, device preference, invoicing, and payment timing. |
| **Subscription, membership, or invoice-based business** | Customer onboarding, renewal/workflow reminders, customer-success tasks, and analytics design. | Virtual-terminal recurring payments, invoicing, online payment, and payment-reporting capabilities. | Billing frequency, retry/dunning needs, ACH/card mix, customer portal needs, and accounting reconciliation. |
| **Multi-location or franchise operation** | Cross-location workflows, partner/owner task assignment, campaign briefs, integration architecture, and controlled reporting. | Multiple payment locations, POS/reporting options, and integrated software solutions; availability must be confirmed. | Number of entities/locations, settlement structure, hardware fleet, roles, reporting, and support requirements. |
| **Nonprofit, events, or community organization** | Campaign brief, donor/community communications, volunteer/partner coordination, and event workflow design. | Payment acceptance options; confirm donation, event, recurring-giving, and receipt requirements. | Donation model, event volume, online/offline mix, PCI/privacy controls, and donor-system integration. |
| **Regulated, high-risk, or specialized industry** | Tailored workflow discovery and documented governance boundaries; no promise of an approved integration or payment capability. | Potential payment evaluation, subject to underwriting, industry eligibility, pricing, compliance, and provider approval. | Industry classification, licensing, prohibited activities, chargeback history, data requirements, and legal/compliance review. |

---

## Recommended combined operating model

| Stage | AIR AGENTS role | Deluxe / Eliot role | Human decision point |
|---|---|---|---|
| **1. Discover** | Capture needs, workflows, deal-breakers, decision owners, and consent. | Explain relevant payment categories and request a merchant-specific evaluation. | Confirm the business problem and authorized contacts. |
| **2. Baseline** | Organize a redacted current statement/quote, channel mix, current systems, and pain points. | Review payment acceptance needs and provide a written proposal if requested. | Validate data scope; do not share restricted payment data. |
| **3. Compare** | Build a cited comparison matrix with cost, channels, integrations, support, controls, and implementation trade-offs. | Confirm product availability, rates, hardware, funding, and program terms for the specific merchant. | Review written offer, contract, compliance, and technical fit. |
| **4. Pilot** | Design the smallest sensible workflow pilot, integration boundary, monitoring, and task ownership. | Configure only the approved payment solution and onboarding path. | Approve scope, testing, migration, and customer communication plan. |
| **5. Operate** | Support ongoing workflow, reporting aggregates, issue routing, and approved improvement work. | Process payments and provide merchant-services support under the agreed plan. | Monitor outcomes, security, service levels, and contract obligations. |

---

## Critical boundaries and verification checklist

Before representing a combined solution to a business, verify:

1. **Merchant-specific payment offer:** rate model, all fee categories, equipment costs, contract term, early-termination language, funding timing, and program eligibility.
2. **Payment workflow:** in-store, online, mobile, virtual-terminal, invoicing, recurring, ACH, and digital-wallet needs.
3. **Technical compatibility:** current POS, e-commerce, accounting, CRM, booking, inventory, and any required API/SDK details.
4. **Data boundary:** payment credentials and cardholder data stay out of AIR AGENTS workflows unless a separately approved, compliant architecture says otherwise. AIR AGENTS should use only minimum-necessary, non-sensitive aggregates.
5. **Compliance and risk:** qualified owners review PCI, surcharge/cash-discount requirements, industry regulations, contract terms, and underwriting—not the AI system.
6. **Implementation ownership:** name the business owner, merchant-services owner, technical owner, and success measures before changing a payment workflow.
7. **Truthful positioning:** do not promise universal business support, best rates, approval, savings, next-day funding, free equipment, compliance, uptime, integrations, or ROI without documented merchant-specific evidence.

---

## Sources and evidence status

| Source | Evidence used | Status |
|---|---|---|
| [AIR AGENTS service catalog](../air_agents_api/main.py) | Current service-catalog descriptions for AI growth systems, partner operations, consent-aware voice workflows, media/production systems, lending coordination, and creative launchpad. | Repository source; current at review date. |
| [AIR AGENTS architecture](AIR_AGENTS_ARCHITECTURE.md) | Consent-aware intake, FastAPI, role-based access, Supabase target architecture, private storage, verified webhooks, auditability, and operational records. | Repository architecture/target-state documentation; not proof that every integration is live. |
| [AIR AGENTS cold-call playbook](AIR_AGENT_COLD_CALL_PLAYBOOK.md) | Tailored-discovery positioning and explicit no-overclaim boundaries for AIR-BRAIN capabilities. | Repository operating guidance; current at review date. |
| [Deluxe Merchant Services — payment processing](https://www.deluxe.com/merchant-services/payment-processing/) | POS, smart terminals, online payment page, dlxPAY, virtual terminal, credit/debit/ACH, recurring/invoicing, reporting, and integrated software statements. | Official public source accessed September 30, 2026. |
| [Deluxe Merchant Services — accept payments](https://www.deluxe.com/merchant-services/accept-payments/) | In-store, online, and mobile acceptance; payment types; mobile features; reporting; integration statements; support claims. | Official public source accessed September 30, 2026. |
| [Eliot Management Group by Deluxe — services](https://www.emgway.com/services/) | Public descriptions of payment processing, selected surcharge/cash-discount programs, gift/loyalty, and next-day funding availability. | Official public source accessed September 30, 2026; merchant eligibility and terms must be re-verified. |

*This comparison is operational and informational. It is not payment, legal, tax, PCI, security, underwriting, or financial advice.*
