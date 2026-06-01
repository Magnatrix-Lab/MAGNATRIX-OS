"""Cross-Model Ensemble — Multiple model outputs, voting, confidence scoring.

Modul ini menyediakan:
- ModelPool untuk manage multiple model instances
- EnsembleVoter dengan multiple strategies (majority, weighted, confidence)
- OutputComparator untuk semantic similarity scoring
- ConfidenceScorer per model
- Consensus mechanism dengan tie-breaking
"""

from __future__ import annotations

import json
import time
import uuid
import statistics
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class VoteStrategy(Enum):
    MAJORITY = auto()
    WEIGHTED = auto()
    CONFIDENCE = auto()
    RANKED = auto()
    AVERAGE = auto()


class ModelCapability(Enum):
    REASONING = "reasoning"
    CODING = "coding"
    CREATIVITY = "creativity"
    FACTUAL = "factual"
    CONVERSATION = "conversation"


@dataclass
class ModelProfile:
    """Profile untuk sebuah model dalam ensemble."""
    model_id: str
    name: str
    weight: float = 1.0
    confidence: float = 0.8
    capabilities: Set[ModelCapability] = field(default_factory=set)
    latency_ms: float = 100.0
    cost_per_token: float = 0.001
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelOutput:
    """Output dari sebuah model."""
    model_id: str
    content: str
    confidence: float = 0.0
    latency_ms: float = 0.0
    tokens_used: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EnsembleResult:
    """Hasil voting dari ensemble."""
    result_id: str
    winning_output: str
    winning_model_id: str
    strategy: VoteStrategy
    consensus_score: float = 0.0
    all_outputs: List[ModelOutput] = field(default_factory=list)
    vote_distribution: Dict[str, float] = field(default_factory=dict)
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "winning_output": self.winning_output[:200],
            "winning_model_id": self.winning_model_id,
            "strategy": self.strategy.name,
            "consensus_score": round(self.consensus_score, 3),
            "vote_distribution": {k: round(v, 3) for k, v in self.vote_distribution.items()},
            "duration_ms": round(self.duration_ms, 2)
        }


class SemanticComparator:
    """Compare semantic similarity antara outputs."""

    def __init__(self):
        self._cache: Dict[Tuple[str, str], float] = {}

    def _tokenize(self, text: str) -> Set[str]:
        return set(text.lower().split())

    def similarity(self, a: str, b: str) -> float:
        key = tuple(sorted([a, b]))
        if key in self._cache:
            return self._cache[key]
        sa, sb = self._tokenize(a), self._tokenize(b)
        if not sa or not sb:
            return 0.0
        jaccard = len(sa & sb) / len(sa | sb)
        # Simple n-gram overlap
        a_bigrams = set(zip(a.lower().split()[:-1], a.lower().split()[1:]))
        b_bigrams = set(zip(b.lower().split()[:-1], b.lower().split()[1:]))
        bigram_sim = len(a_bigrams & b_bigrams) / max(len(a_bigrams | b_bigrams), 1)
        score = 0.5 * jaccard + 0.5 * bigram_sim
        self._cache[key] = score
        return score

    def agreement_matrix(self, outputs: List[ModelOutput]) -> List[List[float]]:
        n = len(outputs)
        matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                matrix[i][j] = self.similarity(outputs[i].content, outputs[j].content)
        return matrix

    def cluster_outputs(self, outputs: List[ModelOutput], threshold: float = 0.7) -> List[List[ModelOutput]]:
        clusters: List[List[ModelOutput]] = []
        for out in outputs:
            placed = False
            for cluster in clusters:
                if self.similarity(out.content, cluster[0].content) >= threshold:
                    cluster.append(out)
                    placed = True
                    break
            if not placed:
                clusters.append([out])
        return clusters


class ModelPool:
    """Pool of models dalam ensemble."""

    def __init__(self):
        self._models: Dict[str, ModelProfile] = {}
        self._invoke_fns: Dict[str, Callable[[str], ModelOutput]] = {}

    def register(self, profile: ModelProfile, invoke_fn: Callable[[str], ModelOutput]) -> None:
        self._models[profile.model_id] = profile
        self._invoke_fns[profile.model_id] = invoke_fn

    def get(self, model_id: str) -> Optional[ModelProfile]:
        return self._models.get(model_id)

    def invoke(self, model_id: str, prompt: str) -> Optional[ModelOutput]:
        fn = self._invoke_fns.get(model_id)
        if not fn:
            return None
        start = time.time()
        output = fn(prompt)
        output.latency_ms = (time.time() - start) * 1000
        return output

    def invoke_all(self, prompt: str) -> List[ModelOutput]:
        results = []
        for mid in self._models:
            out = self.invoke(mid, prompt)
            if out:
                results.append(out)
        return results

    def filter_by_capability(self, capability: ModelCapability) -> List[str]:
        return [mid for mid, p in self._models.items() if capability in p.capabilities]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_models": len(self._models),
            "avg_weight": statistics.mean([p.weight for p in self._models.values()]) if self._models else 0,
            "avg_confidence": statistics.mean([p.confidence for p in self._models.values()]) if self._models else 0,
        }


class EnsembleVoter:
    """Voting strategies untuk ensemble outputs."""

    def __init__(self, comparator: SemanticComparator):
        self.comparator = comparator

    def vote(self, outputs: List[ModelOutput], strategy: VoteStrategy, pool: Optional[ModelPool] = None) -> EnsembleResult:
        start = time.time()
        if not outputs:
            return EnsembleResult(str(uuid.uuid4())[:12], "", "", strategy, 0.0, [])

        if strategy == VoteStrategy.MAJORITY:
            return self._majority_vote(outputs, start)
        elif strategy == VoteStrategy.WEIGHTED:
            return self._weighted_vote(outputs, pool, start)
        elif strategy == VoteStrategy.CONFIDENCE:
            return self._confidence_vote(outputs, start)
        elif strategy == VoteStrategy.RANKED:
            return self._ranked_vote(outputs, pool, start)
        elif strategy == VoteStrategy.AVERAGE:
            return self._average_vote(outputs, start)
        return self._majority_vote(outputs, start)

    def _majority_vote(self, outputs: List[ModelOutput], start: float) -> EnsembleResult:
        clusters = self.comparator.cluster_outputs(outputs, threshold=0.6)
        if not clusters:
            return EnsembleResult(str(uuid.uuid4())[:12], "", "", VoteStrategy.MAJORITY, 0.0, outputs)
        winner_cluster = max(clusters, key=len)
        winner = winner_cluster[0]
        consensus = len(winner_cluster) / len(outputs)
        return EnsembleResult(
            result_id=str(uuid.uuid4())[:12],
            winning_output=winner.content,
            winning_model_id=winner.model_id,
            strategy=VoteStrategy.MAJORITY,
            consensus_score=round(consensus, 3),
            all_outputs=outputs,
            vote_distribution={f"cluster_{i}": len(c) for i, c in enumerate(clusters)},
            duration_ms=(time.time() - start) * 1000
        )

    def _weighted_vote(self, outputs: List[ModelOutput], pool: Optional[ModelPool], start: float) -> EnsembleResult:
        if not pool:
            return self._majority_vote(outputs, start)
        scores = {}
        for out in outputs:
            profile = pool.get(out.model_id)
            weight = profile.weight if profile else 1.0
            scores[out.model_id] = weight * out.confidence
        if not scores:
            return self._majority_vote(outputs, start)
        winner_id = max(scores, key=scores.get)
        winner = next(o for o in outputs if o.model_id == winner_id)
        total = sum(scores.values())
        return EnsembleResult(
            result_id=str(uuid.uuid4())[:12],
            winning_output=winner.content,
            winning_model_id=winner.model_id,
            strategy=VoteStrategy.WEIGHTED,
            consensus_score=round(scores[winner_id] / total, 3) if total > 0 else 0,
            all_outputs=outputs,
            vote_distribution={k: round(v / total, 3) for k, v in scores.items()},
            duration_ms=(time.time() - start) * 1000
        )

    def _confidence_vote(self, outputs: List[ModelOutput], start: float) -> EnsembleResult:
        if not outputs:
            return EnsembleResult(str(uuid.uuid4())[:12], "", "", VoteStrategy.CONFIDENCE, 0.0, outputs)
        winner = max(outputs, key=lambda o: o.confidence)
        avg_conf = statistics.mean([o.confidence for o in outputs])
        return EnsembleResult(
            result_id=str(uuid.uuid4())[:12],
            winning_output=winner.content,
            winning_model_id=winner.model_id,
            strategy=VoteStrategy.CONFIDENCE,
            consensus_score=round(winner.confidence, 3),
            all_outputs=outputs,
            vote_distribution={o.model_id: round(o.confidence, 3) for o in outputs},
            duration_ms=(time.time() - start) * 1000
        )

    def _ranked_vote(self, outputs: List[ModelOutput], pool: Optional[ModelPool], start: float) -> EnsembleResult:
        if not pool or not outputs:
            return self._majority_vote(outputs, start)
        # Borda count: rank by model weight * confidence
        scores = {}
        for out in outputs:
            profile = pool.get(out.model_id)
            weight = profile.weight if profile else 1.0
            scores[out.model_id] = weight * out.confidence
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        points = {}
        for rank, (mid, _) in enumerate(sorted_scores):
            points[mid] = len(sorted_scores) - rank
        winner_id = max(points, key=points.get)
        winner = next(o for o in outputs if o.model_id == winner_id)
        total = sum(points.values())
        return EnsembleResult(
            result_id=str(uuid.uuid4())[:12],
            winning_output=winner.content,
            winning_model_id=winner.model_id,
            strategy=VoteStrategy.RANKED,
            consensus_score=round(points[winner_id] / total, 3) if total > 0 else 0,
            all_outputs=outputs,
            vote_distribution={k: round(v / total, 3) for k, v in points.items()},
            duration_ms=(time.time() - start) * 1000
        )

    def _average_vote(self, outputs: List[ModelOutput], start: float) -> EnsembleResult:
        # For numeric outputs, compute average
        # For text, use most common cluster
        clusters = self.comparator.cluster_outputs(outputs, threshold=0.6)
        if not clusters:
            return EnsembleResult(str(uuid.uuid4())[:12], "", "", VoteStrategy.AVERAGE, 0.0, outputs)
        # Average consensus = all clusters weighted equally
        avg_size = len(outputs) / len(clusters)
        winner_cluster = max(clusters, key=len)
        winner = winner_cluster[0]
        return EnsembleResult(
            result_id=str(uuid.uuid4())[:12],
            winning_output=winner.content,
            winning_model_id=winner.model_id,
            strategy=VoteStrategy.AVERAGE,
            consensus_score=round(avg_size / len(outputs), 3) if outputs else 0,
            all_outputs=outputs,
            vote_distribution={f"cluster_{i}": len(c) for i, c in enumerate(clusters)},
            duration_ms=(time.time() - start) * 1000
        )


class EnsembleOrchestrator:
    """Main orchestrator untuk ensemble inference."""

    def __init__(self):
        self.pool = ModelPool()
        self.comparator = SemanticComparator()
        self.voter = EnsembleVoter(self.comparator)
        self._history: List[EnsembleResult] = []

    def register_model(self, profile: ModelProfile, invoke_fn: Callable[[str], ModelOutput]) -> None:
        self.pool.register(profile, invoke_fn)

    def query(self, prompt: str, strategy: VoteStrategy = VoteStrategy.MAJORITY, filter_cap: Optional[ModelCapability] = None) -> EnsembleResult:
        if filter_cap:
            model_ids = self.pool.filter_by_capability(filter_cap)
            outputs = [self.pool.invoke(mid, prompt) for mid in model_ids]
            outputs = [o for o in outputs if o]
        else:
            outputs = self.pool.invoke_all(prompt)
        result = self.voter.vote(outputs, strategy, self.pool)
        self._history.append(result)
        return result

    def query_with_fallback(self, prompt: str, strategies: List[VoteStrategy] = None) -> EnsembleResult:
        strategies = strategies or [VoteStrategy.CONFIDENCE, VoteStrategy.MAJORITY, VoteStrategy.WEIGHTED]
        for strategy in strategies:
            result = self.query(prompt, strategy)
            if result.consensus_score > 0.5:
                return result
        return result

    def get_history(self) -> List[EnsembleResult]:
        return self._history

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_queries": len(self._history),
            "pool": self.pool.get_stats(),
            "avg_consensus": statistics.mean([r.consensus_score for r in self._history]) if self._history else 0,
        }

    def export_history(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in self._history], f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("CROSS-MODEL ENSEMBLE DEMO")
    print("=" * 70)

    # Setup simulated models
    def model_gpt4(prompt: str) -> ModelOutput:
        return ModelOutput("gpt-4", f"GPT-4 answer: Python is a versatile language. [{prompt[:20]}]", confidence=0.95, tokens_used=50)

    def model_claude(prompt: str) -> ModelOutput:
        return ModelOutput("claude-3", f"Claude says: Python excels in readability and simplicity. [{prompt[:20]}]", confidence=0.92, tokens_used=45)

    def model_llama(prompt: str) -> ModelOutput:
        return ModelOutput("llama-3", f"Llama: Python is great for scripting and AI. [{prompt[:20]}]", confidence=0.85, tokens_used=40)

    def model_small(prompt: str) -> ModelOutput:
        return ModelOutput("tiny-model", f"Python is a language. [{prompt[:20]}]", confidence=0.60, tokens_used=20)

    def model_different(prompt: str) -> ModelOutput:
        return ModelOutput("divergent", f"JavaScript is the best web language. [{prompt[:20]}]", confidence=0.70, tokens_used=35)

    orchestrator = EnsembleOrchestrator()
    orchestrator.register_model(ModelProfile("gpt-4", "GPT-4", weight=1.5, confidence=0.95, capabilities={ModelCapability.REASONING, ModelCapability.CODING}), model_gpt4)
    orchestrator.register_model(ModelProfile("claude-3", "Claude 3", weight=1.4, confidence=0.92, capabilities={ModelCapability.REASONING, ModelCapability.CREATIVITY}), model_claude)
    orchestrator.register_model(ModelProfile("llama-3", "LLaMA 3", weight=1.0, confidence=0.85, capabilities={ModelCapability.CODING, ModelCapability.FACTUAL}), model_llama)
    orchestrator.register_model(ModelProfile("tiny-model", "Tiny Model", weight=0.5, confidence=0.60), model_small)
    orchestrator.register_model(ModelProfile("divergent", "Divergent", weight=0.8, confidence=0.70), model_different)

    prompt = "What is Python?"

    # 1. Majority vote
    print("\n[1] Majority Vote")
    r1 = orchestrator.query(prompt, VoteStrategy.MAJORITY)
    print(f"  Winner: {r1.winning_model_id}")
    print(f"  Output: {r1.winning_output[:60]}...")
    print(f"  Consensus: {r1.consensus_score:.2%}")
    print(f"  Distribution: {r1.vote_distribution}")

    # 2. Weighted vote
    print("\n[2] Weighted Vote")
    r2 = orchestrator.query(prompt, VoteStrategy.WEIGHTED)
    print(f"  Winner: {r2.winning_model_id}")
    print(f"  Consensus: {r2.consensus_score:.2%}")
    print(f"  Distribution: {r2.vote_distribution}")

    # 3. Confidence vote
    print("\n[3] Confidence Vote")
    r3 = orchestrator.query(prompt, VoteStrategy.CONFIDENCE)
    print(f"  Winner: {r3.winning_model_id}")
    print(f"  Consensus: {r3.consensus_score:.2%}")
    print(f"  Distribution: {r3.vote_distribution}")

    # 4. Ranked vote
    print("\n[4] Ranked Vote")
    r4 = orchestrator.query(prompt, VoteStrategy.RANKED)
    print(f"  Winner: {r4.winning_model_id}")
    print(f"  Consensus: {r4.consensus_score:.2%}")
    print(f"  Distribution: {r4.vote_distribution}")

    # 5. Average vote
    print("\n[5] Average Vote")
    r5 = orchestrator.query(prompt, VoteStrategy.AVERAGE)
    print(f"  Winner: {r5.winning_model_id}")
    print(f"  Consensus: {r5.consensus_score:.2%}")

    # 6. Capability filtering
    print("\n[6] Capability Filtering")
    r6 = orchestrator.query(prompt, VoteStrategy.MAJORITY, filter_cap=ModelCapability.CODING)
    print(f"  Coding models only: {len(r6.all_outputs)} models")
    print(f"  Winner: {r6.winning_model_id}")

    # 7. Fallback strategy
    print("\n[7] Fallback Strategy")
    r7 = orchestrator.query_with_fallback(prompt)
    print(f"  Best strategy result: {r7.strategy.name} with consensus {r7.consensus_score:.2%}")

    # 8. Semantic similarity
    print("\n[8] Semantic Similarity")
    comp = SemanticComparator()
    sim = comp.similarity("Python is great for AI", "Python excels in machine learning")
    print(f"  Similarity: {sim:.2%}")
    sim2 = comp.similarity("Python is great", "JavaScript is the best")
    print(f"  Dissimilarity: {sim2:.2%}")

    # 9. Stats
    print("\n[9] Ensemble Stats")
    print(f"  Stats: {orchestrator.get_stats()}")

    # 10. Export
    orchestrator.export_history("/tmp/ensemble_history.json")
    print(f"  Exported history to /tmp/ensemble_history.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
