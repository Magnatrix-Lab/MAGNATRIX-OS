"""Model Router / Gateway — Intelligent LLM backend selection and load balancing.

Modul ini menyediakan:
- ModelRegistry dengan capability scoring, cost, latency tracking
- RouterEngine yang memilih model terbaik berdasarkan query characteristics
- LoadBalancer untuk distribute traffic across replicas
- FallbackManager untuk failover antar provider
- CostTracker untuk budget monitoring per API key / user
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class ModelCapability(Enum):
    REASONING = auto()
    CODING = auto()
    WRITING = auto()
    MATH = auto()
    VISION = auto()
    MULTILINGUAL = auto()
    LONG_CONTEXT = auto()
    FAST = auto()


class RoutingStrategy(Enum):
    CAPABILITY_MATCH = auto()
    COST_MIN = auto()
    LATENCY_MIN = auto()
    QUALITY_MAX = auto()
    BALANCED = auto()
    CUSTOM = auto()


@dataclass
class ModelEndpoint:
    """Single LLM endpoint / replica."""
    endpoint_id: str
    name: str
    provider: str
    model_id: str
    capabilities: Set[ModelCapability]
    cost_per_1k_input: float
    cost_per_1k_output: float
    avg_latency_ms: float = 500.0
    success_rate: float = 0.99
    max_tokens: int = 4096
    load: float = 0.0  # 0-1 current load
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def score_for(self, query_caps: Set[ModelCapability], strategy: RoutingStrategy) -> float:
        if not self.enabled or self.load >= 1.0:
            return -1.0
        cap_match = len(self.capabilities & query_caps) / max(len(query_caps), 1)
        if strategy == RoutingStrategy.CAPABILITY_MATCH:
            return cap_match * 100 - self.load * 10
        elif strategy == RoutingStrategy.COST_MIN:
            return (1.0 / max(self.cost_per_1k_input + self.cost_per_1k_output, 0.001)) * 10 + cap_match * 5
        elif strategy == RoutingStrategy.LATENCY_MIN:
            return (1.0 / max(self.avg_latency_ms, 1.0)) * 1000 + cap_match * 5
        elif strategy == RoutingStrategy.QUALITY_MAX:
            return cap_match * 100 + self.success_rate * 10 - self.load * 5
        elif strategy == RoutingStrategy.BALANCED:
            return (cap_match * 30 + (1.0 / max(self.cost_per_1k_input, 0.001)) * 5 +
                    (1.0 / max(self.avg_latency_ms, 1.0)) * 200 + self.success_rate * 20 - self.load * 15)
        return cap_match * 50


@dataclass
class QueryProfile:
    """Characteristics of a query for routing."""
    query_id: str
    text: str
    required_caps: Set[ModelCapability] = field(default_factory=set)
    max_cost: float = 999.0
    max_latency_ms: float = 99999.0
    min_quality: float = 0.0
    preferred_provider: Optional[str] = None
    estimated_tokens: int = 0

    def infer_caps(self) -> Set[ModelCapability]:
        caps = set()
        t = self.text.lower()
        if any(k in t for k in ["code", "python", "function", "class", "def ", "implement"]):
            caps.add(ModelCapability.CODING)
        if any(k in t for k in ["math", "calculate", "solve", "equation", "number"]):
            caps.add(ModelCapability.MATH)
        if any(k in t for k in ["write", "essay", "article", "story", "draft"]):
            caps.add(ModelCapability.WRITING)
        if any(k in t for k in ["reason", "explain", "why", "how does", "think step"]):
            caps.add(ModelCapability.REASONING)
        if len(self.text) > 2000:
            caps.add(ModelCapability.LONG_CONTEXT)
        if not caps:
            caps.add(ModelCapability.FAST)
        return caps


@dataclass
class RoutingDecision:
    """Result of routing a query."""
    query_id: str
    endpoint_id: str
    model_name: str
    strategy: RoutingStrategy
    score: float
    estimated_cost: float
    estimated_latency: float
    reason: str = ""


class ModelRegistry:
    """Register and manage all available LLM endpoints."""

    def __init__(self):
        self._endpoints: Dict[str, ModelEndpoint] = {}
        self._by_provider: Dict[str, List[str]] = {}
        self._by_capability: Dict[ModelCapability, List[str]] = {}

    def register(self, ep: ModelEndpoint) -> None:
        self._endpoints[ep.endpoint_id] = ep
        self._by_provider.setdefault(ep.provider, []).append(ep.endpoint_id)
        for cap in ep.capabilities:
            self._by_capability.setdefault(cap, []).append(ep.endpoint_id)

    def unregister(self, endpoint_id: str) -> None:
        ep = self._endpoints.pop(endpoint_id, None)
        if ep:
            self._by_provider.get(ep.provider, []).remove(endpoint_id)
            for cap in ep.capabilities:
                self._by_capability.get(cap, []).remove(endpoint_id)

    def get(self, endpoint_id: str) -> Optional[ModelEndpoint]:
        return self._endpoints.get(endpoint_id)

    def list_all(self) -> List[ModelEndpoint]:
        return list(self._endpoints.values())

    def update_health(self, endpoint_id: str, latency: float, success: bool) -> None:
        ep = self._endpoints.get(endpoint_id)
        if ep:
            ep.avg_latency_ms = ep.avg_latency_ms * 0.8 + latency * 0.2
            ep.success_rate = ep.success_rate * 0.95 + (1.0 if success else 0.0) * 0.05
            if not success:
                ep.load = min(1.0, ep.load + 0.1)
            else:
                ep.load = max(0.0, ep.load - 0.05)

    def find_by_capability(self, cap: ModelCapability) -> List[ModelEndpoint]:
        return [self._endpoints[eid] for eid in self._by_capability.get(cap, []) if eid in self._endpoints]


class RouterEngine:
    """Route queries to the best model endpoint."""

    def __init__(self, registry: ModelRegistry, default_strategy: RoutingStrategy = RoutingStrategy.BALANCED):
        self.registry = registry
        self.default_strategy = default_strategy
        self._history: List[RoutingDecision] = []
        self._custom_scorer: Optional[Callable[[ModelEndpoint, QueryProfile], float]] = None

    def set_custom_scorer(self, scorer: Callable[[ModelEndpoint, QueryProfile], float]) -> None:
        self._custom_scorer = scorer

    def route(self, query: QueryProfile, strategy: Optional[RoutingStrategy] = None) -> Optional[RoutingDecision]:
        strategy = strategy or self.default_strategy
        if not query.required_caps:
            query.required_caps = query.infer_caps()

        candidates = []
        for ep in self.registry.list_all():
            if not ep.enabled or ep.load >= 1.0:
                continue
            if query.preferred_provider and ep.provider != query.preferred_provider:
                continue
            if ep.avg_latency_ms > query.max_latency_ms:
                continue
            score = self._score(ep, query, strategy)
            if score > 0:
                candidates.append((score, ep))

        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0], reverse=True)
        best = candidates[0][1]
        est_cost = (query.estimated_tokens / 1000) * (best.cost_per_1k_input + best.cost_per_1k_output * 0.5)
        decision = RoutingDecision(
            query_id=query.query_id,
            endpoint_id=best.endpoint_id,
            model_name=best.name,
            strategy=strategy,
            score=round(candidates[0][0], 2),
            estimated_cost=round(est_cost, 4),
            estimated_latency=round(best.avg_latency_ms, 1),
            reason=f"Best match for {', '.join(c.name for c in query.required_caps)}"
        )
        self._history.append(decision)
        return decision

    def _score(self, ep: ModelEndpoint, query: QueryProfile, strategy: RoutingStrategy) -> float:
        if self._custom_scorer and strategy == RoutingStrategy.CUSTOM:
            return self._custom_scorer(ep, query)
        return ep.score_for(query.required_caps, strategy)

    def get_history(self) -> List[RoutingDecision]:
        return self._history

    def get_stats(self) -> Dict[str, Any]:
        if not self._history:
            return {}
        return {
            "total_routed": len(self._history),
            "strategy_distribution": {s.name: sum(1 for d in self._history if d.strategy == s) for s in RoutingStrategy},
            "avg_estimated_cost": sum(d.estimated_cost for d in self._history) / len(self._history),
            "avg_estimated_latency": sum(d.estimated_latency for d in self._history) / len(self._history),
        }


class LoadBalancer:
    """Distribute queries across replicas with load-aware selection."""

    def __init__(self, registry: ModelRegistry):
        self.registry = registry
        self._round_robin: Dict[str, int] = {}

    def select(self, provider: str, model_id: str) -> Optional[ModelEndpoint]:
        replicas = [ep for ep in self.registry.list_all()
                    if ep.provider == provider and ep.model_id == model_id and ep.enabled and ep.load < 1.0]
        if not replicas:
            return None
        # Pick least loaded
        return min(replicas, key=lambda ep: ep.load)

    def round_robin(self, provider: str, model_id: str) -> Optional[ModelEndpoint]:
        replicas = [ep for ep in self.registry.list_all()
                    if ep.provider == provider and ep.model_id == model_id and ep.enabled and ep.load < 1.0]
        if not replicas:
            return None
        key = f"{provider}:{model_id}"
        idx = self._round_robin.get(key, 0) % len(replicas)
        self._round_robin[key] = idx + 1
        return replicas[idx]


class FallbackManager:
    """Failover to backup endpoints on failure."""

    def __init__(self, registry: ModelRegistry, router: RouterEngine):
        self.registry = registry
        self.router = router
        self._fallback_chains: Dict[str, List[str]] = {}  # endpoint_id -> fallback chain

    def set_fallback_chain(self, endpoint_id: str, chain: List[str]) -> None:
        self._fallback_chains[endpoint_id] = chain

    def execute_with_fallback(self, query: QueryProfile,
                               execute_fn: Callable[[str], Tuple[bool, Any, float]]) -> Tuple[bool, Any, str]:
        decision = self.router.route(query)
        if not decision:
            return False, None, "No available endpoint"
        tried = [decision.endpoint_id]
        current = decision.endpoint_id
        while current:
            success, result, latency = execute_fn(current)
            self.registry.update_health(current, latency, success)
            if success:
                return True, result, current
            # Try fallback
            chain = self._fallback_chains.get(current, [])
            current = None
            for fid in chain:
                if fid not in tried and fid in self.registry._endpoints:
                    tried.append(fid)
                    current = fid
                    break
        return False, None, f"All fallbacks exhausted: {tried}"


class CostTracker:
    """Track API usage costs per key/user."""

    def __init__(self, budget_limit: float = 1000.0):
        self.budget_limit = budget_limit
        self._usage: Dict[str, Dict[str, float]] = {}  # key -> {input_tokens, output_tokens, cost}

    def record(self, api_key: str, input_tokens: int, output_tokens: int, cost_per_1k_in: float, cost_per_1k_out: float) -> None:
        cost = (input_tokens / 1000) * cost_per_1k_in + (output_tokens / 1000) * cost_per_1k_out
        u = self._usage.setdefault(api_key, {"input_tokens": 0, "output_tokens": 0, "cost": 0.0})
        u["input_tokens"] += input_tokens
        u["output_tokens"] += output_tokens
        u["cost"] += cost

    def get_usage(self, api_key: str) -> Dict[str, float]:
        return self._usage.get(api_key, {"input_tokens": 0, "output_tokens": 0, "cost": 0.0})

    def is_over_budget(self, api_key: str) -> bool:
        return self._usage.get(api_key, {}).get("cost", 0.0) > self.budget_limit

    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        return dict(self._usage)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("MODEL ROUTER / GATEWAY DEMO")
    print("=" * 70)

    # Setup registry
    registry = ModelRegistry()
    registry.register(ModelEndpoint(
        "ep-gpt4", "GPT-4", "openai", "gpt-4",
        {ModelCapability.REASONING, ModelCapability.CODING, ModelCapability.WRITING, ModelCapability.LONG_CONTEXT},
        cost_per_1k_input=0.03, cost_per_1k_output=0.06, avg_latency_ms=800, max_tokens=8192
    ))
    registry.register(ModelEndpoint(
        "ep-gpt35", "GPT-3.5", "openai", "gpt-3.5-turbo",
        {ModelCapability.FAST, ModelCapability.WRITING, ModelCapability.CODING},
        cost_per_1k_input=0.0005, cost_per_1k_output=0.0015, avg_latency_ms=200, max_tokens=4096
    ))
    registry.register(ModelEndpoint(
        "ep-claude", "Claude 3.5", "anthropic", "claude-3-5-sonnet",
        {ModelCapability.REASONING, ModelCapability.WRITING, ModelCapability.LONG_CONTEXT, ModelCapability.VISION},
        cost_per_1k_input=0.003, cost_per_1k_output=0.015, avg_latency_ms=600, max_tokens=200000
    ))
    registry.register(ModelEndpoint(
        "ep-local", "Local LLaMA", "local", "llama-3-8b",
        {ModelCapability.FAST, ModelCapability.CODING, ModelCapability.MATH},
        cost_per_1k_input=0.0, cost_per_1k_output=0.0, avg_latency_ms=150, max_tokens=8192
    ))
    registry.register(ModelEndpoint(
        "ep-gemini", "Gemini Pro", "google", "gemini-pro",
        {ModelCapability.REASONING, ModelCapability.VISION, ModelCapability.MULTILINGUAL, ModelCapability.FAST},
        cost_per_1k_input=0.0005, cost_per_1k_output=0.0015, avg_latency_ms=300, max_tokens=32000
    ))
    print(f"\n[Registry] {len(registry.list_all())} endpoints registered")

    # Router
    router = RouterEngine(registry, RoutingStrategy.BALANCED)

    # Test queries
    queries = [
        QueryProfile(str(uuid.uuid4())[:8], "Write a Python function to sort a list", estimated_tokens=500),
        QueryProfile(str(uuid.uuid4())[:8], "Explain quantum computing in detail with math", estimated_tokens=2000),
        QueryProfile(str(uuid.uuid4())[:8], "Summarize this 10-page document", estimated_tokens=5000),
        QueryProfile(str(uuid.uuid4())[:8], "2+2=?", estimated_tokens=50),
        QueryProfile(str(uuid.uuid4())[:8], "Debug this C++ memory leak", estimated_tokens=1000),
    ]

    print("\n[2] Routing Queries")
    for q in queries:
        caps = q.infer_caps()
        q.required_caps = caps
        decision = router.route(q)
        if decision:
            print(f"  [{q.query_id}] {q.text[:40]}... → {decision.model_name} (score={decision.score}, est_cost=${decision.estimated_cost}, latency={decision.estimated_latency}ms)")
        else:
            print(f"  [{q.query_id}] {q.text[:40]}... → NO ROUTE")

    # Strategy comparison
    print("\n[3] Strategy Comparison")
    test_q = QueryProfile(str(uuid.uuid4())[:8], "Solve this complex optimization problem", required_caps={ModelCapability.REASONING, ModelCapability.MATH}, estimated_tokens=1500)
    for strat in [RoutingStrategy.CAPABILITY_MATCH, RoutingStrategy.COST_MIN, RoutingStrategy.LATENCY_MIN, RoutingStrategy.QUALITY_MAX, RoutingStrategy.BALANCED]:
        d = router.route(test_q, strat)
        print(f"  {strat.name}: {d.model_name if d else 'NONE'} (score={d.score if d else 0})")

    # Load balancer
    print("\n[4] Load Balancer")
    lb = LoadBalancer(registry)
    for _ in range(3):
        ep = lb.select("openai", "gpt-4")
        print(f"  Selected: {ep.name if ep else 'None'} (load={ep.load if ep else 'N/A'})")
        if ep:
            ep.load += 0.3

    # Fallback
    print("\n[5] Fallback Manager")
    fm = FallbackManager(registry, router)
    fm.set_fallback_chain("ep-gpt4", ["ep-claude", "ep-gemini", "ep-gpt35"])
    def fake_execute(ep_id):
        return ep_id != "ep-gpt4", {"result": "ok"}, 500.0
    ok, result, used = fm.execute_with_fallback(test_q, fake_execute)
    print(f"  Success: {ok}, Used: {used}, Result: {result}")

    # Cost tracker
    print("\n[6] Cost Tracker")
    ct = CostTracker(budget_limit=10.0)
    ct.record("key-1", 5000, 2000, 0.03, 0.06)
    ct.record("key-1", 3000, 1500, 0.03, 0.06)
    ct.record("key-2", 10000, 5000, 0.0005, 0.0015)
    print(f"  key-1 usage: {ct.get_usage('key-1')}")
    print(f"  key-2 usage: {ct.get_usage('key-2')}")
    print(f"  key-1 over budget? {ct.is_over_budget('key-1')}")

    # Stats
    print("\n[7] Router Stats")
    print(f"  {router.get_stats()}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
