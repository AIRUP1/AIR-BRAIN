"""AI Brain orchestrator: decide which workflow handles a task, then run it through the engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from .agent import AirBrainAgent
from .gateway import GatewayError, ModelGateway, ModelRequest
from .workflow import RunResult, Workflow, WorkflowEngine
from .workflow.engine import _parse_json

WORKFLOW_DIR = Path(__file__).parent / "workflows"

# Keyword rules for tasks without an explicit task_type (checked in order, case-insensitive).
DEFAULT_RULES: List[tuple] = [
    ("lead_feedback", ["accept lead", "reject lead", "feedback on lead"]),
    ("lead_report", ["report", "export", "list leads", "show leads"]),
    ("lead_research", ["find ", "lead", "prospect", "scrape", "research compan", "businesses"]),
]


class Task(BaseModel):
    task_type: Optional[str] = None
    payload: str
    priority: Literal["urgent", "high", "normal", "low"] = "normal"
    inputs: Dict[str, Any] = Field(default_factory=dict)  # extra typed inputs for the chosen workflow


class RouteDecision(BaseModel):
    route: str
    confidence: float = Field(ge=0, le=1)
    reasoning: str
    source: Literal["explicit", "rules", "llm", "default"]
    model: ModelRequest = Field(default_factory=ModelRequest)  # model policy implied by priority


class OrchestratorResult(BaseModel):
    decision: RouteDecision
    run: RunResult


def load_workflows(directory: Path = WORKFLOW_DIR) -> Dict[str, Workflow]:
    workflows = {}
    for path in sorted(directory.glob("*.json")):
        wf = Workflow.model_validate_json(path.read_text(encoding="utf-8"))
        workflows[wf.name] = wf
    return workflows


def default_tools(agent: AirBrainAgent) -> Dict[str, Any]:
    """Tool registry exposing the lead agent to workflows."""
    return {
        "lead.run": lambda goal, max_iterations=40: {"summary": agent.run(goal, max_iterations)},
        "lead.report": lambda min_score=0: {"markdown": agent.report(min_score)},
        "lead.feedback": lambda lead_key, verdict, reason=None: agent.record_feedback(lead_key, verdict, reason),
        "scrape.url": lambda url: {
            "title": (r := agent.scraper.fetch(url)).title,
            "text": r.text[:4000],
            "emails": r.emails,
        },
    }


class Orchestrator:
    def __init__(
        self,
        engine: WorkflowEngine,
        workflows: Optional[Dict[str, Workflow]] = None,
        gateway: Optional[ModelGateway] = None,
        rules: Optional[List[tuple]] = None,
        fallback_route: str = "general",
    ) -> None:
        self.engine, self.gateway = engine, gateway or engine.gateway
        self.workflows = workflows if workflows is not None else load_workflows()
        self.rules = rules if rules is not None else DEFAULT_RULES
        self.fallback_route = fallback_route
        for wf in self.workflows.values():  # fail at startup, not mid-task
            problems = engine.check(wf)
            if problems:
                raise ValueError(f"workflow {wf.name}: {'; '.join(problems)}")

    @staticmethod
    def model_policy(priority: str) -> ModelRequest:
        return {
            "urgent": ModelRequest(latency="fast", cost="balanced"),
            "high": ModelRequest(cost="optimize_quality"),
            "normal": ModelRequest(),
            "low": ModelRequest(latency="batch", cost="optimize_cost"),
        }[priority]

    def route(self, task: Task) -> RouteDecision:
        policy = self.model_policy(task.priority)
        if task.task_type:
            if task.task_type in self.workflows:
                return RouteDecision(
                    route=task.task_type,
                    confidence=1.0,
                    source="explicit",
                    model=policy,
                    reasoning="task_type names a registered workflow",
                )
            raise ValueError(f"unknown task_type '{task.task_type}'; known: {sorted(self.workflows)}")
        low = task.payload.lower()
        for route, needles in self.rules:
            hit = next((n for n in needles if n in low), None)
            if route in self.workflows and hit:
                return RouteDecision(
                    route=route,
                    confidence=0.8,
                    source="rules",
                    model=policy,
                    reasoning=f"matched keyword '{hit.strip()}'",
                )
        if self.gateway is not None:
            prompt = (
                f"Choose the best workflow for the task. Workflows: "
                f"{ {n: w.description for n, w in self.workflows.items()} }. "
                'Reply JSON only: {"route": "<name>", "confidence": 0-1, "reasoning": "<why>"}\n\n'
                f"Task: {task.payload[:4000]}"
            )
            try:
                comp = self.gateway.complete(
                    ModelRequest(complexity="simple", latency="fast"),
                    prompt,
                    "You route tasks for an AI orchestration hub.",
                    300,
                )
                data = _parse_json(comp.text)
                if data.get("route") in self.workflows:
                    return RouteDecision(
                        route=data["route"],
                        confidence=min(max(float(data.get("confidence", 0.5)), 0), 1),
                        reasoning=str(data.get("reasoning", "")),
                        source="llm",
                        model=policy,
                    )
            except (GatewayError, ValueError, AttributeError, TypeError):
                pass
        return RouteDecision(
            route=self.fallback_route,
            confidence=0.3,
            source="default",
            model=policy,
            reasoning="no rule or model choice matched; using fallback workflow",
        )

    def handle(self, task: Task) -> OrchestratorResult:
        decision = self.route(task)
        wf = self.workflows[decision.route]
        inputs = {"task": task.payload, **task.inputs}
        known = {f.name for f in wf.node(next(n.id for n in wf.nodes if n.type == "input")).fields}
        inputs = {k: v for k, v in inputs.items() if k in known}  # workflows declare exactly what they accept
        return OrchestratorResult(decision=decision, run=self.engine.run(wf, inputs))
