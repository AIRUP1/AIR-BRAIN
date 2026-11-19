"""Multi-model gateway: pick a model from a catalog for a request, call it, fall back down the ranking on failure."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Literal, Optional, Protocol

from pydantic import BaseModel, ConfigDict, Field


class ModelSpec(BaseModel):
    provider: str
    model: str
    tier: int = Field(ge=1, le=3)  # 1 = small/fast/cheap, 2 = balanced, 3 = most capable


class ModelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    complexity: Literal["simple", "moderate", "complex"] = "moderate"
    latency: Literal["realtime", "fast", "standard", "batch"] = "standard"
    cost: Literal["optimize_cost", "balanced", "optimize_quality"] = "balanced"
    provider: Optional[str] = None  # soft preference: tried first if it has a usable model


class Attempt(BaseModel):
    provider: str
    model: str
    ok: bool
    error: Optional[str] = None


class Completion(BaseModel):
    text: str
    provider: str
    model: str
    attempts: List[Attempt] = Field(default_factory=list)


class GatewayError(RuntimeError):
    def __init__(self, message: str, attempts: List[Attempt]) -> None:
        super().__init__(message)
        self.attempts = attempts


class Provider(Protocol):
    name: str

    def complete(self, model: str, system: Optional[str], prompt: str, max_tokens: int) -> str: ...


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, client: Any = None) -> None:
        self._client = client

    def complete(self, model: str, system: Optional[str], prompt: str, max_tokens: int) -> str:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        kwargs: Dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        msg = self._client.messages.create(**kwargs)
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


class CallableProvider:
    """Wrap any function(model, system, prompt, max_tokens) -> str as a provider (OpenAI, Ollama, test doubles...)."""

    def __init__(self, name: str, fn: Callable[[str, Optional[str], str, int], str]) -> None:
        self.name, self._fn = name, fn

    def complete(self, model: str, system: Optional[str], prompt: str, max_tokens: int) -> str:
        return self._fn(model, system, prompt, max_tokens)


DEFAULT_CATALOG = [
    ModelSpec(provider="anthropic", model="claude-haiku-5-5", tier=1),
    ModelSpec(provider="anthropic", model="claude-sonnet-5-5", tier=2),
    ModelSpec(provider="anthropic", model="claude-opus-5-5", tier=3),
]
_BASE_TIER = {"simple": 1, "moderate": 2, "complex": 3}
_LATENCY_CAP = {"realtime": 1, "fast": 2, "standard": 3, "batch": 3}


class ModelGateway:
    def __init__(
        self,
        providers: Optional[List[Provider]] = None,
        catalog: Optional[List[ModelSpec]] = None,
        failure_threshold: int = 3,
        cooldown_s: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.providers: Dict[str, Provider] = {p.name: p for p in (providers or [AnthropicProvider()])}
        self.catalog = [s for s in (catalog or DEFAULT_CATALOG) if s.provider in self.providers]
        self.failure_threshold, self.cooldown_s, self._clock = failure_threshold, cooldown_s, clock
        self._failures: Dict[str, int] = {}
        self._tripped_at: Dict[str, float] = {}

    # -- selection ----------------------------------------------------------------
    def target_tier(self, req: ModelRequest) -> int:
        tier = _BASE_TIER[req.complexity] + {"optimize_cost": -1, "balanced": 0, "optimize_quality": 1}[req.cost]
        return max(1, min(tier, _LATENCY_CAP[req.latency], 3))  # latency is a hard ceiling; cost/quality only nudge

    def _available(self, spec: ModelSpec) -> bool:
        key = f"{spec.provider}:{spec.model}"
        tripped = self._tripped_at.get(key)
        if tripped is None:
            return True
        if self._clock() - tripped >= self.cooldown_s:  # half-open: allow one more try after cooldown
            del self._tripped_at[key]
            self._failures[key] = self.failure_threshold - 1
            return True
        return False

    def rank(self, req: ModelRequest) -> List[ModelSpec]:
        """Closest tier to the target first; ties go to the cheaper tier (or the stronger one for optimize_quality)."""
        target = self.target_tier(req)
        sign = -1 if req.cost == "optimize_quality" else 1
        specs = [s for s in self.catalog if self._available(s)]
        specs.sort(
            key=lambda s: (req.provider is not None and s.provider != req.provider, abs(s.tier - target), sign * s.tier)
        )
        return specs

    # -- execution ----------------------------------------------------------------
    def complete(
        self, req: ModelRequest, prompt: str, system: Optional[str] = None, max_tokens: int = 1024
    ) -> Completion:
        attempts: List[Attempt] = []
        for spec in self.rank(req):
            key = f"{spec.provider}:{spec.model}"
            try:
                text = self.providers[spec.provider].complete(spec.model, system, prompt, max_tokens)
            except Exception as exc:  # any provider failure triggers fallback
                attempts.append(
                    Attempt(provider=spec.provider, model=spec.model, ok=False, error=f"{type(exc).__name__}: {exc}")
                )
                self._failures[key] = self._failures.get(key, 0) + 1
                if self._failures[key] >= self.failure_threshold:
                    self._tripped_at[key] = self._clock()
                continue
            self._failures[key] = 0
            attempts.append(Attempt(provider=spec.provider, model=spec.model, ok=True))
            return Completion(text=text, provider=spec.provider, model=spec.model, attempts=attempts)
        raise GatewayError("all models failed or are unavailable", attempts)
