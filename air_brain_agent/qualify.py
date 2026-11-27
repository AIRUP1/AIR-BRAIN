"""Deterministic, explainable prequalification against an ICP, with weights that learn from feedback."""

from __future__ import annotations

from typing import Dict

from .schema import ICP, Feedback, Lead, LeadStatus, Qualification
from .store import Store


def _hit(needles, haystack: str) -> bool:
    haystack = haystack.lower()
    return any(n.lower() in haystack for n in needles)


def qualify(lead: Lead, icp: ICP, weights: Dict[str, float]) -> Qualification:
    text = " ".join([lead.company, lead.industry or "", lead.description or "", *lead.services, *lead.signals])
    reasons, missing, comp = [], [], {}

    def ratio(items, haystack):
        return sum(1 for i in items if i.lower() in haystack.lower()) / len(items) if items else 0.5

    # fit components, each in 0..1 (0.5 = neutral when the ICP does not constrain that dimension)
    comp["industry"] = (
        (1.0 if _hit(icp.target_industries, f"{lead.industry or ''} {lead.description or ''}") else 0.0)
        if icp.target_industries
        else 0.5
    )
    comp["location"] = (
        (1.0 if _hit(icp.target_locations, lead.location or "") else 0.0) if icp.target_locations else 0.5
    )
    if lead.employees is None:
        comp["size"] = 0.4 if (icp.min_employees or icp.max_employees) else 0.5
        if icp.min_employees or icp.max_employees:
            missing.append("employees")
    else:
        ok = (icp.min_employees is None or lead.employees >= icp.min_employees) and (
            icp.max_employees is None or lead.employees <= icp.max_employees
        )
        comp["size"] = 1.0 if ok else 0.0
    comp["keywords"] = ratio(icp.required_keywords, text)
    comp["signals"] = (
        min(1.0, sum(1 for s in icp.buying_signals if s.lower() in text.lower()) / 2) if lead.signals else 0.0
    )
    reachable = [c for c in lead.contacts if c.email or c.phone]
    comp["contact"] = 1.0 if any(c.email for c in reachable) else (0.6 if reachable else 0.0)
    comp["evidence"] = min(1.0, len(lead.evidence) / 3)
    for field in ("website", "industry", "location", "description"):
        if not getattr(lead, field):
            missing.append(field)
    if not reachable:
        missing.append("contact")

    total_w = sum(weights.get(k, 0) for k in comp) or 1.0
    score = round(100 * sum(v * weights.get(k, 0) for k, v in comp.items()) / total_w, 1)

    for name, v in comp.items():
        if v >= 0.99:
            reasons.append(f"+ strong {name} match")
        elif v == 0.0:
            reasons.append(f"- no {name} match")

    dq = [d for d in icp.disqualifiers if _hit([d], text)]
    if dq:
        reasons.append(f"disqualified by: {', '.join(dq)}")
        return Qualification(score=min(score, 20.0), tier="DQ", components=comp, reasons=reasons, missing=missing)
    tier = "A" if score >= icp.qualify_threshold else "B" if score >= icp.nurture_threshold else "C"
    return Qualification(score=score, tier=tier, components=comp, reasons=reasons, missing=missing)


def apply_qualification(lead: Lead, icp: ICP, store: Store) -> Lead:
    lead.qualification = qualify(lead, icp, store.get_weights())
    if lead.status in (LeadStatus.ACCEPTED, LeadStatus.REJECTED):
        return lead  # human decisions are never overwritten by the model
    lead.status = {
        "A": LeadStatus.QUALIFIED,
        "B": LeadStatus.NURTURE,
        "C": LeadStatus.NEW,
        "DQ": LeadStatus.DISQUALIFIED,
    }[lead.qualification.tier]
    return lead


def learn_from_feedback(store: Store, fb: Feedback, lr: float = 0.05) -> Dict[str, float]:
    """Nudge weights toward components that were high on accepted leads and low on rejected ones."""
    lead = store.get_lead(fb.lead_key)
    if lead is None or fb.verdict == "needs_work":
        return store.get_weights()
    sign = 1.0 if fb.verdict == "accepted" else -1.0
    weights = store.get_weights()
    for name, value in lead.qualification.components.items():
        if name in weights:
            weights[name] = max(0.02, weights[name] + lr * sign * (value - 0.5))
    total = sum(weights.values())
    weights = {k: round(v / total, 4) for k, v in weights.items()}
    store.set_weights(weights)
    return weights
