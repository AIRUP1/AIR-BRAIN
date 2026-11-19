"""Build the per-merchant call body for Speko's sessions_phone_create."""
from __future__ import annotations

from typing import Dict, Optional

from .leads import Lead

BASE_RULES = """You are an AI voice assistant making a short business call for {company}. You are an automated assistant and must say so at the start and again if asked.

Rules:
- Short, plain sentences. One question at a time. Pause for the answer.
- Confirm you reached the right business before anything else. If the business name is wrong, apologize, end the call politely and do not continue.
- Find out whether you are speaking with the owner or the person who decides about {topic}. If not, ask who is and when is a good time to reach them. Do not pressure anyone to hand over a name.
- Only describe the offer below. Never invent facts, prices, results or integrations. If asked something outside it, say a team member will follow up.
- Never ask for or repeat card, bank, SSN or account details.
- If anyone says stop, not interested, remove me or do not call: say "Understood, I will mark that now. Thank you," and end the call immediately. Do not try to overcome that objection.
- If they want a person, or are interested, offer a callback from a team member: collect only a first name and the best callback number, repeat the number back, and say the team will follow up. You cannot transfer the call live.
- Never claim to be human. Never imply a prior relationship.

Offer you may describe (nothing beyond this):
{offer}
"""

BRIEFING = """
Background on this business (from public web research, UNVERIFIED and possibly wrong):
{summary}
Possible point-of-sale system: {pos}
Use this only to ask better questions, such as "I understand you may use {pos_short}, is that right?". Never state it as fact, never say you researched them unless asked, and accept any correction immediately.
"""


def build_system_prompt(
    lead: Lead, offer: str, company: str, topic: str = "payments and point-of-sale"
) -> str:
    prompt = BASE_RULES.format(company=company, topic=topic, offer=offer.strip())
    if lead.research_summary or lead.pos_dm:
        pos = lead.pos_dm or "unknown"
        prompt += BRIEFING.format(
            summary=lead.research_summary or "none found",
            pos=pos,
            pos_short=pos.split("(")[0].strip() or "your current system",
        )
    prompt += f"\nThe business you are calling is: {lead.merchant_business_name}."
    return prompt


def build_first_message(lead: Lead, company: str) -> str:
    return (
        f"Hi, this is an automated assistant calling for {company}. "
        f"Am I speaking with someone at {lead.merchant_business_name}?"
    )


def build_call_body(
    lead: Lead,
    agent_id: str,
    offer: str,
    company: str,
    max_seconds: int = 180,
    topic: str = "payments and point-of-sale",
) -> Dict[str, object]:
    return {
        "to": lead.phone_number,
        "agentId": agent_id,
        "firstMessage": build_first_message(lead, company),
        "systemPrompt": build_system_prompt(lead, offer, company, topic),
        "maxDurationSeconds": max_seconds,
        "metadata": {"merchant_business_name": lead.merchant_business_name},
    }


def load_offer(path: Optional[str]) -> str:
    if not path:
        raise ValueError(
            "An offer file is required: describe exactly what the agent may say. "
            "Nothing is assumed about your product or pricing."
        )
    text = open(path, encoding="utf-8").read().strip()
    if not text:
        raise ValueError(f"Offer file {path} is empty")
    return text
