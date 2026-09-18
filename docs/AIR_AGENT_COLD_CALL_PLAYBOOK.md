# AIR Agents Cold-Call Playbook

**Document owner:** Revenue Enablement  
**Audience:** AIR Agents, SDRs, account executives, and AI voice agents  
**Purpose:** Create permission-based, accurate conversations that qualify prospective customers for an AIR BRAIN discovery call or technical consultation.  
**Version:** 1.0 — 18 September 2026

> **Operating principle:** An AIR Agent earns the next conversation; it does not force a sale. Be clear about who is calling, respect opt-outs immediately, and never state that a capability, integration, outcome, customer, price, or security certification is available unless it has been approved for the prospect’s specific offer.

---

## 1. What AIR BRAIN Is

AIR BRAIN is an AI engineering and orchestration platform concept designed to help organizations route work to suitable AI systems, automate data and media workflows, deploy APIs, and monitor operational performance. The repository currently describes a modular architecture rather than a single fixed, generally available packaged product. Therefore, agents must frame the offering as a **tailored discovery, pilot, implementation, or integration conversation**—not a guaranteed off-the-shelf deployment.

| Capability area | Plain-English description | Prospect value to explore | Sales-safe language |
|---|---|---|---|
| **AI Brain Orchestrator** | A central routing layer that assesses a task and sends it to an appropriate subsystem. | Less manual triage; more consistent handling of AI tasks. | “We can explore a central orchestration layer for the AI workflows you already run.” |
| **Multi-Model Gateway** | A design for selecting among model providers and configuring fallbacks. | Better fit among quality, latency, cost, and resilience requirements. | “We can assess whether multi-model routing and fallback would reduce operational friction.” |
| **Agent Factory and Delegation** | A proposed system for creating task-specific agents, assigning work, and tracking capability and health. | Repeatable handling of specialized processes with human oversight. | “We can map which repeatable work is suitable for specialized agents and where people stay in control.” |
| **Recovery and Observability** | Error analysis, staged fallback, monitoring, and escalation concepts. | More visible failures and clearer recovery procedures. | “We can discuss a monitored fallback design rather than promising zero failures.” |
| **Data Intelligence / ETL** | Workflows for ingesting, validating, transforming, analyzing, and serving data. | Faster, more usable data flows. | “We can review the data workflow you want to make more reliable or actionable.” |
| **Media Generation Suite** | A pipeline concept for turning prompts into image, video, and promotional-media plans. | Faster production of campaign or content assets with review gates. | “We can evaluate a governed media workflow for your brand and approval process.” |
| **Respectful Data Collection** | A scraping design that checks robots.txt and rate limits requests. | More structured public-web research within agreed boundaries. | “We can discuss compliant, rate-limited collection only where your policy and the source terms allow it.” |
| **API and Deployment Layer** | FastAPI/MCP-compatible deployment patterns alongside container and monitoring options. | A path from prototype to controlled integration. | “We can identify what would be required to connect a workflow to your existing stack.” |

### Product and service boundaries

Do **not** represent development concepts as live production features. Do **not** promise autonomous actions, legal compliance, uptime, ROI, security certification, data residency, integrations, or model-provider access without written approval. Use these phrases instead:

- “We can assess fit during a discovery session.”
- “The exact scope, controls, and delivery plan would be confirmed with the technical team.”
- “That is an area we can evaluate; I do not want to overstate the current scope.”
- “Would it be useful to compare your current process with a proposed pilot workflow?”

---

## 2. Call Standard and CRM Discipline

Every call has one objective: **earn a relevant next step or accurately close the record.** A qualified next step is not merely a polite “send information.” It has an owner, a business problem, a date or time, and a documented reason to meet.

### Required CRM fields

| Field | What to capture | Example |
|---|---|---|
| Account and contact | Legal business name, prospect name, title, role, phone/email source. | “Northstar Logistics — Maya Chen, VP Operations.” |
| Persona | Economic buyer, technical buyer, operator, influencer, or gatekeeper. | “Technical evaluator.” |
| Current workflow | Tools, vendors, manual steps, and teams involved. | “Support tickets triaged manually; pilots use two LLM vendors.” |
| Pain / trigger | Specific friction and its business impact. | “No fallback when an API fails; backlog affects SLA.” |
| AIR BRAIN fit | Most relevant capability area and why. | “Orchestration + monitored fallback.” |
| Objection and response | Exact objection, concern, response given, and result. | “Already has vendor; asked about complementing existing stack.” |
| Consent / preference | Permission to contact, preferred channel, opt-out or do-not-call status. | “Email follow-up permitted; no calls before 10 a.m. local.” |
| Next step | Date/time, attendee(s), meeting type, owner, agenda. | “25-min discovery, Tue 10:30 a.m. CT, Maya + solutions lead.” |
| Disposition | See the disposition table below. | “Qualified discovery booked.” |

### Dispositions

| Disposition | Definition | Required next action |
|---|---|---|
| **Qualified discovery booked** | Pain, relevant stakeholder, and scheduled meeting are confirmed. | Send calendar confirmation and a short agenda. |
| **Nurture—timed** | Clear future trigger or date exists. | Create a dated task; do not repeatedly call before the agreed time. |
| **Nurture—education** | Interest exists but no immediate project. | Send only requested material; tag the capability area. |
| **Referral / transfer** | Prospect identified a more suitable stakeholder. | Verify name, role, and preferred introduction method. |
| **Not a fit** | The problem or segment is outside current offering. | Close reason accurately; do not force a meeting. |
| **No permission / opt-out** | Prospect asks not to be called or contacted. | Stop the call, mark the record immediately, and do not re-contact through the restricted channel. |
| **Wrong number / invalid record** | Contact information is not valid. | Correct or suppress the record according to CRM policy. |

---

## 3. TTS Delivery Setup for AIR Voice Agents

The goal is **calm, credible, human-sounding delivery**. The voice must not imitate a real person or conceal that it is an AI agent when disclosure is required by applicable policy or law. If the agent is automated, use the approved disclosure at the start of the call.

### Performance requirements

- Speak in plain U.S. English at a measured, conversational pace.
- Pause after the introduction and after every direct question.
- State the company and reason for the call before the pitch.
- Use the prospect’s name only when confidence is high; never guess pronunciation.
- Avoid fake urgency, exaggerated enthusiasm, or language that implies a prior relationship.
- Keep initial remarks below 30 seconds before asking permission or a discovery question.
- Use action tags only for pauses or a short breath; do not put emotional descriptors in square brackets.

### Recommended voice profiles

| Use case | Suggested voice character | Delivery direction |
|---|---|---|
| Executive / technical discovery | **Clear or informative** voice, such as Iapetus, Charon, or Sadaltager. | Measured, concise, quietly confident. |
| Operations / business conversation | **Friendly or warm** voice, such as Achird, Algieba, or Sulafat. | Helpful, practical, and unhurried. |
| Follow-up or referral call | **Easy-going** voice, such as Umbriel or Callirrhoe. | Familiar but not overly casual. |

### TTS prompt format

Use a single colon to separate the direction from the spoken content. The text before the colon is **not spoken**. Keep global direction in English and put only the actual script after the colon.

```text
Speak in U.S. English with a calm, warm, professional tone. Maintain a natural, conversational pace. Sound consultative rather than salesy; pause after questions: Hi [First Name], this is [Agent Name] with AIR BRAIN. We help teams explore practical ways to coordinate AI workflows, data processes, and monitored fallbacks. [short pause] Did I catch you with thirty seconds for a quick question?
```

```text
Speak in U.S. English with a clear, concise executive tone. Keep the delivery grounded and respectful: I understand. Before I let you go, may I ask one quick question? When an AI workflow or outside API fails today, does your team have a defined fallback process, or is it still handled manually?
```

> Do not synthesize an outbound call until contact permission, jurisdictional rules, company policy, and the relevant opt-out controls have been verified.

---

## 4. The Core Cold-Call Flow

### 4.1 The 30-second permission opener

**Use when:** Calling a relevant business contact with a credible reason to believe AI workflow, data operations, media operations, or model reliability may be relevant.

```text
Hi [First Name], this is [Agent Name] with AIR BRAIN. I know I’m calling out of the blue—have I caught you with thirty seconds?

[If yes.] Thank you. We work with teams that are trying to make AI and data workflows more dependable without adding a tangle of point tools. We help them assess orchestration, model fallback, task-specific agents, and monitored deployment designs. I’m not calling to assume that is a fit. I was curious: where does your team spend the most time coordinating AI, data, or automation work today?
```

**If the prospect does not have 30 seconds:**

```text
Of course. What would be a more respectful time to call, or would you prefer a brief email with the reason for my outreach?
```

### 4.2 The 60-second relevance bridge

Use the answer to make **one** relevant connection. Do not catalogue every capability.

| Prospect says | Relevant bridge | Discovery question |
|---|---|---|
| “We use several AI tools and vendors.” | “That is exactly where orchestration and model-routing design can become useful.” | “How do you decide which tool or provider handles each workflow today?” |
| “Our team manages a lot of data manually.” | “We often begin by mapping the ingestion, validation, and handoff points.” | “Which handoff creates the most rework or delay?” |
| “We need more reliable automations.” | “A monitored fallback and escalation path is often the practical starting point.” | “When something fails, who notices first and what happens next?” |
| “Marketing needs more content output.” | “A governed media workflow may help, but brand review and approvals should remain explicit.” | “Where does the approval process slow content down?” |
| “Our developers are building this in-house.” | “That can still be a fit if a modular architecture or deployment pattern would speed the build.” | “What part of the roadmap is consuming the most engineering time?” |

### 4.3 Discovery questions

Ask no more than two or three questions before offering a next step. Let the prospect answer fully.

1. **Workflow:** “Can you walk me through how that process works today?”
2. **Friction:** “Where does it break down, slow down, or require a person to intervene?”
3. **Impact:** “What does that delay or inconsistency affect—cost, customer response, throughput, or your team’s time?”
4. **Priority:** “Is improving that a current-quarter priority, or something you are watching for later?”
5. **Stakeholders:** “Who else is usually involved when you evaluate a workflow like this?”
6. **Success:** “If a pilot were useful, what would need to be true for your team to call it a success?”

### 4.4 Close for a concrete next step

```text
Based on what you described, a short discovery session could be useful. We would map the current workflow, identify the smallest sensible pilot, and confirm where human review, data controls, and integrations matter. Would a 25-minute session with a solutions lead next [day] or [day] be worthwhile?
```

If they agree:

```text
Great. To make it useful, I’ll note that the focus is [pain] and that [stakeholder] should be included. I have [two specific times in the prospect’s time zone]. Which is better?
```

---

## 5. Persona-Specific Pitch Examples

### 5.1 Operations leader

**Positioning:** Reduce manual coordination and clarify recovery when automations fail.

```text
Hi [First Name], this is [Agent Name] with AIR BRAIN. I know this is unexpected—do you have thirty seconds?

We speak with operations leaders whose teams are stitching together AI tools, data feeds, and manual handoffs. AIR BRAIN is designed to help map and coordinate those workflows, with monitored fallback paths when something fails. I’m curious: is there a workflow your team has to watch manually because it is too important to leave unattended?
```

**Follow-up bridge:**

```text
That sounds like a good fit for a focused workflow review. Rather than replacing everything, the goal would be to identify one handoff, failure point, or repetitive decision that could be made more visible and reliable. Would a 25-minute discovery session be useful?
```

### 5.2 CIO, CTO, or VP Engineering

**Positioning:** Architecture, controlled deployment, provider flexibility, and observability.

```text
Hi [First Name], [Agent Name] with AIR BRAIN. I’m reaching out because many engineering teams are being asked to operationalize AI faster while keeping control of routing, fallbacks, logging, and deployment. We are not calling to claim a plug-and-play answer; we help teams evaluate a modular orchestration and API architecture around their existing stack. How are you handling model choice and failure recovery across AI workflows today?
```

**Follow-up bridge:**

```text
If it is useful, a technical discovery could focus on one workflow, its data boundaries, provider dependencies, and the controls that would be needed before a pilot. Would it make sense to include the person responsible for platform architecture?
```

### 5.3 Data / analytics leader

**Positioning:** More dependable ingestion, validation, transformation, and accessible intelligence.

```text
Hi [First Name], this is [Agent Name] with AIR BRAIN. I’ll be brief. We work with teams evaluating more structured data workflows—from ingestion and validation through analysis and deployment—especially where manual cleanup or brittle handoffs slow down decisions. Where does your team lose the most time between raw data arriving and someone being able to use it confidently?
```

### 5.4 Marketing or content leader

**Positioning:** Governed media workflows, not automated brand replacement.

```text
Hi [First Name], [Agent Name] with AIR BRAIN. We are speaking with content teams that want faster ideation and production without losing approval and brand controls. AIR BRAIN includes a media workflow concept that can connect prompt development, image or video planning, and review steps. I’m curious: is your larger bottleneck content volume, approval time, or reuse across channels?
```

### 5.5 Existing AI program / partner-led team

**Positioning:** Complement rather than displace.

```text
It sounds like you already have meaningful work underway. I’m not suggesting you replace it. The question may be whether a focused orchestration, fallback, or observability layer could make the existing program easier to operate. Would it be unreasonable to have a short technical conversation to decide whether there is any gap at all?
```

---

## 6. The DELUXE ENABLE Rejection-Overcome Process

A rejection is information, not a challenge to defeat. The purpose of objection handling is to understand the concern, offer a truthful reframing if one exists, and either earn a proportionate next step or exit cleanly. Do not argue, pressure, disguise intent, or continue after an opt-out.

### DELUXE: Understand before answering

| Step | Meaning | Agent behavior | Example language |
|---|---|---|---|
| **D — Defuse** | Lower pressure immediately. | Thank the prospect; acknowledge the interruption. | “I understand, and I appreciate you telling me directly.” |
| **E — Examine** | Clarify the actual objection. | Ask one short, neutral question only if the prospect is open. | “Is the timing the issue, or is this simply outside your priorities?” |
| **L — Listen** | Let them finish. | Do not interrupt or rush to a script. | “That makes sense.” |
| **U — Uncover** | Identify the underlying condition. | Find the project status, concern, owner, or trigger. | “What would need to change for this to become relevant?” |
| **X — eXchange the frame** | Offer one accurate alternative perspective. | Connect only a relevant AIR BRAIN capability; do not overclaim. | “Rather than replacing your stack, a discovery could examine one failure point around it.” |
| **E — Evidence and exit path** | Give bounded evidence or offer a clean close. | State only verified scope; propose one proportional action. | “I can send a one-page workflow outline, or I can close the loop—what is more useful?” |

### ENABLE: Convert qualified interest into an ethical next step

| Step | Meaning | Agent behavior | Example language |
|---|---|---|---|
| **E — Earn permission** | Ask before continuing. | Respect a no. | “Would you be open to one quick question so I can tell whether this is relevant?” |
| **N — Narrow the outcome** | Define the smallest next action. | Avoid an open-ended sales meeting. | “A 25-minute workflow assessment focused only on fallback and ownership.” |
| **A — Align the module** | Match one capability to one pain. | Do not feature-dump. | “The relevant area appears to be monitored orchestration, not media generation.” |
| **B — Book specifically** | Offer two times and clear attendees. | Confirm time zone and agenda. | “Would Tuesday at 10:30 or Wednesday at 2:00 work?” |
| **L — Log completely** | Preserve what was learned in the CRM. | Record exact concern, trigger, stakeholders, and consent. | “Log: existing vendor; revisit after Q4 platform review.” |
| **E — Exit respectfully** | End with clarity. | Never linger after refusal. | “Thank you for your time. I’ll follow the preference you gave me.” |

### Decision rule

- **Clear opt-out, do-not-call, or no-contact request:** Stop immediately. Confirm the request and update the CRM. **Do not use DELUXE to continue.**
- **Firm but courteous rejection:** Use at most one clarification question and one relevant reframe. If there is no opening, close the call.
- **Ambiguous objection:** Use DELUXE, then either ENABLE a specific next step or document a timed nurture event.
- **Material technical, legal, security, pricing, or integration question:** Do not improvise. Capture it verbatim and offer a qualified follow-up with the appropriate owner.

---

## 7. Objection and Rejection Handling Library

### 7.1 “I’m not interested.”

**Intent to diagnose:** Is this a polite brush-off, wrong timing, or genuine lack of need?

```text
I understand. I’ll keep this brief. Is that because AI workflow coordination is not a priority right now, or because you already have a process you are happy with?
```

**If they share a reason:**

```text
That is helpful. Based on that, I do not want to force a fit. If it becomes relevant later, would a brief overview focused on [relevant area] be useful, or should I simply close the loop?
```

**CRM:** Record the exact reason. If they decline further contact, mark the appropriate preference and stop.

### 7.2 “We already have an AI vendor / we’re building in-house.”

```text
That makes sense, and I would not assume you should replace either. Some teams speak with us to examine the operational layer around an existing program—such as routing, monitoring, fallback, or a particular data workflow. Is there any part of the current build that is harder to operationalize than expected?
```

**If no:**

```text
Understood. I’ll leave it there. If the program reaches a point where a workflow review would be useful, AIR BRAIN can be a resource.
```

### 7.3 “Just send me information.”

```text
Happy to. So I do not send generic material, which area is most relevant: coordinating multiple AI tools, improving data workflows, monitored fallback and deployment, or governed media production?
```

**After answer:**

```text
Thank you. I’ll send a concise note on that area. Would it be appropriate to include one question for a follow-up after you have reviewed it, or would you prefer no follow-up?
```

**CRM:** Log topic, delivery channel, and whether follow-up permission was granted. Never treat an email request as automatic permission for repeated calling.

### 7.4 “I’m too busy.”

```text
I understand. Would you prefer I send a three-sentence summary, or is there a specific time when a brief call would be more useful?
```

If they name a time, confirm it. If they do not, end cleanly.

### 7.5 “We do not have budget.”

```text
Understood. A discovery call would not commit you to a project, but it may not be the right use of time without a live priority. Is there a particular planning cycle or operational trigger when evaluating a workflow improvement becomes more realistic?
```

Do not invent pricing or discounts. If there is a trigger, set a **timed nurture** task; otherwise close as not currently active.

### 7.6 “AI is risky / our security team will never allow this.”

```text
That is a reasonable concern. Responsible use requires clear data boundaries, access controls, human review, and an approved architecture; I should not claim otherwise. Would a technical discovery focused on your requirements be useful, or would you rather wait until there is an active initiative?
```

**Escalate:** Capture security requirements verbatim. Do not offer unsupported compliance claims.

### 7.7 “We were burned by an automation project before.”

```text
I can understand why you would be cautious. Rather than talk about a broad transformation, the useful question may be whether there is one narrow workflow with a clear owner, success measure, and human fallback. What went wrong with the prior project—scope, adoption, reliability, data, or ownership?
```

**Reframe only if appropriate:**

```text
Thank you. A small discovery can test whether that condition could be designed differently this time. If not, it is better to know that early.
```

### 7.8 “I’m not the decision-maker.”

```text
Thank you for clarifying. Who owns [AI operations / data automation / platform architecture] on your team? If you are comfortable, would you prefer to make an introduction, or should I send you a short note that you can forward?
```

Do not pressure them for a personal number or undocumented referral. Record their role and the recommended contact route.

### 7.9 “Call me later.”

```text
Certainly. What date and time would you prefer, and is there a particular topic that would make the follow-up useful?
```

Repeat the agreed time, time zone, and topic. If they cannot name a time, offer email or close gracefully.

### 7.10 “Remove me / do not call again.”

```text
Absolutely. I’ll mark that preference now. Thank you for letting me know, and I will not continue the call.
```

**Required action:** End the call. Mark the CRM record immediately according to company policy. Do not redirect to email, ask another question, or attempt a rebuttal.

---

## 8. Full Example Conversations

### Example A — Operations leader with a live reliability issue

**Goal:** Book a discovery call for monitored orchestration and fallback.

```text
Agent: Hi Maya, this is Jordan with AIR BRAIN. I know I’m calling unexpectedly—have I caught you with thirty seconds?

Prospect: I have a minute.

Agent: Thank you. We help teams assess AI and data workflows that have become difficult to coordinate or recover when a dependency fails. I am not calling to assume there is a fit. Where does your operations team spend the most time watching an automation manually?

Prospect: We have an order-status workflow that breaks when an external data feed times out.

Agent: That is helpful context. When it times out, who notices first, and what does the team do next?

Prospect: Customer service finds out after customers complain, then someone runs a manual process.

Agent: Understood. The most relevant AIR BRAIN area would be a monitored workflow and defined fallback—not a broad AI overhaul. A short discovery could map that one workflow, its handoffs, and a practical pilot boundary. Would a 25-minute session next Tuesday or Wednesday be useful?

Prospect: Wednesday might work.

Agent: Great. I have Wednesday at 2:00 or 3:30 p.m. Central. Which is better, and should anyone from customer service or engineering join?
```

**CRM note:** “Live external-feed timeout impacts order-status workflow; CS detects via complaints; manual recovery. Fit: monitoring + fallback. Discovery booked Wed 2:00 CT; invite operations, CS, engineering.”

### Example B — Technical leader says they already have a vendor

**Goal:** Qualify whether AIR BRAIN complements existing architecture.

```text
Agent: Hi Daniel, this is Priya with AIR BRAIN. Do you have thirty seconds for the reason I’m calling?

Prospect: We already have an AI vendor.

Agent: That makes sense. I am not suggesting you replace it. Some teams talk with us only when the operational layer around their existing tools—such as model routing, logging, fallback, or an API handoff—needs more structure. Is any part of running the current program more complicated than expected?

Prospect: Honestly, vendor lock-in and failure handling are concerns, but we are early.

Agent: That is a useful distinction. Rather than a sales demo, a technical discovery could identify whether a provider-agnostic routing and fallback design is worth considering for your roadmap. Would a short architecture conversation after the current phase is complete be better, or should I send a concise outline for your team to review now?

Prospect: Send something and circle back in Q4.

Agent: Absolutely. I’ll send a brief outline focused on routing and fallback, and I’ll note Q4 as the agreed check-in. Is email the best channel?
```

**CRM note:** “Existing AI vendor; concerns: lock-in and failure handling; early phase. Requested architecture outline; permission to circle back Q4 by email.”

### Example C — Busy marketing leader requests information

**Goal:** Send relevant material and gain explicit follow-up preference.

```text
Agent: Hi Elena, [Agent Name] with AIR BRAIN. I will be brief. We are speaking with content teams that want to speed ideation and production while keeping brand approval explicit. Is content volume or approval time the larger bottleneck for your team?

Prospect: I’m walking into a meeting. Send me something.

Agent: Happy to. To make it useful, should I focus it on governed media workflows, or on coordinating the underlying AI tools?

Prospect: Approval workflows.

Agent: Thank you. I’ll send a concise note on governed media production and approvals. Would you like me to follow up after you review it, or should I wait for you to reach back out?

Prospect: Follow up next month.

Agent: Perfect. I’ll make that a next-month email follow-up. Thank you for your time.
```

**CRM note:** “Asked for information during meeting transition. Topic: approval workflows. Explicit permission: email follow-up next month.”

### Example D — Firm rejection and compliant close

```text
Agent: Hi [First Name], [Agent Name] with AIR BRAIN. Have I caught you with thirty seconds?

Prospect: No. Take me off your list.

Agent: Absolutely. I’ll mark that preference now. Thank you, and I will not continue the call.
```

**CRM note:** “Requested no further calls. DNC applied immediately. No additional outreach attempted.”

---

## 9. Voicemail and Follow-Up Templates

### 9.1 Voicemail (20–25 seconds)

```text
Hi [First Name], this is [Agent Name] with AIR BRAIN. I’m reaching out because we help teams assess more dependable AI, data, and automation workflows—especially where routing, fallbacks, or manual coordination are becoming difficult. I’ll send a short note with context. If this is relevant, you can reach me at [number]. Again, [number]. Thank you.
```

### 9.2 Follow-up email after a live conversation

**Subject:** AIR BRAIN follow-up — [prospect’s stated workflow]

```text
Hi [First Name],

Thank you for the brief conversation today. You mentioned that [specific pain / workflow]. Based on that, the potentially relevant AIR BRAIN area is [one capability area], which we would evaluate as a scoped workflow or technical discovery rather than assume as a prebuilt solution.

As agreed, the next step is [meeting date/time OR requested information]. The discussion would focus on [two agenda points] and would include [attendees, if known].

Best,
[Name]
[Role]
[Contact details]
```

### 9.3 Re-engagement email after timed permission

**Subject:** Checking in as agreed — [topic]

```text
Hi [First Name],

I’m following up at the time you suggested regarding [topic]. When we last spoke, you noted [relevant trigger or concern]. Has that become an active priority, or would a later check-in be more appropriate?

If useful, we can schedule a brief discovery focused only on [one specific workflow]. If not, I will update the record accordingly.

Best,
[Name]
```

---

## 10. Quality Assurance Scorecard

Score each reviewed call from 0–2 per category. A call that ignores an opt-out automatically fails compliance review regardless of its total score.

| Category | 0 | 1 | 2 |
|---|---|---|---|
| Identity and purpose | Identity or reason unclear. | Partially clear. | Clear identity, company, and reason for outreach. |
| Permission and pacing | Pushy or uninterrupted pitch. | Asks permission but rushes. | Earns permission, pauses, and adapts to time available. |
| Product accuracy | Overstates capabilities or outcomes. | Mostly accurate, some vague claims. | Bounded, accurate, and clearly scoped. |
| Discovery | Feature-dump; no questions. | One generic question. | Relevant questions uncover workflow, impact, and ownership. |
| Objection handling | Argues or repeats pitch. | Acknowledges but weakly clarifies. | Uses DELUXE respectfully and exits when appropriate. |
| Next step | No action or vague promise. | Next action lacks owner/date. | Specific meeting or consent-based nurture action recorded. |
| CRM hygiene | Missing notes or disposition. | Basic notes only. | Complete fields, exact objections, preferences, and next steps. |
| Compliance | Opt-out mishandled or prohibited claim. | No issue observed. | Explicitly respects contact preferences and uses approved language. |

### Coaching signals

- **High conversion, low quality:** Review for pressure, unsupported claims, and improperly qualified meetings.
- **Low conversion, high quality:** Improve targeting and relevance hypotheses before changing the agent’s tone.
- **Repeated “send information” outcomes:** Audit whether the agent asks a purposeful qualifying question before sending material.
- **Frequent security objections:** Route a technical security FAQ request to the product owner; do not improvise certifications or guarantees.

---

## 11. Pre-Call and Post-Call Checklists

### Pre-call

- [ ] Confirm contact source, account relevance, and local contact rules.
- [ ] Review CRM history, prior objections, and stated preferences.
- [ ] Choose one likely capability area; do not prepare a broad feature dump.
- [ ] Identify one relevance hypothesis and two discovery questions.
- [ ] Confirm approved claims, current offer, and the correct next-step owner.
- [ ] Configure the selected voice and TTS director instruction.

### Post-call

- [ ] Log exact words used for material objections or requests.
- [ ] Update consent, contact preference, and opt-out status immediately.
- [ ] Record workflow, pain, impact, stakeholder, fit area, and disposition.
- [ ] Create the next task only when permission and timing are clear.
- [ ] Send only the content requested and only through the permitted channel.
- [ ] Escalate pricing, legal, security, integration, or scope questions to an authorized human owner.

---

## 12. Agent Quick Reference

> **Open:** “Hi [Name], this is [Agent] with AIR BRAIN. I know I’m calling unexpectedly—have I caught you with thirty seconds?”

> **Explore:** “Where does your team spend the most time coordinating AI, data, or automation work today?”

> **Bridge:** “Based on that, the relevant area may be [one capability], not a broad replacement program.”

> **Close:** “Would a 25-minute discovery to map that one workflow be worthwhile?”

> **When rejected:** “I understand. Is it timing, priority, or an existing process you are satisfied with?”

> **When asked to stop:** “Absolutely. I’ll mark that preference now. Thank you, and I will not continue the call.”

This playbook should be reviewed whenever the AIR BRAIN product scope, approved services, regional calling policy, or CRM workflow changes.
