"""Investor blueprint KPI calculations and a print-ready workspace presentation."""

from __future__ import annotations

import html
import json
import secrets
from collections import defaultdict
from datetime import date
from typing import Any

STATUS_META = {
    "achieved": {"label": "Achieved", "color": "#047857"},
    "on_track": {"label": "On track", "color": "#2563eb"},
    "watch": {"label": "Watch", "color": "#b45309"},
    "at_risk": {"label": "At risk", "color": "#b91c1c"},
}
CATEGORY_META = {
    "revenue": "Revenue",
    "retention": "Retention",
    "growth": "Growth",
    "operations": "Operations",
}
CATEGORY_ORDER = {category: index for index, category in enumerate(CATEGORY_META)}
CURRENCY_SYMBOLS = {"USD": "$", "CAD": "CA$", "EUR": "€", "GBP": "£"}


def present_kpi(kpi: dict[str, Any]) -> dict[str, Any]:
    """Add normalized progress, variance, and a display status to one KPI."""

    actual = float(kpi["actual_value"])
    target = float(kpi["target_value"])
    achievement_percent = (actual / target) * 100 if target > 0 else 0.0
    progress_percent = min(100.0, max(0.0, achievement_percent))

    if achievement_percent >= 100:
        status = "achieved"
    elif achievement_percent >= 80:
        status = "on_track"
    elif achievement_percent >= 50:
        status = "watch"
    else:
        status = "at_risk"

    return {
        **kpi,
        "actual_value": actual,
        "target_value": target,
        "achievement_percent": round(achievement_percent, 1),
        "progress_percent": round(progress_percent, 1),
        "variance": round(actual - target, 2),
        "status": status,
    }


def build_snapshot(blueprint: dict[str, Any], kpis: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a presentation-ready investor snapshot from stored blueprint data."""

    presented = [present_kpi(kpi) for kpi in kpis]
    presented.sort(
        key=lambda kpi: (
            CATEGORY_ORDER.get(kpi["category"], len(CATEGORY_ORDER)),
            kpi.get("target_date") or "9999-12-31",
            kpi["label"].lower(),
        )
    )
    return {**blueprint, "kpis": presented}


def _format_number(value: float, *, decimals: int = 0) -> str:
    if decimals:
        return f"{value:,.{decimals}f}"
    return f"{value:,.0f}"


def format_value(value: float, unit: str, currency: str) -> str:
    """Format a KPI value without applying financial calculations or projections."""

    if unit == "currency":
        symbol = CURRENCY_SYMBOLS.get(currency, f"{currency} ")
        if abs(value) >= 1_000_000:
            return f"{symbol}{value / 1_000_000:,.1f}M"
        if abs(value) >= 10_000:
            return f"{symbol}{value / 1_000:,.1f}K"
        return f"{symbol}{_format_number(value, decimals=2)}"
    if unit == "percent":
        return f"{_format_number(value, decimals=1)}%"
    if unit == "ratio":
        return f"{_format_number(value, decimals=2)}x"
    return _format_number(value)


def _safe(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _status_badge(kpi: dict[str, Any]) -> str:
    meta = STATUS_META[kpi["status"]]
    return (
        f'<span class="status status-{_safe(kpi["status"])}" '
        f'aria-label="Status: {_safe(meta["label"])}">{_safe(meta["label"])}</span>'
    )


def _progress(kpi: dict[str, Any]) -> str:
    meta = STATUS_META[kpi["status"]]
    progress = kpi["progress_percent"]
    return (
        '<div class="progress-shell">'
        f'<div class="progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" '
        f'aria-valuenow="{progress}" aria-label="{_safe(kpi["label"])} progress" '
        f'style="--progress:{progress}%;--status-color:{meta["color"]}"></div>'
        f'<span class="progress-label">{progress:.0f}% of target</span>'
        "</div>"
    )


def _summary_card(category: str, kpis: list[dict[str, Any]], currency: str) -> str:
    label = CATEGORY_META[category]
    if not kpis:
        return (
            '<article class="signal-card muted">'
            f"<p>{label}</p><strong>Not tracked</strong><span>Add a KPI to this blueprint.</span>"
            "</article>"
        )
    selected = max(kpis, key=lambda kpi: (kpi["achievement_percent"], kpi["actual_value"]))
    meta = STATUS_META[selected["status"]]
    return (
        f'<article class="signal-card status-{_safe(selected["status"])}">'
        f"<p>{label}</p>"
        f'<strong>{_safe(format_value(selected["actual_value"], selected["unit"], currency))}</strong>'
        f'<span>vs. {_safe(format_value(selected["target_value"], selected["unit"], currency))} target</span>'
        f'<em style="color:{meta["color"]}">{_safe(meta["label"])} · {selected["achievement_percent"]:.0f}%</em>'
        "</article>"
    )


def _kpi_row(kpi: dict[str, Any], currency: str, can_edit: bool) -> str:
    owner = kpi.get("owner") or "Unassigned"
    target_date = kpi.get("target_date")
    target_date_text = date.fromisoformat(target_date).strftime("%b %-d, %Y") if target_date else "No target date"
    edit_fields = ""
    if can_edit:
        edit_fields = (
            '<div class="edit-fields" aria-label="Editable KPI fields">'
            '<label>Owner'
            f'<input class="owner-input" value="{_safe(kpi.get("owner") or "")}" maxlength="120" '
            'placeholder="Accountable owner"></label>'
            '<label>Target value'
            f'<input class="target-input" type="number" step="any" min="0.000001" value="{kpi["target_value"]}"></label>'
            "</div>"
        )
    description = f'<p class="description">{_safe(kpi["description"])}</p>' if kpi.get("description") else ""
    return (
        f'<article class="kpi-row" data-kpi-id="{_safe(kpi["id"])}" '
        f'data-owner="{_safe(kpi.get("owner") or "")}" data-target="{kpi["target_value"]}">'
        '<div class="kpi-main">'
        '<div class="kpi-heading">'
        f'<div><p class="eyebrow">{_safe(CATEGORY_META[kpi["category"]])}</p><h3>{_safe(kpi["label"])}</h3>{description}</div>'
        f"{_status_badge(kpi)}"
        "</div>"
        '<div class="metric-line">'
        f'<strong>{_safe(format_value(kpi["actual_value"], kpi["unit"], currency))}</strong>'
        f'<span>actual / {_safe(format_value(kpi["target_value"], kpi["unit"], currency))} target</span>'
        f'<span class="variance">{_safe(format_value(kpi["variance"], kpi["unit"], currency))} variance</span>'
        "</div>"
        f"{_progress(kpi)}"
        "</div>"
        '<aside class="accountability">'
        '<p class="eyebrow">Accountable owner</p>'
        f'<strong class="owner-display">{_safe(owner)}</strong>'
        f'<span>{_safe(target_date_text)}</span>'
        f"{edit_fields}"
        "</aside>"
        "</article>"
    )


def render_investor_blueprint(
    snapshot: dict[str, Any],
    *,
    can_edit: bool,
    csrf_token: str | None = None,
    export_mode: bool = False,
) -> str:
    """Render the single-page investor preset and the cookie-authenticated admin editor."""

    nonce = secrets.token_urlsafe(16)
    currency = snapshot["currency"]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for kpi in snapshot["kpis"]:
        grouped[kpi["category"]].append(kpi)

    title = _safe(snapshot["title"])
    as_of_date = date.fromisoformat(snapshot["as_of_date"]).strftime("%B %-d, %Y")
    summary = "".join(_summary_card(category, grouped[category], currency) for category in ("revenue", "retention", "growth"))
    sections = "".join(
        f'<section class="milestone-group"><div class="group-heading"><p class="eyebrow">{_safe(CATEGORY_META[category])}</p>'
        f'<h2>{_safe(CATEGORY_META[category])} milestones</h2></div>'
        f"{''.join(_kpi_row(kpi, currency, can_edit and not export_mode) for kpi in grouped[category])}</section>"
        for category in CATEGORY_META
        if grouped[category]
    )
    controls = ""
    if can_edit and not export_mode:
        controls = (
            '<div class="controls screen-only">'
            '<button type="button" id="edit-toggle" class="secondary">Edit blueprint</button>'
            '<button type="button" id="save-changes" class="primary" hidden>Save owner & target changes</button>'
            '<span id="save-status" role="status" aria-live="polite"></span>'
            "</div>"
        )
    elif not export_mode:
        controls = '<p class="viewer-note screen-only">Viewer mode — only administrators can edit KPI ownership and target values.</p>'

    script = ""
    if can_edit and not export_mode:
        state = json.dumps(
            {
                "csrfToken": csrf_token,
                "updateBaseUrl": f"/v1/workspace/investor-blueprints/{snapshot['id']}",
            },
            separators=(",", ":"),
        ).replace("<", "\\u003c")
        script = f"""
<script nonce="{nonce}">
(() => {{
  const state = {state};
  const toggle = document.getElementById("edit-toggle");
  const save = document.getElementById("save-changes");
  const status = document.getElementById("save-status");
  let editing = false;

  toggle.addEventListener("click", () => {{
    editing = !editing;
    document.body.classList.toggle("edit-mode", editing);
    toggle.textContent = editing ? "Cancel editing" : "Edit blueprint";
    save.hidden = !editing;
    status.textContent = "";
  }});

  save.addEventListener("click", async () => {{
    const changed = [];
    for (const row of document.querySelectorAll(".kpi-row")) {{
      const owner = row.querySelector(".owner-input").value.trim();
      const target = Number(row.querySelector(".target-input").value);
      if (!Number.isFinite(target) || target <= 0) {{
        status.textContent = "Each KPI target must be greater than zero.";
        return;
      }}
      const payload = {{}};
      if (owner !== row.dataset.owner) payload.owner = owner || null;
      if (target !== Number(row.dataset.target)) payload.target_value = target;
      if (Object.keys(payload).length) changed.push([row.dataset.kpiId, payload]);
    }}
    if (!changed.length) {{
      status.textContent = "No changes to save.";
      return;
    }}
    save.disabled = true;
    status.textContent = "Saving…";
    try {{
      for (const [id, payload] of changed) {{
        const response = await fetch(`${{state.updateBaseUrl}}/kpis/${{id}}`, {{
          method: "PATCH",
          credentials: "same-origin",
          headers: {{"Content-Type": "application/json", "X-CSRF-Token": state.csrfToken}},
          body: JSON.stringify(payload),
        }});
        if (!response.ok) throw new Error("Save request failed");
      }}
      status.textContent = "Saved. Refreshing KPI progress…";
      window.location.reload();
    }} catch (_) {{
      status.textContent = "Changes could not be saved. Please refresh and try again.";
      save.disabled = false;
    }}
  }});
}})();
</script>"""

    page_label = "Investor export" if export_mode else "Investor blueprint"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-{nonce}'; connect-src 'self'; form-action 'self'; base-uri 'none'">
  <title>{title} — {page_label}</title>
  <style nonce="{nonce}">
    @page {{ size: letter; margin: .36in; }}
    :root {{ color-scheme: light; --ink:#10243a; --muted:#64748b; --line:#dbe4ee; --surface:#f8fafc; --navy:#0f2d4a; --teal:#0f766e; }}
    * {{ box-sizing:border-box; }} body {{ margin:0; background:#e8eef5; color:var(--ink); font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
    .page {{ width:min(100%, 960px); margin:32px auto; padding:30px; background:white; box-shadow:0 14px 36px rgba(15,45,74,.13); }}
    .masthead {{ display:flex; justify-content:space-between; gap:20px; border-bottom:3px solid var(--teal); padding-bottom:16px; }}
    .eyebrow {{ margin:0 0 5px; font-size:11px; line-height:1.15; font-weight:800; letter-spacing:.12em; text-transform:uppercase; color:var(--teal); }}
    h1 {{ margin:0; font-size:30px; line-height:1.1; letter-spacing:-.03em; }} h2 {{ margin:0; font-size:18px; }} h3 {{ margin:0; font-size:16px; line-height:1.25; }}
    .as-of {{ margin:3px 0 0; color:var(--muted); font-size:13px; white-space:nowrap; }}
    .controls {{ display:flex; align-items:center; justify-content:flex-end; gap:10px; margin:16px 0 0; min-height:38px; }}
    button {{ border:0; border-radius:7px; cursor:pointer; font:inherit; font-weight:700; padding:9px 13px; }} button:disabled {{ cursor:wait; opacity:.65; }} .primary {{ background:var(--teal); color:#fff; }} .secondary {{ background:#e7eef5; color:var(--navy); }} #save-status {{ color:var(--muted); font-size:13px; }}
    .viewer-note {{ margin:16px 0 0; color:var(--muted); font-size:13px; text-align:right; }}
    .signal-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin:20px 0 24px; }}
    .signal-card {{ min-height:128px; padding:16px; border:1px solid var(--line); border-left:5px solid var(--status-color,#94a3b8); border-radius:8px; background:linear-gradient(135deg,#fff,var(--surface)); }}
    .signal-card.status-achieved {{ --status-color:#047857; }} .signal-card.status-on_track {{ --status-color:#2563eb; }} .signal-card.status-watch {{ --status-color:#b45309; }} .signal-card.status-at_risk {{ --status-color:#b91c1c; }}
    .signal-card p {{ margin:0 0 13px; color:var(--muted); font-size:12px; font-weight:750; text-transform:uppercase; letter-spacing:.08em; }} .signal-card strong {{ display:block; font-size:24px; letter-spacing:-.03em; }} .signal-card span {{ display:block; color:var(--muted); font-size:12px; margin-top:4px; }} .signal-card em {{ display:block; font-size:12px; font-style:normal; font-weight:800; margin-top:10px; }}
    .milestone-group {{ margin-top:20px; break-inside:avoid; }} .group-heading {{ display:flex; align-items:baseline; gap:9px; margin-bottom:8px; }} .group-heading .eyebrow {{ margin:0; }}
    .kpi-row {{ display:grid; grid-template-columns:minmax(0,1fr) 190px; gap:18px; padding:15px 0; border-top:1px solid var(--line); break-inside:avoid; }}
    .kpi-heading {{ display:flex; align-items:flex-start; justify-content:space-between; gap:12px; }} .description {{ margin:4px 0 0; color:var(--muted); font-size:12px; line-height:1.35; }}
    .status {{ flex:none; display:inline-flex; align-items:center; border-radius:999px; padding:4px 8px; font-size:11px; font-weight:800; white-space:nowrap; }} .status-achieved {{ color:#065f46; background:#d1fae5; }} .status-on_track {{ color:#1d4ed8; background:#dbeafe; }} .status-watch {{ color:#92400e; background:#fef3c7; }} .status-at_risk {{ color:#991b1b; background:#fee2e2; }}
    .metric-line {{ display:flex; align-items:baseline; flex-wrap:wrap; gap:6px; margin:11px 0 7px; }} .metric-line strong {{ font-size:20px; letter-spacing:-.02em; }} .metric-line span {{ color:var(--muted); font-size:12px; }} .metric-line .variance {{ margin-left:auto; font-weight:700; }}
    .progress-shell {{ display:grid; grid-template-columns:minmax(0,1fr) auto; align-items:center; gap:8px; }} .progress {{ height:9px; overflow:hidden; border-radius:999px; background:#e4ebf2; }} .progress::before {{ content:""; display:block; width:var(--progress); height:100%; border-radius:inherit; background:var(--status-color); }} .progress-label {{ color:var(--muted); font-size:11px; font-variant-numeric:tabular-nums; }}
    .accountability {{ border-left:1px solid var(--line); padding-left:15px; }} .accountability strong {{ display:block; font-size:14px; }} .accountability > span {{ color:var(--muted); display:block; font-size:12px; margin-top:4px; }}
    .edit-fields {{ display:none; margin-top:10px; }} .edit-mode .edit-fields {{ display:grid; gap:7px; }} .edit-fields label {{ color:var(--muted); display:grid; gap:3px; font-size:11px; font-weight:700; }} .edit-fields input {{ width:100%; border:1px solid #b6c7d8; border-radius:5px; color:var(--ink); font:inherit; font-size:12px; padding:6px; }} .edit-mode .owner-display {{ display:none; }}
    .footer {{ margin-top:23px; padding-top:10px; border-top:1px solid var(--line); color:var(--muted); font-size:10px; display:flex; justify-content:space-between; gap:16px; }}
    @media (max-width:700px) {{ .page {{ margin:0; box-shadow:none; padding:20px; }} .masthead,.kpi-row {{ display:block; }} .as-of {{ margin-top:10px; }} .signal-grid {{ grid-template-columns:1fr; }} .accountability {{ border-left:0; border-top:1px solid var(--line); margin-top:13px; padding:12px 0 0; }} .controls {{ justify-content:flex-start; flex-wrap:wrap; }} }}
    @media print {{ body {{ background:#fff; }} .page {{ width:auto; margin:0; padding:0; box-shadow:none; }} .screen-only {{ display:none !important; }} h1 {{ font-size:25px; }} .signal-grid {{ margin:14px 0 17px; }} .signal-card {{ min-height:100px; padding:12px; }} .milestone-group {{ margin-top:14px; }} .kpi-row {{ padding:10px 0; }} .footer {{ margin-top:13px; }} }}
  </style>
</head>
<body>
  <main class="page">
    <header class="masthead"><div><p class="eyebrow">AIR AGENTS · Investor operating snapshot</p><h1>{title}</h1></div><p class="as-of">As of {as_of_date}</p></header>
    {controls}
    <section class="signal-grid" aria-label="Investor highlights">{summary}</section>
    {sections or '<p class="empty">No KPI targets have been added to this blueprint yet.</p>'}
    <footer class="footer"><span>Investor preset · Revenue, retention &amp; growth milestones</span><span>Source: AIR AGENTS blueprint workspace</span></footer>
  </main>
  {script}
</body>
</html>"""
