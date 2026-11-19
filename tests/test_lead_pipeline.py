import json
from pathlib import Path

import pytest

from lead_pipeline import cli
from lead_pipeline.leads import (
    Lead,
    LeadFileError,
    callable_reason,
    clean_leads,
    load_leads,
    load_suppression,
    normalize_phone,
    save_leads,
)
from lead_pipeline.memory import ResearchMemory
from lead_pipeline.outcomes import apply_outcome, classify
from lead_pipeline.prompt import build_call_body, load_offer
from lead_pipeline.research import build_queries, research_lead

SHEET = (
    "Merchant Business Name,Phone number,POS / DM,Owner / Pre-Qualification\n"
    "Joe's Diner,(210) 555-0142,Clover,\n"
    "Bella Salon,1-210-555-0177,,Owner\n"
    "Joe's Diner,210.555.0142,,\n"
    "No Phone Cafe,12345,,\n"
)


def write_sheet(tmp_path: Path) -> Path:
    path = tmp_path / "in.csv"
    path.write_text(SHEET, encoding="utf-8")
    return path


def test_phone_normalization():
    assert normalize_phone("(210) 555-0142") == "+12105550142"
    assert normalize_phone("1-210-555-0177") == "+12105550177"
    assert normalize_phone("+44 20 7946 0958") == "+442079460958"
    assert normalize_phone("12345") is None
    assert normalize_phone("") is None


def test_clean_dedupes_and_reports(tmp_path):
    leads, problems = clean_leads(load_leads(write_sheet(tmp_path)))
    assert [lead.merchant_business_name for lead in leads] == ["Joe's Diner", "Bella Salon"]
    assert any("duplicate" in p for p in problems)
    assert any("invalid phone" in p for p in problems)


def test_csv_and_xml_round_trip(tmp_path):
    leads, _ = clean_leads(load_leads(write_sheet(tmp_path)))
    leads[0].called = True
    leads[0].interested = True
    for name in ("out.csv", "out.xml"):
        save_leads(leads, tmp_path / name)
        again = load_leads(tmp_path / name)
        assert again[0].merchant_business_name == "Joe's Diner"
        assert again[0].phone_number == "+12105550142"
        assert again[0].called and again[0].interested and not again[0].voicemail


def test_xml_with_entities_is_refused(tmp_path):
    bad = tmp_path / "bad.xml"
    bad.write_text('<!DOCTYPE x [<!ENTITY a "b">]><leads/>', encoding="utf-8")
    with pytest.raises(LeadFileError):
        load_leads(bad)


def test_suppression_and_eligibility(tmp_path):
    dnc = tmp_path / "dnc.txt"
    dnc.write_text("# comment\n(210) 555-0142\n", encoding="utf-8")
    suppression = load_suppression(dnc)
    assert "+12105550142" in suppression
    assert callable_reason(Lead(phone_number="+12105550142"), suppression)
    assert callable_reason(Lead(phone_number="+12105550177", opt_out=True), set())
    assert callable_reason(Lead(phone_number="+12105550177", called=True), set())
    assert callable_reason(Lead(phone_number="+12105550177", called=True), set(), retry=True) is None
    assert callable_reason(Lead(phone_number="+12105550177"), set()) is None


def test_queries_are_public_profile_only():
    joined = " ".join(build_queries("Joe's Diner", "San Antonio")).lower()
    for banned in ("filetype:", "intext:password", "inurl:admin", "ext:env", "ssn"):
        assert banned not in joined
    assert "site:yelp.com" in joined


def test_research_stores_unverified_memory(tmp_path):
    pages = {
        "default": "<html><script>x()</script><p>Joe's Diner is a family restaurant "
        "on Main Street that takes Clover payments.</p></html>"
    }
    memory = ResearchMemory(tmp_path / "mem.jsonl")
    lead = Lead(merchant_business_name="Joe's Diner", phone_number="+12105550142")
    result = research_lead(lead, lambda url: pages["default"], memory)
    assert "family restaurant" in lead.research_summary
    assert lead.pos_dm == "Clover (unverified)"
    assert result["pos_hint"] == "Clover"
    saved = memory.latest("+12105550142")
    assert saved["verified"] is False and saved["sources"]


def test_research_handles_empty_fetch(tmp_path):
    memory = ResearchMemory(tmp_path / "mem.jsonl")
    lead = Lead(merchant_business_name="Ghost Shop", phone_number="+12105550199")
    research_lead(lead, lambda url: None, memory)
    assert lead.research_summary == "" and lead.pos_dm == ""


def test_call_body_discloses_and_confirms_business(tmp_path):
    lead = Lead(
        merchant_business_name="Joe's Diner",
        phone_number="+12105550142",
        pos_dm="Clover (unverified)",
        research_summary="Family restaurant.",
    )
    body = build_call_body(lead, "agent_1", "We offer X.", "AIR AGENTS", 120)
    assert body["to"] == "+12105550142" and body["maxDurationSeconds"] == 120
    assert "automated assistant" in body["firstMessage"]
    assert "Joe's Diner" in body["firstMessage"]
    prompt = body["systemPrompt"]
    assert "UNVERIFIED" in prompt and "Clover" in prompt
    assert "do not call" in prompt.lower() and "end the call immediately" in prompt
    assert "We offer X." in prompt


def test_offer_is_required(tmp_path):
    with pytest.raises(ValueError):
        load_offer(None)
    empty = tmp_path / "offer.md"
    empty.write_text("  ", encoding="utf-8")
    with pytest.raises(ValueError):
        load_offer(str(empty))


def transcript(*lines):
    return {"entries": [{"source": "user", "text": t} for t in lines]}


def test_classify_interested_owner_callback():
    session = {"answered": True, "voicemail": {"detected": False, "amdVerdict": "human"}}
    flags = classify(
        session, transcript("Yes I'm the owner", "sounds interesting, can someone call me back")
    )
    assert flags["connected"] and flags["interested"] and flags["connect_live_agent"]
    assert flags["owner_prequalification"] == "owner (self-identified)"
    assert not flags["opt_out"] and not flags["failed"]


def test_classify_opt_out_wins():
    session = {"answered": True, "voicemail": {}}
    flags = classify(session, transcript("not interested, stop calling me"))
    assert flags["opt_out"] and not flags["interested"] and not flags["connect_live_agent"]


def test_classify_voicemail_and_unanswered():
    vm = classify({"answered": True, "voicemail": {"detected": True}}, transcript("leave a message"))
    assert vm["voicemail"] and not vm["connected"]
    missed = classify({"answered": False}, {"entries": []})
    assert missed["failed"] and not missed["connected"] and missed["called"]


def test_apply_outcome_keeps_earlier_positive_result():
    lead = Lead(merchant_business_name="A", phone_number="+12105550142", interested=True)
    flags = classify({"answered": True, "voicemail": {}}, transcript("hello"))
    apply_outcome(lead, flags, session_id="s1")
    assert lead.interested and lead.called and lead.session_id == "s1"


def test_cli_end_to_end(tmp_path, capsys):
    clean = tmp_path / "clean.csv"
    assert cli.main(["import", str(write_sheet(tmp_path)), "--out", str(clean)]) == 0

    offer = tmp_path / "offer.md"
    offer.write_text("A short offer.", encoding="utf-8")
    dnc = tmp_path / "dnc.txt"
    dnc.write_text("+12105550177\n", encoding="utf-8")
    calls = tmp_path / "calls.jsonl"
    cli.main(["prepare", str(clean), "--agent-id", "agent_1", "--offer", str(offer),
              "--dnc", str(dnc), "--out", str(calls)])
    bodies = [json.loads(line) for line in calls.read_text().splitlines()]
    assert [b["to"] for b in bodies] == ["+12105550142"]  # Bella Salon is suppressed

    session = tmp_path / "s.json"
    session.write_text(json.dumps({"id": "abc", "answered": True, "voicemail": {}}))
    tr = tmp_path / "t.json"
    tr.write_text(json.dumps({"data": transcript("yes I own it, tell me more")}))
    xml_out = tmp_path / "result.xml"
    cli.main(["record", str(clean), "--phone", "+12105550142", "--session", str(session),
              "--transcript", str(tr), "--out", str(xml_out)])
    result = load_leads(xml_out)
    joe = next(lead for lead in result if lead.merchant_business_name == "Joe's Diner")
    assert joe.called and joe.connected and joe.interested and joe.session_id == "abc"
    assert cli.main(["record", str(clean), "--phone", "+19999999999", "--session", str(session),
                     "--transcript", str(tr)]) == 1
