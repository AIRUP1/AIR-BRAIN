"""Layered, polite scraper: cache -> HTTP (robots-aware) -> Firecrawl rendering fallback, with structured extraction.

Deliberately does NOT bypass logins, paywalls, CAPTCHAs or robots.txt, and refuses people-search / social platforms.
"""

from __future__ import annotations

import ipaddress
import json
import os
import re
import socket
import time
import urllib.robotparser
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from .schema import domain_of
from .store import Store

# Platforms whose terms forbid scraping or that hold private-individual data. Use their official APIs instead.
BLOCKED_DOMAINS = (
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "spokeo.com",
    "whitepages.com",
    "beenverified.com",
    "truepeoplesearch.com",
    "fastpeoplesearch.com",
)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?1[\s.-]?)?\(?\b\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b")
JUNK_EMAIL_SUFFIX = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js")
MAX_TEXT = 60_000


class ScrapeBlocked(Exception):
    pass


@dataclass
class ScrapeResult:
    url: str
    status: int
    source: str  # cache | http | firecrawl
    title: str = ""
    text: str = ""
    links: List[str] = field(default_factory=list)
    emails: List[str] = field(default_factory=list)
    phones: List[str] = field(default_factory=list)
    jsonld: List[dict] = field(default_factory=list)  # schema.org Organization / LocalBusiness blobs


def _public_host(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    return all(ipaddress.ip_address(i[4][0]).is_global for i in infos)


def extract(url: str, html: str) -> ScrapeResult:
    soup = BeautifulSoup(html, "html.parser")
    jsonld: List[dict] = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except ValueError:
            continue
        for item in data if isinstance(data, list) else [data]:
            if isinstance(item, dict) and re.search(
                r"Organization|LocalBusiness|Corporation|Store", json.dumps(item.get("@type", ""))
            ):
                jsonld.append(item)
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = re.sub(r"\n{3,}", "\n\n", soup.get_text("\n", strip=True))[:MAX_TEXT]
    mailtos = [a["href"][7:].split("?")[0] for a in soup.find_all("a", href=re.compile(r"^mailto:", re.I))]
    emails = sorted({e.lower() for e in EMAIL_RE.findall(text) + mailtos if not e.lower().endswith(JUNK_EMAIL_SUFFIX)})
    base = domain_of(url)
    links = []
    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"]).split("#")[0]
        if domain_of(href) == base and href not in links and href.startswith("http"):
            links.append(href)
    return ScrapeResult(
        url=url,
        status=200,
        source="http",
        title=(soup.title.string or "").strip() if soup.title else "",
        text=text,
        links=links[:60],
        emails=emails[:20],
        phones=sorted(set(PHONE_RE.findall(text)))[:10],
        jsonld=jsonld[:5],
    )


class Scraper:
    def __init__(
        self,
        store: Store,
        user_agent: str = "AirBrainBot/1.0 (+business lead research; respects robots.txt)",
        min_interval_s: float = 1.5,
        cache_ttl_s: float = 7 * 86400,
        timeout_s: float = 20,
        firecrawl_key: Optional[str] = None,
    ) -> None:
        self.store, self.ua, self.interval, self.ttl, self.timeout = (
            store,
            user_agent,
            min_interval_s,
            cache_ttl_s,
            timeout_s,
        )
        self.firecrawl_key = firecrawl_key if firecrawl_key is not None else os.getenv("FIRECRAWL_API_KEY")
        self._last_hit: Dict[str, float] = {}
        self._robots: Dict[str, Optional[urllib.robotparser.RobotFileParser]] = {}
        self._client = httpx.Client(headers={"User-Agent": user_agent}, timeout=timeout_s, follow_redirects=True)

    # -- guards -----------------------------------------------------------
    def _guard(self, url: str) -> str:
        parsed = urlparse(url if "//" in url else f"https://{url}")
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ScrapeBlocked("only http(s) URLs are allowed")
        host = parsed.hostname.lower()
        if any(host == d or host.endswith("." + d) for d in BLOCKED_DOMAINS):
            raise ScrapeBlocked(
                f"{host} is blocked: its terms forbid scraping or it holds private-person data; use an official API"
            )
        if not _public_host(host):
            raise ScrapeBlocked(f"{host} does not resolve to a public address")
        return parsed.geturl()

    def _allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                resp = self._client.get(origin + "/robots.txt")
                if resp.status_code == 200:
                    rp.parse(resp.text.splitlines())
                    self._robots[origin] = rp
                else:
                    self._robots[origin] = None  # no robots.txt => allowed
            except httpx.HTTPError:
                self._robots[origin] = None
        rp = self._robots[origin]
        return True if rp is None else rp.can_fetch(self.ua, url)

    def _throttle(self, host: str) -> None:
        wait = self.interval - (time.time() - self._last_hit.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        self._last_hit[host] = time.time()

    # -- fetching ---------------------------------------------------------
    def fetch(self, url: str, force: bool = False, render: bool = False) -> ScrapeResult:
        url = self._guard(url)
        domain = domain_of(url)
        if not force:
            cached = self.store.get_page(url, self.ttl)
            if cached:
                meta = cached["meta"]
                return ScrapeResult(
                    url,
                    cached["status"],
                    "cache",
                    cached["title"],
                    cached["text"],
                    meta.get("links", []),
                    meta.get("emails", []),
                    meta.get("phones", []),
                    meta.get("jsonld", []),
                )
        if not self._allowed(url):
            self.store.note_domain(domain, f"robots.txt disallows {urlparse(url).path or '/'}; skipped")
            raise ScrapeBlocked("robots.txt disallows this path")
        self._throttle(domain)
        result: Optional[ScrapeResult] = None
        if not render:
            try:
                resp = self._client.get(url)
                if resp.status_code >= 400:
                    self.store.note_domain(domain, f"HTTP {resp.status_code} on {urlparse(url).path or '/'}")
                    result = ScrapeResult(url, resp.status_code, "http")
                elif "html" in resp.headers.get("content-type", "html"):
                    result = extract(url, resp.text)
            except httpx.HTTPError as exc:
                self.store.note_domain(domain, f"HTTP error {type(exc).__name__}")
        thin = result is None or (result.status < 400 and len(result.text) < 300)
        if (render or thin) and self.firecrawl_key:
            fc = self._firecrawl(url)
            if fc and len(fc.text) > len(result.text if result else ""):
                result = fc
                self.store.note_domain(domain, "page needs JS rendering; Firecrawl fallback used")
        if result is None:
            result = ScrapeResult(url, 0, "http")
        if result.status < 400 and result.text:
            self.store.put_page(
                url,
                result.status,
                result.source,
                result.title,
                result.text,
                {"links": result.links, "emails": result.emails, "phones": result.phones, "jsonld": result.jsonld},
            )
        return result

    def _firecrawl(self, url: str) -> Optional[ScrapeResult]:
        try:
            resp = httpx.post(
                "https://api.firecrawl.dev/v1/scrape",
                timeout=60,
                headers={"Authorization": f"Bearer {self.firecrawl_key}"},
                json={"url": url, "formats": ["markdown", "html"], "onlyMainContent": False},
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
            result = extract(url, data.get("html") or "")
            md = data.get("markdown") or ""
            if len(md) > len(result.text):
                result.text = md[:MAX_TEXT]
                result.emails = sorted(set(result.emails) | {e.lower() for e in EMAIL_RE.findall(md)})
            result.source = "firecrawl"
            return result
        except (httpx.HTTPError, ValueError):
            return None

    def search(self, query: str, limit: int = 8) -> List[dict]:
        """Web search through Firecrawl (requires FIRECRAWL_API_KEY). Returns [{url,title,description}]."""
        if not self.firecrawl_key:
            raise ScrapeBlocked("web search needs FIRECRAWL_API_KEY; otherwise pass seed URLs to scrape_url")
        resp = httpx.post(
            "https://api.firecrawl.dev/v1/search",
            timeout=60,
            headers={"Authorization": f"Bearer {self.firecrawl_key}"},
            json={"query": query, "limit": limit},
        )
        resp.raise_for_status()
        return [
            {"url": r.get("url"), "title": r.get("title"), "description": r.get("description")}
            for r in resp.json().get("data", [])
        ]
