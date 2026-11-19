"""CLI: python -m air_brain_agent run "find 10 ..." | report | feedback <key> accepted "why" | export"""

from __future__ import annotations

import argparse
import json

from .agent import AirBrainAgent
from .gateway import ModelGateway
from .orchestrator import Orchestrator, Task, default_tools, load_workflows
from .report import export
from .workflow import Workflow, WorkflowEngine


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
    b = sub.add_parser("brain", help="route a task through the orchestrator")
    b.add_argument("task")
    b.add_argument("--task-type")
    b.add_argument("--priority", choices=["urgent", "high", "normal", "low"], default="normal")
    sub.add_parser("workflows", help="list workflows")
    sub.add_parser("schema", help="print the workflow JSON Schema")
    e = sub.add_parser("export")
    e.add_argument("--fmt", choices=["csv", "json"], default="csv")
    a = p.parse_args()

    if a.cmd == "schema":
        print(json.dumps(Workflow.model_json_schema(), indent=2, sort_keys=True))
        return
    agent = AirBrainAgent(a.data_dir)
    if a.cmd == "workflows":
        for name, wf in load_workflows().items():
            print(f"{name}: {wf.description}")
    elif a.cmd == "brain":
        orch = Orchestrator(WorkflowEngine(default_tools(agent), ModelGateway()))
        res = orch.handle(Task(task_type=a.task_type, payload=a.task, priority=a.priority))
        print(res.model_dump_json(indent=2))
    elif a.cmd == "run":
        print(agent.run(a.goal, a.max_iterations))
    elif a.cmd == "report":
        print(agent.report(a.min_score))
    elif a.cmd == "feedback":
        print(agent.record_feedback(a.lead_key, a.verdict, a.reason))
    else:
        print(export(agent.store.list_leads(), a.fmt))


if __name__ == "__main__":
    main()
