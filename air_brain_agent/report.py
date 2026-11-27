"""Output: ranked markdown report and CSV/JSON export of leads."""

from __future__ import annotations

import csv
import io
import json
from typing import List

from .schema import Lead


def markdown_report(leads: List[Lead]) -> str:
    out = [f"# Lead report ({len(leads)} leads)\n"]
    for lead in leads:
        q = lead.qualification
        out.append(f"## {lead.company}  —  tier {q.tier} · score {q.score} · {lead.status.value}")
        out.append(
            f"{lead.website or 'no website'} | {lead.industry or '?'} | {lead.location or '?'} | "
            f"{lead.employees or '?'} employees"
        )
        if lead.description:
            out.append(f"\n{lead.description}")
        if lead.signals:
            out.append(f"\n**Buying signals:** {', '.join(lead.signals)}")
        for c in lead.contacts:
            out.append(f"- {c.name or 'Contact'} ({c.title or 'n/a'}) {c.email or ''} {c.phone or ''}".rstrip())
        out.append(
            f"\n_Why:_ {'; '.join(q.reasons) or 'n/a'}"
            + (f"  \n_Missing:_ {', '.join(q.missing)}" if q.missing else "")
        )
        out.append("_Evidence:_ " + (" · ".join(e.url for e in lead.evidence[:3]) or "none") + "\n")
    return "\n".join(out)


def export(leads: List[Lead], fmt: str = "csv") -> str:
    if fmt == "json":
        return json.dumps([l.model_dump(mode="json") for l in leads], indent=2)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "company",
            "website",
            "industry",
            "location",
            "employees",
            "tier",
            "score",
            "status",
            "email",
            "phone",
            "signals",
            "evidence",
        ]
    )
    for l in leads:
        email = next((c.email for c in l.contacts if c.email), "")
        phone = next((c.phone for c in l.contacts if c.phone), "")
        w.writerow(
            [
                l.company,
                l.website,
                l.industry,
                l.location,
                l.employees,
                l.qualification.tier,
                l.qualification.score,
                l.status.value,
                email,
                phone,
                "; ".join(l.signals),
                " ".join(e.url for e in l.evidence[:3]),
            ]
        )
    return buf.getvalue()
