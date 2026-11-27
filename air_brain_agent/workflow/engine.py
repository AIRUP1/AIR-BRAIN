"""Executes a validated Workflow: topological order, router branching, retries, per-node trace."""

from __future__ import annotations

import json
import re
import time
from typing import Any, Callable, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from ..gateway import GatewayError, ModelGateway
from .schema import TEMPLATE_RE, FieldSpec, Workflow

_TYPES = {"string": str, "number": (int, float), "boolean": bool, "object": dict, "array": list}


class NodeRun(BaseModel):
    id: str
    status: Literal["succeeded", "failed", "skipped"]
    output: Any = None
    error: Optional[str] = None
    route: Optional[str] = None
    attempts: int = 0
    duration_ms: int = 0
    model: Optional[str] = None  # provider:model that served an llm/router node


class RunResult(BaseModel):
    workflow: str
    status: Literal["succeeded", "failed"]
    outputs: Dict[str, Any] = Field(default_factory=dict)
    nodes: Dict[str, NodeRun] = Field(default_factory=dict)
    error: Optional[str] = None


class WorkflowError(Exception):
    pass


def _lookup(ctx: Dict[str, Any], ref: str, path: Optional[str]) -> Any:
    if ref not in ctx:
        raise WorkflowError(f"template references '{ref}', which did not run (skipped or failed)")
    value = ctx[ref]
    for part in (path or "").split("."):
        if not part:
            continue
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            raise WorkflowError(f"template {{{{{ref}.{path}}}}} does not resolve")
    return value


def render(value: Any, ctx: Dict[str, Any]) -> Any:
    """Resolve {{node.path}} templates. A string that is exactly one template keeps the referenced value's type."""
    if isinstance(value, str):
        full = TEMPLATE_RE.fullmatch(value.strip())
        if full:
            return _lookup(ctx, full.group(1), full.group(2))
        return TEMPLATE_RE.sub(lambda m: _as_text(_lookup(ctx, m.group(1), m.group(2))), value)
    if isinstance(value, dict):
        return {k: render(v, ctx) for k, v in value.items()}
    if isinstance(value, list):
        return [render(v, ctx) for v in value]
    return value


def _as_text(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, default=str)


def _parse_json(text: str) -> Any:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        return json.loads(text)
    except ValueError:
        start, end = text.find("{"), text.rfind("}")
        if 0 <= start < end:
            return json.loads(text[start : end + 1])
        raise


class WorkflowEngine:
    def __init__(
        self, tools: Optional[Dict[str, Callable[..., Any]]] = None, gateway: Optional[ModelGateway] = None
    ) -> None:
        self.tools = dict(tools or {})
        self.gateway = gateway

    def check(self, wf: Workflow) -> List[str]:
        """Static problems that depend on this engine: unknown tools, llm nodes without a gateway."""
        problems = []
        for n in wf.nodes:
            if n.type == "tool" and n.tool not in self.tools:
                problems.append(f"node {n.id}: unknown tool '{n.tool}'")
            if (n.type == "llm" or (n.type == "router" and n.use_llm)) and self.gateway is None:
                problems.append(f"node {n.id}: needs a model gateway")
        return problems

    def run(self, wf: Workflow, inputs: Optional[Dict[str, Any]] = None) -> RunResult:
        problems = self.check(wf)
        if problems:
            raise WorkflowError("; ".join(problems))
        ctx: Dict[str, Any] = {}
        runs: Dict[str, NodeRun] = {}
        result = RunResult(workflow=wf.name, status="succeeded")  # pydantic copies dicts, so nodes is set at the end
        halted = False
        for node_id in wf.topological_order():
            node = wf.node(node_id)
            if halted or (node.type != "input" and not self._active_inputs(wf, node_id, runs)):
                runs[node_id] = NodeRun(id=node_id, status="skipped")
                continue
            started, attempts, error, out, route, model = time.perf_counter(), 0, None, None, None, None
            for attempts in range(1, node.retries + 2):
                try:
                    out, route, model = self._execute(node, ctx, inputs or {})
                    error = None
                    break
                except Exception as exc:
                    error = f"{type(exc).__name__}: {exc}"
            ms = int((time.perf_counter() - started) * 1000)
            if error is None:
                ctx[node_id] = out
                runs[node_id] = NodeRun(
                    id=node_id,
                    status="succeeded",
                    output=out,
                    route=route,
                    attempts=attempts,
                    duration_ms=ms,
                    model=model,
                )
                if node.type == "output":
                    result.outputs.update(out)
            else:
                runs[node_id] = NodeRun(id=node_id, status="failed", error=error, attempts=attempts, duration_ms=ms)
                if node.on_error == "fail":
                    result.status, result.error, halted = "failed", f"node {node_id} failed: {error}", True
        result.nodes = runs
        return result

    @staticmethod
    def _active_inputs(wf: Workflow, node_id: str, runs: Dict[str, NodeRun]) -> list:
        active = []
        for e in wf.incoming(node_id):
            src = runs.get(e.source)
            if src and src.status == "succeeded" and (e.condition is None or src.route == e.condition):
                active.append(e)
        return active

    # -- node implementations ----------------------------------------------------------
    def _execute(self, node, ctx: Dict[str, Any], inputs: Dict[str, Any]):
        if node.type == "input":
            return self._validate_inputs(node.fields, inputs), None, None
        if node.type == "tool":
            out = self.tools[node.tool](**render(node.args, ctx))
            return (out if isinstance(out, dict) else {"result": out}), None, None
        if node.type == "output":
            return render(node.fields, ctx), None, None
        if node.type == "llm":
            comp = self.gateway.complete(
                node.model, render(node.prompt, ctx), render(node.system, ctx), node.max_tokens
            )
            out: Dict[str, Any] = {"text": comp.text}
            if node.json_output:
                out["json"] = _parse_json(comp.text)
            return out, None, f"{comp.provider}:{comp.model}"
        return self._route(node, ctx)

    @staticmethod
    def _validate_inputs(fields: List[FieldSpec], inputs: Dict[str, Any]) -> Dict[str, Any]:
        known = {f.name for f in fields}
        extra = set(inputs) - known
        if extra:
            raise WorkflowError(f"unknown input(s): {sorted(extra)}")
        out: Dict[str, Any] = {}
        for f in fields:
            if f.name in inputs:
                value = inputs[f.name]
                ok = isinstance(value, _TYPES[f.type]) and not (f.type == "number" and isinstance(value, bool))
                if not ok:
                    raise WorkflowError(f"input '{f.name}' must be {f.type}")
                out[f.name] = value
            elif f.default is not None:
                out[f.name] = f.default
            elif f.required:
                raise WorkflowError(f"missing required input '{f.name}'")
            else:
                out[f.name] = None  # optional and absent: templates resolve to null instead of failing
        return out

    def _route(self, node, ctx: Dict[str, Any]):
        value = _as_text(render(node.on, ctx))
        low = value.lower()
        if value in node.routes:  # exact route name wins
            return {"route": value, "via": "exact"}, value, None
        for rule in node.rules:
            if any(c.lower() in low for c in rule.contains):
                return {"route": rule.route, "via": "rule"}, rule.route, None
        if node.use_llm:
            prompt = (
                f"Choose the single best route for this input. Routes: {node.routes}. "
                f'Reply with JSON only: {{"route": "<one of the routes>"}}\n\nInput:\n{value[:4000]}'
            )
            try:
                comp = self.gateway.complete(node.model, prompt, "You are a precise routing classifier.", 100)
                choice = _parse_json(comp.text).get("route")
                if choice in node.routes:
                    return {"route": choice, "via": "llm"}, choice, f"{comp.provider}:{comp.model}"
            except (GatewayError, ValueError, AttributeError):
                pass  # fall through to the default route
        return {"route": node.default, "via": "default"}, node.default, None
