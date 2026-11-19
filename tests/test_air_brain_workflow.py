# pylint: disable=protected-access,redefined-outer-name
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from air_brain_agent.agent import AirBrainAgent
from air_brain_agent.gateway import CallableProvider, GatewayError, ModelGateway, ModelRequest, ModelSpec
from air_brain_agent.orchestrator import Orchestrator, Task, default_tools, load_workflows
from air_brain_agent.schema import ICP
from air_brain_agent.store import Store
from air_brain_agent.workflow import Workflow, WorkflowEngine
from air_brain_agent.workflow.engine import WorkflowError

IN = {"id": "in", "type": "input", "fields": [{"name": "q", "type": "string"}]}
OUT = {"id": "out", "type": "output", "fields": {"a": "{{in.q}}"}}


def wf(nodes, edges, name="t"):
    return {"name": name, "nodes": nodes, "edges": edges}


# ---------------------------------------------------------------- schema
@pytest.mark.parametrize(
    "bad, msg",
    [
        (wf([IN, OUT], [{"source": "in", "target": "zzz"}]), "unknown node"),
        (
            wf(
                [IN, OUT, {"id": "t", "type": "tool", "tool": "x"}],
                [{"source": "in", "target": "t"}, {"source": "t", "target": "out"}, {"source": "out", "target": "t"}],
            ),
            "output nodes",
        ),
        (
            wf(
                [IN, {"id": "a", "type": "tool", "tool": "x"}, {"id": "b", "type": "tool", "tool": "x"}, OUT],
                [
                    {"source": "in", "target": "a"},
                    {"source": "a", "target": "b"},
                    {"source": "b", "target": "a"},
                    {"source": "b", "target": "out"},
                ],
            ),
            "cycle",
        ),
        (
            wf(
                [IN, {"id": "a", "type": "tool", "tool": "x", "args": {"v": "{{out.a}}"}}, OUT],
                [{"source": "in", "target": "a"}, {"source": "a", "target": "out"}],
            ),
            "not upstream",
        ),
        (
            wf(
                [IN, {"id": "a", "type": "tool", "tool": "x", "args": {"v": "{{nope.a}}"}}, OUT],
                [{"source": "in", "target": "a"}, {"source": "a", "target": "out"}],
            ),
            "unknown node 'nope'",
        ),
        (wf([IN, OUT], [{"source": "in", "target": "out", "condition": "x"}]), "only router edges"),
        (
            wf([IN, {"id": "island", "type": "tool", "tool": "x"}, OUT], [{"source": "in", "target": "out"}]),
            "unreachable",
        ),
        (wf([IN, {**IN, "id": "in2"}, OUT], [{"source": "in", "target": "out"}]), "exactly one input"),
        (
            wf(
                [IN, {"id": "a", "type": "tool", "tool": "x", "bogus": 1}, OUT],
                [{"source": "in", "target": "a"}, {"source": "a", "target": "out"}],
            ),
            "bogus",
        ),
    ],
)
def test_invalid_workflows_are_rejected_at_load(bad, msg):
    with pytest.raises(ValidationError, match=msg):
        Workflow.model_validate(bad)


def test_router_validation():
    router = {"id": "r", "type": "router", "on": "{{in.q}}", "routes": ["a", "b"], "default": "a"}
    with pytest.raises(ValidationError, match="no outgoing edge"):
        Workflow.model_validate(
            wf([IN, router, OUT], [{"source": "in", "target": "r"}, {"source": "r", "target": "out", "condition": "a"}])
        )
    with pytest.raises(ValidationError, match="default"):
        Workflow.model_validate(wf([IN, {**router, "default": "zzz"}, OUT], []))


def test_shipped_workflows_valid_and_schema_file_in_sync():
    names = set(load_workflows())
    assert {"lead_research", "lead_report", "lead_feedback", "general"} <= names
    published = json.loads((Path(__file__).parent.parent / "docs" / "workflow.schema.json").read_text())
    assert published == json.loads(
        json.dumps(Workflow.model_json_schema(), sort_keys=True)
    ), "regenerate with: python -m air_brain_agent schema > docs/workflow.schema.json"


# ---------------------------------------------------------------- gateway
def provider(name, fn):
    return CallableProvider(name, lambda model, system, prompt, mt: fn(model, prompt))


CATALOG = [
    ModelSpec(provider="p", model="small", tier=1),
    ModelSpec(provider="p", model="mid", tier=2),
    ModelSpec(provider="p", model="big", tier=3),
]


def test_ranking_policy():
    g = ModelGateway([provider("p", lambda m, p: "ok")], CATALOG)
    def first(**kw):
        return g.rank(ModelRequest(**kw))[0].model

    assert first(complexity="simple") == "small"
    assert first(complexity="moderate") == "mid"
    assert first(complexity="complex") == "big"
    assert first(complexity="complex", latency="realtime") == "small"  # latency is a hard ceiling
    assert first(complexity="moderate", cost="optimize_cost") == "small"
    assert first(complexity="moderate", cost="optimize_quality") == "big"
    assert [s.model for s in g.rank(ModelRequest())] == [
        "mid",
        "small",
        "big",
    ]  # fallback order: nearest tier, cheaper first


def test_fallback_and_circuit_breaker():
    now = [0.0]
    calls = []

    def fn(model, _prompt):
        calls.append(model)
        if model == "mid":
            raise RuntimeError("boom")
        return f"served by {model}"

    g = ModelGateway([provider("p", fn)], CATALOG, failure_threshold=2, cooldown_s=30, clock=lambda: now[0])
    c = g.complete(ModelRequest(), "hi")
    assert c.model == "small" and [a.ok for a in c.attempts] == [False, True]
    g.complete(ModelRequest(), "hi")  # second failure trips the breaker for "mid"
    calls.clear()
    assert g.complete(ModelRequest(), "hi").model == "small" and calls == ["small"]  # mid is skipped
    now[0] = 31  # cooldown over: mid is probed again
    g.complete(ModelRequest(), "hi")
    assert calls[1] == "mid"


def test_all_models_failing_raises_with_attempts():
    def fn(model, _prompt):
        raise ValueError("down")

    g = ModelGateway([provider("p", fn)], CATALOG)
    with pytest.raises(GatewayError) as err:
        g.complete(ModelRequest(), "x")
    assert len(err.value.attempts) == 3


def test_provider_preference_is_soft():
    other = [ModelSpec(provider="q", model="q-mid", tier=2)]
    g = ModelGateway([provider("p", lambda m, p: "p"), provider("q", lambda m, p: "q")], CATALOG + other)
    assert g.rank(ModelRequest(provider="q"))[0].model == "q-mid"


# ---------------------------------------------------------------- engine
def engine(tools=None, reply=lambda m, p: "hello"):
    return WorkflowEngine(tools or {}, ModelGateway([provider("p", reply)], CATALOG))


def test_linear_run_with_typed_templates():
    w = Workflow.model_validate(
        wf(
            [
                {
                    "id": "in",
                    "type": "input",
                    "fields": [{"name": "n", "type": "number"}, {"name": "tag", "type": "string", "required": False}],
                },
                {"id": "t", "type": "tool", "tool": "double", "args": {"x": "{{in.n}}"}},
                {"id": "out", "type": "output", "fields": {"v": "{{t.result}}", "label": "n={{in.n}} tag={{in.tag}}"}},
            ],
            [{"source": "in", "target": "t"}, {"source": "t", "target": "out"}],
        )
    )
    res = engine({"double": lambda x: x * 2}).run(w, {"n": 21})
    assert res.status == "succeeded" and res.outputs == {"v": 42, "label": "n=21 tag=null"}  # full-template keeps type
    with pytest.raises(WorkflowError, match="unknown tool"):
        engine().run(w, {"n": 1})


def test_input_validation_fails_the_run_cleanly():
    w = Workflow.model_validate(wf([IN, OUT], [{"source": "in", "target": "out"}]))
    assert engine().run(w, {}).error.endswith("missing required input 'q'")
    assert "must be string" in engine().run(w, {"q": 5}).error
    assert "unknown input" in engine().run(w, {"q": "a", "z": 1}).error


ROUTED = wf(
    [
        IN,
        {
            "id": "r",
            "type": "router",
            "on": "{{in.q}}",
            "routes": ["lead", "other"],
            "default": "other",
            "rules": [{"contains": ["prospect"], "route": "lead"}],
        },
        {"id": "lead_t", "type": "tool", "tool": "lead"},
        {"id": "other_t", "type": "tool", "tool": "other"},
        {"id": "out", "type": "output", "fields": {"who": "{{lead_t.result}}"}},
        {"id": "out2", "type": "output", "fields": {"who2": "{{other_t.result}}"}},
    ],
    [
        {"source": "in", "target": "r"},
        {"source": "r", "target": "lead_t", "condition": "lead"},
        {"source": "r", "target": "other_t", "condition": "other"},
        {"source": "lead_t", "target": "out"},
        {"source": "other_t", "target": "out2"},
    ],
)


def test_router_branches_and_skips_inactive_path():
    w = Workflow.model_validate(ROUTED)
    e = engine({"lead": lambda: "L", "other": lambda: "O"})
    res = e.run(w, {"q": "find prospects"})
    assert (
        res.outputs == {"who": "L"}
        and res.nodes["other_t"].status == "skipped"
        and res.nodes["out2"].status == "skipped"
    )
    assert res.nodes["r"].output["via"] == "rule"
    assert e.run(w, {"q": "hello"}).outputs == {"who2": "O"}  # default route
    assert e.run(w, {"q": "other"}).nodes["r"].output["via"] == "exact"


def test_router_llm_fallback_and_bad_llm_answer_uses_default():
    raw = json.loads(json.dumps(ROUTED))
    raw["nodes"][1]["use_llm"] = True
    w = Workflow.model_validate(raw)
    tools = {"lead": lambda: "L", "other": lambda: "O"}
    assert engine(tools, lambda m, p: '{"route": "lead"}').run(w, {"q": "zzz"}).outputs == {"who": "L"}
    assert engine(tools, lambda m, p: "not json").run(w, {"q": "zzz"}).outputs == {"who2": "O"}


def test_retries_and_error_policies():
    attempts = []

    def flaky():
        attempts.append(1)
        if len(attempts) < 3:
            raise RuntimeError("transient")
        return "ok"

    def build(on_error="fail", retries=2):
        return Workflow.model_validate(
            wf(
                [
                    IN,
                    {"id": "t", "type": "tool", "tool": "f", "retries": retries, "on_error": on_error},
                    {"id": "out", "type": "output", "fields": {"v": "{{t.result}}"}},
                ],
                [{"source": "in", "target": "t"}, {"source": "t", "target": "out"}],
            )
        )

    res = engine({"f": flaky}).run(build(), {"q": "x"})
    assert res.status == "succeeded" and res.nodes["t"].attempts == 3
    always = engine({"f": lambda: 1 / 0})
    failed = always.run(build(), {"q": "x"})
    assert failed.status == "failed" and failed.nodes["out"].status == "skipped" and "ZeroDivisionError" in failed.error
    soft = always.run(build(on_error="continue", retries=0), {"q": "x"})
    assert soft.status == "succeeded" and soft.nodes["t"].status == "failed" and soft.nodes["out"].status == "skipped"


def test_llm_node_json_output_records_model():
    w = Workflow.model_validate(
        wf(
            [
                IN,
                {
                    "id": "l",
                    "type": "llm",
                    "prompt": "Q: {{in.q}}",
                    "json_output": True,
                    "model": {"complexity": "complex"},
                },
                {"id": "out", "type": "output", "fields": {"j": "{{l.json.answer}}"}},
            ],
            [{"source": "in", "target": "l"}, {"source": "l", "target": "out"}],
        )
    )
    res = engine(reply=lambda m, p: '```json\n{"answer": 42}\n```').run(w, {"q": "x"})
    assert res.outputs == {"j": 42} and res.nodes["l"].model == "p:big"


# ---------------------------------------------------------------- orchestrator + lead agent
@pytest.fixture()
def orch(tmp_path):
    agent = AirBrainAgent(str(tmp_path), icp=ICP(target_industries=["solar"]), store=Store(":memory:"))
    tools = default_tools(agent)
    tools["lead.run"] = lambda goal, max_iterations=40: {"summary": f"ran: {goal}"}  # no live Claude in tests
    gw = ModelGateway(
        [
            provider(
                "p",
                lambda m, p: (
                    '{"route": "general", "confidence": 0.6, "reasoning": "chat"}' if "Workflows:" in p else "an answer"
                ),
            )
        ],
        CATALOG,
    )
    return Orchestrator(WorkflowEngine(tools, gw)), agent


def test_orchestrator_routing_sources(orch):
    o, _ = orch
    assert o.route(Task(task_type="lead_report", payload="x")).source == "explicit"
    with pytest.raises(ValueError, match="unknown task_type"):
        o.route(Task(task_type="nope", payload="x"))
    d = o.route(Task(payload="find 10 solar installers in Texas", priority="low"))
    assert (d.route, d.source) == ("lead_research", "rules") and d.model.cost == "optimize_cost"
    assert o.route(Task(payload="show me the weekly report")).route == "lead_report"
    llm = o.route(Task(payload="what is the capital of France"))
    assert (llm.route, llm.source) == ("general", "llm")


def test_end_to_end_lead_workflows(orch):
    o, agent = orch
    res = o.handle(Task(payload="find solar installers in Tampa"))
    assert res.decision.route == "lead_research" and res.run.status == "succeeded"
    assert res.run.outputs["summary"] == "ran: find solar installers in Tampa"
    assert res.run.nodes["brief"].status == "succeeded"  # llm brief via gateway
    from air_brain_agent.schema import Contact, Evidence, Lead

    agent.save_lead(
        Lead(
            company="Acme",
            website="https://acme.com",
            industry="solar",
            contacts=[Contact(email="a@acme.com")],
            evidence=[Evidence(url="https://acme.com", quote="solar")],
        )
    )
    fb = o.handle(Task(task_type="lead_feedback", payload="", inputs={"lead_key": "acme.com", "verdict": "accepted"}))
    assert fb.run.status == "succeeded" and fb.run.outputs["result"]["ok"] is True
    assert agent.store.get_lead("acme.com").status.value == "accepted"
    assert "Acme" in o.handle(Task(task_type="lead_report", payload="")).run.outputs["report"]


def test_orchestrator_rejects_workflows_with_unknown_tools():
    w = Workflow.model_validate(
        wf(
            [IN, {"id": "t", "type": "tool", "tool": "missing"}, {"id": "out", "type": "output", "fields": {}}],
            [{"source": "in", "target": "t"}, {"source": "t", "target": "out"}],
            name="bad",
        )
    )
    with pytest.raises(ValueError, match="unknown tool"):
        Orchestrator(WorkflowEngine({}, None), {"bad": w})
