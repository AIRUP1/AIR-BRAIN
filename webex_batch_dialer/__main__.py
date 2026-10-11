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


def build_client():
    have = all(os.environ.get(k) for k in ("WEBEX_CLIENT_ID", "WEBEX_CLIENT_SECRET", "WEBEX_REFRESH_TOKEN"))
    if not (have or os.environ.get("WEBEX_ACCESS_TOKEN")):
        print("error: set WEBEX_CLIENT_ID, WEBEX_CLIENT_SECRET and WEBEX_REFRESH_TOKEN "
              "(or WEBEX_ACCESS_TOKEN). Run: python -m webex_batch_dialer.get_webex_token", file=sys.stderr)
        return None
    return WebexClient(os.environ.get("WEBEX_CLIENT_ID"), os.environ.get("WEBEX_CLIENT_SECRET"),
                       os.environ.get("WEBEX_REFRESH_TOKEN"), os.environ.get("WEBEX_ACCESS_TOKEN"))


def timing(a):
    gap, poll = (0.5, 0.5) if a.fast else (a.gap, a.poll)
    return {"gap_seconds": gap, "poll_seconds": poll, "ring_timeout": a.ring_timeout}


def run_auto(a, dnc):
    from .automation import TooManyFailures, run_inbox
    client = build_client()
    if client is None:
        return 2
    try:
        run_inbox(client, a.call_list, dnc, max_failures=a.max_failures, once=a.once, batch_size=a.batch_size, **timing(a))
    except TooManyFailures as e:
        print("stopped:", e, file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        return 0
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="webex_batch_dialer")
    p.add_argument("command", choices=["run", "sync", "auto", "history"])
    p.add_argument("call_list", nargs="?", default="", help="CSV file (run/sync) or inbox folder (auto); not needed for history")
    p.add_argument("--max-failures", type=int, default=5, help="auto: stop after this many failed dials in a row")
    p.add_argument("--batch-size", type=int, help="auto: max calls per pass (leave the rest for the next scheduled pass)")
    p.add_argument("--gap", type=float, default=2.0, help="seconds to pause between calls (default 2, was 5)")
    p.add_argument("--poll", type=float, default=1.0, help="seconds between call-state checks (default 1)")
    p.add_argument("--ring-timeout", type=float, default=5.0, help="hang up if unanswered after this many seconds (default 5)")
    p.add_argument("--fast", action="store_true", help="shortcut for --gap 0.5 --poll 0.5 (watch for Webex rate limits)")
    p.add_argument("--once", action="store_true", help="auto: process the inbox once and exit (for cron)")
    p.add_argument("--dnc", help="file with one number per line")
    p.add_argument("--limit", type=int)
    p.add_argument("--state", default="dialer_state.jsonl")
    p.add_argument("--out", default="dialer_results.csv")
    p.add_argument("--dry-run", action="store_true", help="validate the list and print the queue only")
    p.add_argument("--no-prompt", action="store_true")
    p.add_argument("--ignore-hours", action="store_true")
    a = p.parse_args(argv)

    dnc = Path(a.dnc).read_text().split() if a.dnc else []
    if a.command == "auto":
        return run_auto(a, dnc)
    if a.command == "history":
        from .dialer import export_history
        client = build_client()
        if client is None:
            return 2
        out = a.out if a.out != "dialer_results.csv" else "webex_call_history.csv"
        print(f"{export_history(client, out)} calls -> {out}")
        return 0
    records, warnings = load_call_list(a.call_list, dnc)
    for w in warnings:
        print("warn:", w, file=sys.stderr)
    print(f"{len(records)} callable numbers")
    if a.dry_run:
        for r in records:
            print(f"  {r.phone_e164}  {r.business_name}")
        return 0

    have_refresh = all(os.environ.get(k) for k in ("WEBEX_CLIENT_ID", "WEBEX_CLIENT_SECRET", "WEBEX_REFRESH_TOKEN"))
    if not (have_refresh or os.environ.get("WEBEX_ACCESS_TOKEN")):
        print("error: set WEBEX_CLIENT_ID, WEBEX_CLIENT_SECRET and WEBEX_REFRESH_TOKEN "
              "(or WEBEX_ACCESS_TOKEN). Run: python -m webex_batch_dialer.get_webex_token", file=sys.stderr)
        return 2

    client = WebexClient(
        os.environ.get("WEBEX_CLIENT_ID"), os.environ.get("WEBEX_CLIENT_SECRET"),
        os.environ.get("WEBEX_REFRESH_TOKEN"), os.environ.get("WEBEX_ACCESS_TOKEN"),
    )
    d = BatchDialer(client, records, a.state, None if a.no_prompt else prompt_disposition,
                    enforce_hours=not a.ignore_hours, **timing(a))
    if a.command == "run":
        d.run(a.limit)
    else:
        print(f"synced {d.sync_history()} calls from Webex history")
    d.export(a.out)
    print("results ->", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
