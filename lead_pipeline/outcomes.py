"""Turn a Speko session and transcript into the lead's outcome columns.

The rules are keyword heuristics over the merchant's own words. They are meant
to fill the sheet quickly, not to replace a person reading flagged calls.
"""
from __future__ import annotations

import re
from typing import Dict, Iterable, List

from .leads import Lead

OPT_OUT = (
    "do not call", "don't call", "dont call", "stop calling", "remove me",
    "take me off", "take us off", "unsubscribe",
)
NOT_INTERESTED = (
    "not interested", "no thanks", "no thank you", "we're good", "we are good",
    "not for us", "don't need", "do not need",
)
INTERESTED = (
    "interested", "tell me more", "sounds good", "sounds interesting",
    "send me", "email me", "sure, go ahead", "go ahead", "yes please",
)
WANTS_PERSON = (
    "speak to", "speak with", "talk to", "real person", "live person",
    "someone call", "call me back", "callback", "call back",
)
OWNER = ("i'm the owner", "i am the owner", "i own", "this is the owner", "owner here")
NOT_OWNER = ("not the owner", "i'm not the owner", "i am not the owner", "just an employee")
WRONG_BUSINESS = ("wrong number", "wrong business", "you have the wrong")


def _has(text: str, phrases: Iterable[str]) -> bool:
    return any(re.search(r"\b" + re.escape(p), text) for p in phrases)


def user_text(transcript: object) -> str:
    entries = transcript.get("entries", []) if isinstance(transcript, dict) else transcript
    parts: List[str] = [
        str(entry.get("text", ""))
        for entry in entries or []
        if entry.get("source") == "user"
    ]
    return " ".join(parts).lower()


def classify(session: Dict[str, object], transcript: object) -> Dict[str, object]:
    voicemail_info = session.get("voicemail") or {}
    verdict = str(voicemail_info.get("amdVerdict") or "").lower()
    voicemail = bool(voicemail_info.get("detected")) or verdict in ("machine", "voicemail")
    answered = bool(session.get("answered"))
    said = user_text(transcript)
    spoke = bool(said.strip())

    opt_out = _has(said, OPT_OUT)
    declined = _has(said, NOT_INTERESTED)
    wants_person = _has(said, WANTS_PERSON)
    interested = (_has(said, INTERESTED) or wants_person) and not (opt_out or declined)

    owner = ""
    if _has(said, NOT_OWNER):
        owner = "not owner"
    elif _has(said, OWNER):
        owner = "owner (self-identified)"

    flags: Dict[str, object] = {
        "called": True,
        "connected": answered and not voicemail and spoke,
        "failed": not answered,
        "voicemail": voicemail,
        "interested": interested,
        "connect_live_agent": wants_person and not opt_out,
        "opt_out": opt_out,
        "owner_prequalification": owner,
        "wrong_business": _has(said, WRONG_BUSINESS),
    }
    return flags


def apply_outcome(
    lead: Lead, flags: Dict[str, object], session_id: str = "", note: str = ""
) -> Lead:
    lead.called = True
    for name in ("connected", "failed", "voicemail", "interested", "connect_live_agent"):
        # An earlier positive result is never erased by a later retry.
        setattr(lead, name, bool(flags[name]) or getattr(lead, name))
    if flags["opt_out"]:
        lead.opt_out = True
    if flags.get("owner_prequalification"):
        lead.owner_prequalification = str(flags["owner_prequalification"])
    if flags.get("wrong_business"):
        lead.notes = (lead.notes + " wrong business/number").strip()
    if session_id:
        lead.session_id = session_id
    if note:
        lead.notes = (lead.notes + " " + note).strip()
    return lead
