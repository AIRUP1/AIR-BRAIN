"""CLI: python -m air_brain_agent run "find 10 ..." | report | feedback <key> accepted "why" | export"""

from __future__ import annotations

import argparse

from .agent import AirBrainAgent
from .report import export


def main() -> None:
    p = argparse.ArgumentParser(prog="air_brain_agent")
    p.add_argument("--data-dir", default="./data/air_brain")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("goal")
    r.add_argument("--max-iterations", type=int, default=40)
    rep = sub.add_parser("report")
    rep.add_argument("--min-score", type=float, default=0)
    f = sub.add_parser("feedback")
    f.add_argument("lead_key")
    f.add_argument("verdict", choices=["accepted", "rejected", "needs_work"])
    f.add_argument("reason", nargs="?")
    e = sub.add_parser("export")
    e.add_argument("--fmt", choices=["csv", "json"], default="csv")
    a = p.parse_args()

    agent = AirBrainAgent(a.data_dir)
    if a.cmd == "run":
        print(agent.run(a.goal, a.max_iterations))
    elif a.cmd == "report":
        print(agent.report(a.min_score))
    elif a.cmd == "feedback":
        print(agent.record_feedback(a.lead_key, a.verdict, a.reason))
    else:
        print(export(agent.store.list_leads(), a.fmt))


if __name__ == "__main__":
    main()
