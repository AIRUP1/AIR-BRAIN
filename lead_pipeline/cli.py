"""Command line: import, research, prepare calls, record outcomes.

This tool never dials. `prepare` writes call bodies for eligible leads; a person
reviews them and places each call. `record` folds the results back in.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

from .leads import (
    Lead,
    callable_reason,
    clean_leads,
    load_leads,
    load_suppression,
    save_leads,
)
from .memory import ResearchMemory
from .outcomes import apply_outcome, classify
from .prompt import build_call_body, load_offer
from .research import browserless_fetcher, research_lead


def _cmd_import(args: argparse.Namespace) -> int:
    leads, problems = clean_leads(load_leads(args.input))
    save_leads(leads, args.out)
    print(f"Kept {len(leads)} leads -> {args.out}")
    for problem in problems:
        print(f"  skipped: {problem}", file=sys.stderr)
    return 0


def _cmd_research(args: argparse.Namespace) -> int:
    leads = load_leads(args.input)
    memory = ResearchMemory(args.memory)
    fetch = browserless_fetcher(os.environ.get("BROWSERLESS_API_KEY"))
    done = 0
    for lead in leads:
        if args.limit and done >= args.limit:
            break
        if lead.research_summary and not args.refresh:
            continue
        result = research_lead(lead, fetch, memory, city=args.city or "")
        print(f"{lead.merchant_business_name}: {result['sources']} pages, POS hint "
              f"'{result['pos_hint'] or 'none'}'")
        done += 1
    save_leads(leads, args.out or args.input)
    return 0


def _cmd_prepare(args: argparse.Namespace) -> int:
    leads = load_leads(args.input)
    suppression = load_suppression(args.dnc)
    offer = load_offer(args.offer)
    bodies: List[dict] = []
    for lead in leads:
        reason = callable_reason(lead, suppression, retry=args.retry)
        if reason:
            print(f"skip {lead.merchant_business_name}: {reason}", file=sys.stderr)
            continue
        if args.limit and len(bodies) >= args.limit:
            break
        bodies.append(
            build_call_body(lead, args.agent_id, offer, args.company, args.max_seconds)
        )
    Path(args.out).write_text(
        "".join(json.dumps(body) + "\n" for body in bodies), encoding="utf-8"
    )
    print(f"Wrote {len(bodies)} call bodies -> {args.out}. Nothing was dialed.")
    return 0


def _cmd_record(args: argparse.Namespace) -> int:
    leads = load_leads(args.input)
    session = json.loads(Path(args.session).read_text(encoding="utf-8"))
    transcript = json.loads(Path(args.transcript).read_text(encoding="utf-8"))
    transcript = transcript.get("data", transcript)
    session_data = session.get("data", session)
    target: Optional[Lead] = next(
        (lead for lead in leads if lead.phone_number == args.phone), None
    )
    if target is None:
        print(f"No lead with phone {args.phone}", file=sys.stderr)
        return 1
    flags = classify(session_data, transcript)
    apply_outcome(target, flags, session_id=str(session_data.get("id", "")))
    save_leads(leads, args.out or args.input)
    shown = {k: v for k, v in flags.items() if v}
    print(f"{target.merchant_business_name}: {shown}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lead_pipeline", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    imp = sub.add_parser("import", help="clean a CSV/XML sheet (phones, duplicates)")
    imp.add_argument("input")
    imp.add_argument("--out", required=True, help=".csv or .xml")
    imp.set_defaults(func=_cmd_import)

    res = sub.add_parser("research", help="public-web research into memory")
    res.add_argument("input")
    res.add_argument("--memory", default="lead_data/research_memory.jsonl")
    res.add_argument("--city", help="narrow searches to a city")
    res.add_argument("--limit", type=int, default=0)
    res.add_argument("--refresh", action="store_true")
    res.add_argument("--out")
    res.set_defaults(func=_cmd_research)

    prep = sub.add_parser("prepare", help="write call bodies for eligible leads")
    prep.add_argument("input")
    prep.add_argument("--agent-id", required=True)
    prep.add_argument("--offer", required=True, help="file: what the agent may say")
    prep.add_argument("--company", default="AIR AGENTS")
    prep.add_argument("--dnc", help="do-not-call file, one number per line")
    prep.add_argument("--limit", type=int, default=0)
    prep.add_argument("--max-seconds", type=int, default=180)
    prep.add_argument("--retry", action="store_true")
    prep.add_argument("--out", required=True)
    prep.set_defaults(func=_cmd_prepare)

    rec = sub.add_parser("record", help="write a call's outcome back to the sheet")
    rec.add_argument("input")
    rec.add_argument("--phone", required=True, help="E.164 of the lead called")
    rec.add_argument("--session", required=True, help="sessions_get JSON")
    rec.add_argument("--transcript", required=True, help="sessions_transcript_get JSON")
    rec.add_argument("--out")
    rec.set_defaults(func=_cmd_record)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
