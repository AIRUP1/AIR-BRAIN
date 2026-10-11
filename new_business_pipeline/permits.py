"""Weekly pull of newly opened DFW outlets from Texas Comptroller sales-tax permit data.

Source: https://data.texas.gov/resource/jrea-zgmq (Active Sales Tax Permit Holders).
Writes a call-list-ready CSV (phone/email/website blank until enriched) and remembers which
outlets it already emitted so each run only returns new ones.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

API = "https://data.texas.gov/resource/jrea-zgmq.json"
COUNTIES = {"057": "Dallas", "043": "Collin", "061": "Denton", "220": "Tarrant", "199": "Rockwall"}
KEEP_NAICS = ("44", "45", "72", "81", "71")  # retail, food service, personal services, arts/rec
RESIDENTIAL = re.compile(r"\b(APT|UNIT|PO BOX|P O BOX|TRLR|LOT)\b|#\s*\d+[A-Z]?$", re.I)
COMMERCIAL = re.compile(r"\b(STE|SUITE|BLDG|BLVD|PKWY|HWY|FWY|FM \d+|SH \d+|US \d+|IH ?\d+|EXPY|MAIN ST|AVE|PLZ|PLAZA|CENTER|TRL?)\b", re.I)
CHAINS = re.compile(
    r"CHIPOTLE|CICI|CORNER BAKERY|WALMART|TARGET|DOLLAR|7-ELEVEN|STARBUCKS|MCDONALD|CHICK-FIL|WHATABURGER|TACO BELL|SUBWAY|"
    r"CVS|WALGREEN|AUTOZONE|O'REILLY|SALLY|PANDA|CIRCLE K|DUNKIN|DOMINO|PAPA JOHN|SONIC|WINGSTOP|JERSEY MIKE|JIMMY JOHN|"
    r"FIREHOUSE|HABIT|DAIRY QUEEN|LITTLE CAESAR|BURGER KING|POPEYES|KFC|WENDY|RAISING CANE|DUTCH BROS|7 BREW|CRUMBL|"
    r"SMOOTHIE KING|SUPERCUTS|GREAT CLIPS|SPORT CLIPS|ORANGETHEORY|PLANET FITNESS|ULTA|MARSHALLS|TJ MAXX|BURLINGTON|"
    r"FIVE BELOW|FAMILY DOLLAR|GAMESTOP|VERIZON|AT&T|T-MOBILE|BOOST MOBILE|CRICKET|H&R|PETCO|PETSMART|HOBBY LOBBY|"
    r"ADVANCE AUTO|JIFFY|VALVOLINE|SHERWIN|HOME DEPOT|LOWE'S|BEST BUY|SPROUTS|ALDI|WHOLE FOODS|KROGER|ALBERTSON|"
    r"CONOCO|VALERO|SHELL|EXXON|CHEVRON|MURPHY|QUIKTRIP|RACETRAC|BUC-EE|LOVE'S|PILOT",
    re.I,
)
NEEDS = {
    "722": ("Website / online ordering if none", "Online ordering + reservations", "Restaurant POS (Toast/Square/Clover)", "Local SEO + Google Business", "AI voice agent for phone orders and reservations", "Loyalty / SMS"),
    "812": ("Site + booking", "Online booking platform", "Salon/spa POS", "Local SEO + Google Business", "AI receptionist / booking agent", "Rebooking campaigns"),
    "811": ("Site + booking", "Online booking / quotes", "Invoicing / POS", "Local SEO + Google Business", "AI voice agent for inbound calls", "CRM / review requests"),
    "default": ("Site / e-commerce", "E-commerce platform (Shopify)", "Retail POS synced to inventory", "Local SEO", "AI chat / SMS agent", "Email / SMS campaigns"),
}
HEADER = ["business_name", "legal_entity", "phone_e164", "email", "website", "address", "city", "state", "zip", "county", "naics",
          "priority", "source", "opened_date", "current_pos_software", "needs_website", "needs_platform", "needs_pos", "needs_seo",
          "needs_agents", "other_needs", "enrichment_status", "notes"]


def outlet_key(r: dict) -> str:
    return f"{r.get('taxpayer_number', '')}-{r.get('outlet_number', '')}"


def keep(r: dict) -> bool:
    n = r.get("outlet_naics_code", "")
    addr = r.get("outlet_address", "")
    # Sole proprietors (org types IS/PI/PL) are kept; the home-address filter below still applies.
    return (
        n[:2] in KEEP_NAICS and not n.startswith("454")
        and not RESIDENTIAL.search(addr) and bool(COMMERCIAL.search(addr))
        and not CHAINS.search(r.get("outlet_name", ""))
    )


def to_row(r: dict) -> list[str]:
    k = r["outlet_naics_code"][:3]
    nd = NEEDS.get(k, NEEDS["default"])
    return [r["outlet_name"].title(), r["taxpayer_name"].title(), "", "", "", r["outlet_address"].title(), r["outlet_city"].title(), "TX",
            r["outlet_zip_code"][:5], COUNTIES.get(r["outlet_county_code"], ""), r["outlet_naics_code"],
            "A" if k in ("722", "812", "811") else "B", "TX Comptroller sales-tax permits (data.texas.gov jrea-zgmq)",
            r["outlet_first_sales_date"][:10], "Unknown", *nd, "pending", "Phone / website / email to be enriched"]


def fetch(since: date, until: date, limit: int = 2000, opener=urllib.request.urlopen) -> list[dict]:
    rows: list[dict] = []
    for code in COUNTIES:
        offset = 0
        while True:
            q = urllib.parse.urlencode({
                "outlet_county_code": code,
                "$where": f"outlet_first_sales_date between '{since.isoformat()}T00:00:00' and '{until.isoformat()}T00:00:00'",
                "$order": "outlet_first_sales_date DESC", "$limit": 1000, "$offset": offset,
            }, quote_via=urllib.parse.quote)
            with opener(f"{API}?{q}", timeout=60) as resp:
                page = json.load(resp)
            rows += page
            if len(page) < 1000 or len(rows) >= limit * len(COUNTIES):
                break
            offset += 1000
    return rows


def run(since: date, until: date, out: Path, seen_path: Path, rows: list[dict] | None = None) -> int:
    rows = fetch(since, until) if rows is None else rows
    seen = set(seen_path.read_text().split()) if seen_path.exists() else set()
    fresh, names, dupes = [], set(), set()
    for r in sorted(rows, key=lambda r: r["outlet_first_sales_date"], reverse=True):
        key = outlet_key(r)
        sig = (re.sub(r"#\s*\d+", "", r["outlet_name"].upper()).strip(), r["outlet_address"].upper())
        if key in seen or not keep(r):
            continue
        if sig in names:
            dupes.add(key)  # same business at the same address: remember it so it never comes back
            continue
        names.add(sig)
        fresh.append((key, to_row(r)))
    if fresh:
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(HEADER)
            w.writerows(row for _, row in fresh)
        seen_path.parent.mkdir(parents=True, exist_ok=True)
        seen_path.write_text("\n".join(sorted(seen | dupes | {k for k, _ in fresh})) + "\n")
    return len(fresh)


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=10, help="look back this many days from today")
    p.add_argument("--out", default=None)
    p.add_argument("--seen", default="data/seen_outlets.txt")
    a = p.parse_args(argv)
    today = date.today()
    out = Path(a.out or f"data/new_businesses_{today.isoformat()}.csv")
    n = run(today - timedelta(days=a.days), today, out, Path(a.seen))
    print(f"{n} new businesses -> {out}" if n else "no new businesses this run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
