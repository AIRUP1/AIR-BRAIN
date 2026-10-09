"""CLI:  python -m webex_batch_dialer run call_list.csv [--dnc dnc.txt] [--limit N] [--dry-run]

Env: WEBEX_CLIENT_ID, WEBEX_CLIENT_SECRET, WEBEX_REFRESH_TOKEN  (or WEBEX_ACCESS_TOKEN)
"""

import argparse
import os
import sys
from pathlib import Path

from .dialer import BatchDialer, DISPOSITIONS, load_call_list
from .webex_client import WebexClient


def prompt_disposition(r):
    print(f"\n[{r.business_name}] {r.phone_e164} - log result: {', '.join(DISPOSITIONS)} (enter = auto)")
    d = input("disposition> ").strip().lower()
    while d and d not in DISPOSITIONS:
        d = input("one of the listed values> ").strip().lower()
    return d, input("note> ").strip() if d else ""


def main(argv=None):
    p = argparse.ArgumentParser(prog="webex_batch_dialer")
    p.add_argument("command", choices=["run", "sync"])
    p.add_argument("call_list")
    p.add_argument("--dnc", help="file with one number per line")
    p.add_argument("--limit", type=int)
    p.add_argument("--state", default="dialer_state.jsonl")
    p.add_argument("--out", default="dialer_results.csv")
    p.add_argument("--dry-run", action="store_true", help="validate the list and print the queue only")
    p.add_argument("--no-prompt", action="store_true")
    p.add_argument("--ignore-hours", action="store_true")
    a = p.parse_args(argv)

    dnc = Path(a.dnc).read_text().split() if a.dnc else []
    records, warnings = load_call_list(a.call_list, dnc)
    for w in warnings:
        print("warn:", w, file=sys.stderr)
    print(f"{len(records)} callable numbers")
    if a.dry_run:
        for r in records:
            print(f"  {r.phone_e164}  {r.business_name}")
        return 0

    client = WebexClient(
        os.environ.get("WEBEX_CLIENT_ID"), os.environ.get("WEBEX_CLIENT_SECRET"),
        os.environ.get("WEBEX_REFRESH_TOKEN"), os.environ.get("WEBEX_ACCESS_TOKEN"),
    )
    d = BatchDialer(client, records, a.state, None if a.no_prompt else prompt_disposition,
                    enforce_hours=not a.ignore_hours)
    if a.command == "run":
        d.run(a.limit)
    else:
        print(f"synced {d.sync_history()} calls from Webex history")
    d.export(a.out)
    print("results ->", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
