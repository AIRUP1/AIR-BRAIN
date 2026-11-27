"""Workflow definition schema.

A workflow is a validated DAG. Node configs are a discriminated union on ``type`` so each node type has exactly the
fields it needs. ``{{node_id.path}}`` templates may only reference *upstream* nodes, and router edges must name a
declared route; all of this is checked when the workflow is loaded, not when it runs.
"""

from __future__ import annotations

import re
from collections import defaultdict, deque
from typing import Annotated, Any, Dict, Iterator, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..gateway import ModelRequest

TEMPLATE_RE = re.compile(r"\{\{\s*([A-Za-z_][\w-]*)(?:\.([\w.\-]+))?\s*\}\}")
ID_PATTERN = r"^[A-Za-z_][A-Za-z0-9_-]*$"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FieldSpec(_Strict):
    name: str = Field(pattern=ID_PATTERN)
    type: Literal["string", "number", "boolean", "object", "array"] = "string"
    required: bool = True
    default: Any = None
    description: str = ""


class _NodeBase(_Strict):
    id: str = Field(pattern=ID_PATTERN)
    description: str = ""
    retries: int = Field(default=0, ge=0, le=5)
    on_error: Literal["fail", "continue"] = "fail"


class InputNode(_NodeBase):
    type: Literal["input"] = "input"
    fields: List[FieldSpec] = Field(default_factory=list)


class ToolNode(_NodeBase):
    type: Literal["tool"] = "tool"
    tool: str  # name in the engine's tool registry, e.g. "lead.run"
    args: Dict[str, Any] = Field(default_factory=dict)  # values may contain {{templates}}


class LLMNode(_NodeBase):
    type: Literal["llm"] = "llm"
    prompt: str
    system: Optional[str] = None
    model: ModelRequest = Field(default_factory=ModelRequest)  # the gateway picks provider + model + fallbacks
    max_tokens: int = Field(default=1024, ge=1, le=64000)
    json_output: bool = False  # parse the reply as JSON; output is then {"text", "json"}


class RouteRule(_Strict):
    contains: List[str] = Field(min_length=1)  # case-insensitive substrings of the routed value
    route: str


class RouterNode(_Strict):
    id: str = Field(pattern=ID_PATTERN)
    type: Literal["router"] = "router"
    description: str = ""
    retries: int = Field(default=0, ge=0, le=5)
    on_error: Literal["fail", "continue"] = "fail"
    on: str  # template resolving to the value to route on
    routes: List[str] = Field(min_length=2)
    default: str
    rules: List[RouteRule] = Field(default_factory=list)
    use_llm: bool = False  # ask the gateway to pick a route when no rule matches
    model: ModelRequest = Field(default_factory=lambda: ModelRequest(complexity="simple", latency="fast"))

    @model_validator(mode="after")
    def _check(self) -> "RouterNode":
        if len(set(self.routes)) != len(self.routes):
            raise ValueError(f"router {self.id}: duplicate routes")
        if self.default not in self.routes:
            raise ValueError(f"router {self.id}: default '{self.default}' is not in routes")
        for rule in self.rules:
            if rule.route not in self.routes:
                raise ValueError(f"router {self.id}: rule targets unknown route '{rule.route}'")
        return self


class OutputNode(_Strict):
    id: str = Field(pattern=ID_PATTERN)
    type: Literal["output"] = "output"
    description: str = ""
    retries: int = Field(default=0, ge=0, le=5)
    on_error: Literal["fail", "continue"] = "fail"
    fields: Dict[str, Any]  # name -> value or {{template}}


Node = Annotated[Union[InputNode, ToolNode, LLMNode, RouterNode, OutputNode], Field(discriminator="type")]


class Edge(_Strict):
    source: str
    target: str
    condition: Optional[str] = None  # only valid on edges leaving a router: the route that activates this edge


def _strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)


class Workflow(_Strict):
    schema_version: Literal["1"] = "1"
    name: str = Field(pattern=ID_PATTERN)
    version: str = "1.0.0"
    description: str = ""
    nodes: List[Node] = Field(min_length=2)
    edges: List[Edge] = Field(default_factory=list)

    # -- graph helpers ---------------------------------------------------------
    def node(self, node_id: str):
        return next(n for n in self.nodes if n.id == node_id)

    def incoming(self, node_id: str) -> List[Edge]:
        return [e for e in self.edges if e.target == node_id]

    def topological_order(self) -> List[str]:
        indeg = {n.id: 0 for n in self.nodes}
        out: Dict[str, List[str]] = defaultdict(list)
        for e in self.edges:
            indeg[e.target] += 1
            out[e.source].append(e.target)
        queue = deque(n.id for n in self.nodes if indeg[n.id] == 0)  # declaration order keeps runs deterministic
        order = []
        while queue:
            cur = queue.popleft()
            order.append(cur)
            for nxt in out[cur]:
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    queue.append(nxt)
        if len(order) != len(self.nodes):
            raise ValueError("workflow contains a cycle")
        return order

    def ancestors(self, node_id: str) -> set:
        seen, stack = set(), [e.source for e in self.incoming(node_id)]
        while stack:
            cur = stack.pop()
            if cur not in seen:
                seen.add(cur)
                stack.extend(e.source for e in self.incoming(cur))
        return seen

    # -- validation --------------------------------------------------------------
    @model_validator(mode="after")
    def _validate_graph(self) -> "Workflow":
        ids = [n.id for n in self.nodes]
        if len(set(ids)) != len(ids):
            raise ValueError("node ids must be unique")
        inputs = [n for n in self.nodes if n.type == "input"]
        if len(inputs) != 1:
            raise ValueError("a workflow needs exactly one input node")
        if not any(n.type == "output" for n in self.nodes):
            raise ValueError("a workflow needs at least one output node")
        by_id = {n.id: n for n in self.nodes}
        for e in self.edges:
            if e.source not in by_id or e.target not in by_id:
                raise ValueError(f"edge {e.source}->{e.target} references an unknown node")
            if e.source == e.target:
                raise ValueError(f"edge {e.source}->{e.target} is a self-loop")
            src, dst = by_id[e.source], by_id[e.target]
            if dst.type == "input":
                raise ValueError("the input node cannot have incoming edges")
            if src.type == "output":
                raise ValueError("output nodes cannot have outgoing edges")
            if src.type == "router":
                if e.condition not in src.routes:
                    raise ValueError(f"edge {e.source}->{e.target}: condition must be one of {src.routes}")
            elif e.condition is not None:
                raise ValueError(f"edge {e.source}->{e.target}: only router edges may have a condition")
        for n in self.nodes:
            if n.type == "router":
                covered = {e.condition for e in self.edges if e.source == n.id}
                missing = set(n.routes) - covered
                if missing:
                    raise ValueError(f"router {n.id}: no outgoing edge for route(s) {sorted(missing)}")
            if n.type != "input" and not self.incoming(n.id):
                raise ValueError(f"node {n.id} is unreachable (no incoming edge)")
        self.topological_order()  # raises on cycles
        for n in self.nodes:  # templates may only reference upstream nodes
            allowed = self.ancestors(n.id)
            for text in _strings(n.model_dump(exclude={"id", "type"})):
                for ref, _ in TEMPLATE_RE.findall(text):
                    if ref not in by_id:
                        raise ValueError(f"node {n.id}: template references unknown node '{ref}'")
                    if ref not in allowed:
                        raise ValueError(f"node {n.id}: template references '{ref}', which is not upstream of it")
        return self
