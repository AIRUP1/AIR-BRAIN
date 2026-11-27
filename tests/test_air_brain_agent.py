# pylint: disable=protected-access,use-dict-literal
import httpx
import pytest

from air_brain_agent import ICP, Contact, Evidence, Lead, LeadStatus
from air_brain_agent import scraper as scraper_mod
from air_brain_agent.agent import AirBrainAgent
from air_brain_agent.memory import sync_memory
from air_brain_agent.report import export, markdown_report
from air_brain_agent.scraper import ScrapeBlocked, Scraper
from air_brain_agent.store import Store

HOME = """<html><head><title>Acme Solar</title>
<script type="application/ld+json">{"@type":"LocalBusiness","name":"Acme Solar","telephone":"555-123-4567"}</script></head>
<body><h1>Acme Solar Tampa</h1><p>We are hiring installers and expanding. Contact sales@acmesolar.com or 813-555-0100.</p>
<a href="/about">About</a><a href="https://other.com/x">x</a><img src="logo@2x.png"></body></html>""" + "x " * 200


@pytest.fixture()
def store():
    return Store(":memory:")


@pytest.fixture()
def fake_web(monkeypatch):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private")
        return httpx.Response(200, text=HOME, headers={"content-type": "text/html"})

    monkeypatch.setattr(scraper_mod, "_public_host", lambda host: True)
    monkeypatch.setattr(scraper_mod.time, "sleep", lambda s: None)

    def make(store):
        s = Scraper(store, firecrawl_key="", min_interval_s=0)
        s._client = httpx.Client(transport=httpx.MockTransport(handler), headers={"User-Agent": s.ua})
        return s

    return make, calls


def test_extract_contacts_links_and_jsonld(store, fake_web):
    make, _ = fake_web
    r = make(store).fetch("https://acmesolar.com/")
    assert r.emails == ["sales@acmesolar.com"]  # image-ish "logo@2x.png" filtered
    assert any("555-0100" in p for p in r.phones)
    assert r.links == ["https://acmesolar.com/about"]
    assert r.jsonld[0]["name"] == "Acme Solar"


def test_cache_is_scrape_memory(store, fake_web):
    make, calls = fake_web
    s = make(store)
    assert s.fetch("https://acmesolar.com/").source == "http"
    n = len(calls)
    assert s.fetch("https://acmesolar.com/").source == "cache"
    assert len(calls) == n


def test_robots_and_blocklist_are_respected(store, fake_web):
    make, _ = fake_web
    s = make(store)
    with pytest.raises(ScrapeBlocked, match="robots"):
        s.fetch("https://acmesolar.com/private/page")
    assert "robots.txt" in store.domain_notes()["acmesolar.com"]
    for url in ("https://www.linkedin.com/company/x", "https://spokeo.com/john", "ftp://x.com"):
        with pytest.raises(ScrapeBlocked):
            s.fetch(url)


def test_private_addresses_blocked(store):
    with pytest.raises(ScrapeBlocked):
        Scraper(store, firecrawl_key="").fetch("http://127.0.0.1/admin")


def make_lead(**kw):
    base = dict(
        company="Acme Solar",
        website="https://www.acmesolar.com",
        industry="solar installation",
        location="Tampa, FL",
        employees=25,
        description="Residential solar installer, hiring and expanding",
        signals=["hiring"],
        contacts=[Contact(email="sales@acmesolar.com")],
        evidence=[Evidence(url="https://acmesolar.com", quote="we are hiring")] * 3,
    )
    base.update(kw)
    return Lead(**base)


ICP_SOLAR = ICP(
    target_industries=["solar"],
    target_locations=["FL"],
    min_employees=10,
    max_employees=200,
    disqualifiers=["franchise"],
)


def test_qualification_tiers_and_dedupe(tmp_path):
    agent = AirBrainAgent(str(tmp_path), icp=ICP_SOLAR, store=Store(":memory:"))
    good = agent.save_lead(make_lead())
    assert good.key == "acmesolar.com" and good.qualification.tier == "A" and good.status == LeadStatus.QUALIFIED
    again = agent.save_lead(make_lead(company="Acme Solar LLC", signals=["new location"]))
    assert len(agent.store.list_leads()) == 1 and set(again.signals) == {"hiring", "new location"}
    thin = agent.save_lead(Lead(company="Mystery Co"))
    assert thin.qualification.tier in {"B", "C"} and "contact" in thin.qualification.missing
    dq = agent.save_lead(make_lead(website="https://frank.com", company="Frank", description="franchise solar"))
    assert dq.status == LeadStatus.DISQUALIFIED and dq.qualification.score <= 20


def test_feedback_shifts_weights_and_syncs_memory(tmp_path):
    agent = AirBrainAgent(str(tmp_path), icp=ICP_SOLAR, store=Store(":memory:"))
    agent.save_lead(make_lead(contacts=[]))  # strong industry/location, no contact
    before = agent.store.get_weights()
    out = agent.record_feedback("acmesolar.com", "rejected", "no way to reach them")
    assert out["ok"] and out["weights"]["industry"] < before["industry"]
    assert out["weights"]["contact"] > before["contact"]
    assert agent.store.get_lead("acmesolar.com").status == LeadStatus.REJECTED
    agent.save_lead(make_lead(contacts=[]))  # human decision survives re-qualification
    assert agent.store.get_lead("acmesolar.com").status == LeadStatus.REJECTED
    notes = (tmp_path / "memories" / "icp_and_feedback.md").read_text()
    assert "REJECTED acmesolar.com" in notes and "no way to reach them" in notes
    assert agent.record_feedback("nope", "accepted")["error"]


def test_memory_files_for_domains(tmp_path):
    store = Store(":memory:")
    store.note_domain("acmesolar.com", "needs JS rendering")
    sync_memory(store, ICP(), str(tmp_path))
    assert "needs JS rendering" in (tmp_path / "memories" / "scraping" / "acmesolar.com.md").read_text()


def test_outputs(tmp_path):
    agent = AirBrainAgent(str(tmp_path), icp=ICP_SOLAR, store=Store(":memory:"))
    agent.save_lead(make_lead())
    assert "Acme Solar" in markdown_report(agent.store.list_leads())
    assert "sales@acmesolar.com" in export(agent.store.list_leads(), "csv")
    assert '"company": "Acme Solar"' in export(agent.store.list_leads(), "json")


def test_llm_tools_schema_and_dispatch(tmp_path):
    agent = AirBrainAgent(str(tmp_path), icp=ICP_SOLAR, store=Store(":memory:"))
    tools = {t.to_dict()["name"]: t for t in agent._tools()}
    assert {"web_search", "scrape_url", "save_lead", "list_leads", "record_feedback", "export_leads"} <= set(tools)
    res = tools["save_lead"].call(
        {
            "company": "Acme Solar",
            "website": "https://acmesolar.com",
            "industry": "solar",
            "contacts": [{"email": "bad-email"}],
        }
    )
    assert "invalid lead" in str(res)  # schema validation guards model output
    ok = tools["save_lead"].call(
        {
            "company": "Acme Solar",
            "website": "https://acmesolar.com",
            "industry": "solar",
            "evidence": [{"url": "https://acmesolar.com", "quote": "hi"}],
        }
    )
    assert "acmesolar.com" in str(ok)
    assert "BLOCKED" in str(tools["scrape_url"].call({"url": "https://linkedin.com/in/x"}))
