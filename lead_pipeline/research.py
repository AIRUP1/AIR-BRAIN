"""Public-web research about a merchant, feeding the agent's call briefing.

Queries are limited to public business-profile information: what the business
is, where it is, which point-of-sale system it appears to use and who is named
as owner. They deliberately exclude exposed-file, credential or personal-record
searches. Everything found is stored as unverified.
"""
from __future__ import annotations

import html
import re
from typing import Callable, Dict, List, Optional
from urllib.parse import quote_plus

from .leads import Lead
from .memory import ResearchMemory

Fetcher = Callable[[str], Optional[str]]

POS_VENDORS = (
    "Clover", "Square", "Toast", "Lightspeed", "Shopify POS", "Heartland",
    "Revel", "TouchBistro", "SpotOn", "PAR Brink", "Aloha", "Micros",
    "Epos Now", "NCR Silver", "Fiserv",
)

PROFILE_SITES = ("facebook.com", "yelp.com", "mapquest.com", "bbb.org", "linkedin.com/company")


def build_queries(name: str, city: str = "") -> List[str]:
    """Search-operator queries for public business profile data only."""
    name = name.replace('"', "").strip()
    where = f" {city.strip()}" if city.strip() else ""
    sites = " OR ".join(f"site:{site}" for site in PROFILE_SITES)
    pos = " OR ".join(f'"{vendor}"' for vendor in POS_VENDORS[:6])
    return [
        f'"{name}"{where} phone hours',
        f'"{name}"{where} ({sites})',
        f'"{name}"{where} ({pos}) "point of sale"',
        f'"{name}"{where} ("owned by" OR owner OR founder)',
    ]


def search_url(query: str) -> str:
    return "https://www.google.com/search?q=" + quote_plus(query)


def _text(page: str) -> str:
    page = re.sub(r"(?is)<(script|style).*?</\1>", " ", page)
    page = re.sub(r"(?s)<[^>]+>", " ", page)
    return re.sub(r"\s+", " ", html.unescape(page)).strip()


def detect_pos(text: str) -> str:
    lowered = text.lower()
    found = [vendor for vendor in POS_VENDORS if vendor.lower() in lowered]
    return ", ".join(found[:3])


def summarize(name: str, texts: List[str]) -> str:
    """Short, hedged summary built from sentences that mention the business."""
    needle = name.lower()
    sentences: List[str] = []
    for text in texts:
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            if needle in sentence.lower() and 20 < len(sentence) < 240:
                sentences.append(sentence.strip())
    unique = list(dict.fromkeys(sentences))[:3]
    return " ".join(unique)[:500]


def research_lead(
    lead: Lead,
    fetch: Fetcher,
    memory: ResearchMemory,
    city: str = "",
) -> Dict[str, object]:
    """Run the queries, store what was found, and update the lead."""
    sources: List[str] = []
    texts: List[str] = []
    for query in build_queries(lead.merchant_business_name, city):
        url = search_url(query)
        page = fetch(url)
        if not page:
            continue
        sources.append(url)
        texts.append(_text(page))
    combined = " ".join(texts)
    summary = summarize(lead.merchant_business_name, texts)
    pos_hint = detect_pos(combined) if any(
        lead.merchant_business_name.lower() in t.lower() for t in texts
    ) else ""
    memory.add(lead.phone_number, summary, sources, pos_hint)
    lead.research_summary = summary
    if pos_hint and not lead.pos_dm:
        lead.pos_dm = f"{pos_hint} (unverified)"
    return {"summary": summary, "pos_hint": pos_hint, "sources": len(sources)}


def browserless_fetcher(api_key: Optional[str] = None) -> Fetcher:
    """Fetch pages through the repo's Browserless client (needs an API key)."""
    from browserless_integration import BrowserlessClient

    client = BrowserlessClient(api_key)
    return lambda url: client.get_content(url)
