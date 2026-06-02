"""Semantic Router — Intent classification and query routing based on semantic matching.

Modul ini menyediakan:
- IntentClassifier untuk classify user intent dari text
- SemanticRouter untuk route queries ke handlers berdasarkan intent
- EmbeddingEngine untuk text embedding (simulated)
- RouteRegistry untuk register handlers dengan patterns
- ConfidenceScorer untuk scoring confidence routing
"""

from __future__ import annotations

import json
import time
import uuid
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class IntentType(Enum):
    GREETING = "greeting"
    QUESTION = "question"
    COMMAND = "command"
    CODE = "code"
    ANALYSIS = "analysis"
    CREATIVE = "creative"
    FACTUAL = "factual"
    CLARIFICATION = "clarification"
    UNKNOWN = "unknown"


@dataclass
class Intent:
    """Classified intent."""
    intent_type: IntentType
    confidence: float = 0.0
    entities: Dict[str, str] = field(default_factory=dict)
    keywords: List[str] = field(default_factory=list)


@dataclass
class Route:
    """Routing destination."""
    route_id: str
    name: str
    intent_types: Set[IntentType]
    handler: Optional[Callable[..., Any]] = None
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingDecision:
    """Result of routing."""
    query: str
    intent: Intent
    route_id: Optional[str]
    route_name: Optional[str]
    confidence: float
    latency_ms: float


class EmbeddingEngine:
    """Simulated text embedding for semantic matching."""

    def __init__(self, dim: int = 128):
        self.dim = dim

    def embed(self, text: str) -> List[float]:
        # Deterministic hash-based embedding
        import hashlib
        h = hashlib.sha256(text.encode()).hexdigest()
        # Extend hash if needed for dimension
        while len(h) < self.dim * 2:
            h += hashlib.sha256(h.encode()).hexdigest()
        vec = []
        for i in range(self.dim):
            val = int(h[i * 2:i * 2 + 2], 16) / 255.0
            vec.append(val)
        return vec

    def similarity(self, a: str, b: str) -> float:
        va = self.embed(a)
        vb = self.embed(b)
        dot = sum(x * y for x, y in zip(va, vb))
        norm_a = sum(x * x for x in va) ** 0.5
        norm_b = sum(x * x for x in vb) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


class IntentClassifier:
    """Classify user intent from text."""

    # Intent patterns (keywords -> intent)
    INTENT_PATTERNS = {
        IntentType.GREETING: ["hello", "hi", "hey", "greetings", "morning", "afternoon", "evening"],
        IntentType.QUESTION: ["what", "how", "why", "when", "where", "who", "which", "can you", "do you know"],
        IntentType.COMMAND: ["create", "build", "make", "generate", "write", "do", "run", "execute", "show"],
        IntentType.CODE: ["code", "function", "script", "program", "debug", "python", "javascript", "compile", "error"],
        IntentType.ANALYSIS: ["analyze", "compare", "evaluate", "assess", "review", "study", "examine"],
        IntentType.CREATIVE: ["story", "poem", "creative", "imagine", "design", "art", "write a story"],
        IntentType.FACTUAL: ["is", "are", "was", "were", "does", "did", "true", "false", "fact"],
    }

    def __init__(self, embedding_engine: Optional[EmbeddingEngine] = None):
        self.embedder = embedding_engine or EmbeddingEngine()

    def classify(self, text: str) -> Intent:
        text_lower = text.lower()
        scores = {}
        entities = {}

        # Pattern matching
        for intent, keywords in self.INTENT_PATTERNS.items():
            score = 0.0
            for kw in keywords:
                if kw in text_lower:
                    score += 1.0
            scores[intent] = score

        # Entity extraction (simple regex)
        # Extract quoted strings as entities
        quotes = re.findall(r'"([^"]*)"', text)
        if quotes:
            entities["quoted"] = quotes[0]
        # Extract code blocks
        code_blocks = re.findall(r'```(\w+)?', text)
        if code_blocks:
            entities["language"] = code_blocks[0] if code_blocks[0] else "code"

        # Find best intent
        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]
        total_score = sum(scores.values())
        confidence = best_score / max(total_score, 1) if total_score > 0 else 0.0

        if best_score == 0:
            best_intent = IntentType.UNKNOWN
            confidence = 0.0

        return Intent(
            intent_type=best_intent,
            confidence=round(confidence, 3),
            entities=entities,
            keywords=[k for k in text_lower.split() if len(k) > 3],
        )

    def classify_batch(self, texts: List[str]) -> List[Intent]:
        return [self.classify(t) for t in texts]


class RouteRegistry:
    """Register and manage routes."""

    def __init__(self):
        self._routes: Dict[str, Route] = {}
        self._by_intent: Dict[IntentType, List[str]] = {}

    def register(self, route: Route) -> None:
        self._routes[route.route_id] = route
        for intent in route.intent_types:
            self._by_intent.setdefault(intent, []).append(route.route_id)

    def get(self, route_id: str) -> Optional[Route]:
        return self._routes.get(route_id)

    def find_by_intent(self, intent: IntentType) -> List[Route]:
        return [self._routes[rid] for rid in self._by_intent.get(intent, []) if rid in self._routes]

    def list_all(self) -> List[Route]:
        return list(self._routes.values())

    def get_stats(self) -> Dict[str, Any]:
        return {
            "routes": len(self._routes),
            "intents": len(self._by_intent),
        }


class SemanticRouter:
    """Route queries to handlers based on intent."""

    def __init__(self, classifier: Optional[IntentClassifier] = None, registry: Optional[RouteRegistry] = None):
        self.classifier = classifier or IntentClassifier()
        self.registry = registry or RouteRegistry()
        self._history: List[RoutingDecision] = []
        self._default_handler: Optional[Callable[..., Any]] = None

    def set_default_handler(self, handler: Callable[..., Any]) -> None:
        self._default_handler = handler

    def route(self, query: str) -> RoutingDecision:
        start = time.time()
        intent = self.classifier.classify(query)
        routes = self.registry.find_by_intent(intent.intent_type)

        if not routes:
            # Fallback to semantic similarity
            routes = self.registry.list_all()
            if routes:
                best_route = self._find_by_similarity(query, routes)
            else:
                best_route = None
        else:
            best_route = max(routes, key=lambda r: r.priority)

        decision = RoutingDecision(
            query=query[:100],
            intent=intent,
            route_id=best_route.route_id if best_route else None,
            route_name=best_route.name if best_route else None,
            confidence=intent.confidence,
            latency_ms=round((time.time() - start) * 1000, 2),
        )
        self._history.append(decision)
        return decision

    def _find_by_similarity(self, query: str, routes: List[Route]) -> Optional[Route]:
        best = None
        best_score = 0.0
        for route in routes:
            score = self.classifier.embedder.similarity(query, route.name)
            if score > best_score:
                best_score = score
                best = route
        return best

    def execute(self, query: str, *args, **kwargs) -> Any:
        decision = self.route(query)
        if decision.route_id:
            route = self.registry.get(decision.route_id)
            if route and route.handler:
                return route.handler(query, decision, *args, **kwargs)
        if self._default_handler:
            return self._default_handler(query, decision)
        return None

    def get_history(self) -> List[RoutingDecision]:
        return self._history

    def get_stats(self) -> Dict[str, Any]:
        if not self._history:
            return {}
        total = len(self._history)
        return {
            "total_routed": total,
            "avg_confidence": sum(d.confidence for d in self._history) / total,
            "avg_latency_ms": sum(d.latency_ms for d in self._history) / total,
            "intent_distribution": {it.name: sum(1 for d in self._history if d.intent.intent_type == it) for it in IntentType},
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "stats": self.get_stats(),
                "recent": [
                    {
                        "query": d.query,
                        "intent": d.intent.intent_type.name,
                        "route": d.route_name,
                        "confidence": d.confidence,
                    }
                    for d in self._history[-10:]
                ],
            }, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("SEMANTIC ROUTER DEMO")
    print("=" * 70)

    # 1. Setup
    print("\n[1] Setup Routes")
    router = SemanticRouter()
    router.registry.register(Route("r1", "General QA", {IntentType.QUESTION, IntentType.FACTUAL}, priority=1))
    router.registry.register(Route("r2", "Code Assistant", {IntentType.CODE, IntentType.COMMAND}, priority=2))
    router.registry.register(Route("r3", "Creative Writer", {IntentType.CREATIVE}, priority=3))
    router.registry.register(Route("r4", "Analyzer", {IntentType.ANALYSIS}, priority=2))
    router.registry.register(Route("r5", "Greeter", {IntentType.GREETING}, priority=5))
    print(f"  Routes: {router.registry.get_stats()}")

    # 2. Test queries
    print("\n[2] Routing Queries")
    queries = [
        "Hello there!",
        "How does Python handle memory?",
        "Write a function to sort a list",
        "Tell me a story about a dragon",
        "Analyze this data set",
        "What is the capital of France?",
        "Create a React component",
    ]
    for q in queries:
        decision = router.route(q)
        print(f"  '{q[:40]}' -> {decision.intent.intent_type.name} (conf={decision.confidence:.2f}) -> {decision.route_name}")

    # 3. Batch classify
    print("\n[3] Batch Classification")
    intents = router.classifier.classify_batch(["Hello", "How are you?", "Write code", "Compare A and B"])
    for i, intent in enumerate(intents):
        print(f"  Intent {i+1}: {intent.intent_type.name} (conf={intent.confidence:.2f})")

    # 4. Semantic similarity
    print("\n[4] Semantic Similarity")
    sim = router.classifier.embedder.similarity("machine learning", "deep learning")
    print(f"  'machine learning' <-> 'deep learning': {sim:.4f}")
    sim2 = router.classifier.embedder.similarity("hello world", "goodbye")
    print(f"  'hello world' <-> 'goodbye': {sim2:.4f}")

    # 5. Execute with handler
    print("\n[5] Execute with Handler")
    def code_handler(query, decision):
        return f"[CODE] Handling: {query[:30]}..."
    def qa_handler(query, decision):
        return f"[QA] Answering: {query[:30]}..."
    router.registry.get("r2").handler = code_handler
    router.registry.get("r1").handler = qa_handler
    for q in ["Write a Python function", "What is AI?"]:
        result = router.execute(q)
        print(f"  '{q[:30]}...' -> {result}")

    # 6. Default handler
    print("\n[6] Default Handler")
    router.set_default_handler(lambda q, d: f"[DEFAULT] I got: {q[:30]}")
    result = router.execute("Random unknown query")
    print(f"  Result: {result}")

    # 7. Stats
    print(f"\n[7] Router Stats")
    print(f"  {router.get_stats()}")

    # 8. Export
    print("\n[8] Export")
    router.export("/tmp/routing.json")
    print("  Exported to /tmp/routing.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
