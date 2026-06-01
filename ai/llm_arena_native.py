#!/usr/bin/env python3
"""llm_arena_native.py — LLM Arena: Multi-Model Ensemble + Reasoning + Self-Improvement Engine.

Goal: Surpass Claude through ensemble intelligence, distributed reasoning,
self-play competition, and synthetic training data generation.
Not a single model — a system that orchestrates many models to achieve
superior performance across all domains.
"""

from __future__ import annotations
import hashlib, time, random, json, math, statistics
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum, auto


class ModelCapability(Enum):
    REASONING = "reasoning"
    CODING = "coding"
    WRITING = "writing"
    MATH = "math"
    SCIENCE = "science"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    CREATIVITY = "creativity"
    KNOWLEDGE = "knowledge"
    CONVERSATION = "conversation"


class VoteStrategy(Enum):
    BEST_SINGLE = "best_single"
    MAJORITY = "majority"
    WEIGHTED = "weighted"
    CONSENSUS = "consensus"
    DEBATE = "debate"
    CASCADE = "cascade"


@dataclass
class ModelAgent:
    id: str
    name: str
    provider: str
    param_count: str
    capabilities: Dict[ModelCapability, float]
    latency_ms: float
    cost_per_1k: float
    reliability: float
    context_window: int
    supports_tools: bool
    supports_vision: bool
    supports_streaming: bool
    status: str = "active"
    win_count: int = 0
    total_calls: int = 0
    avg_score: float = 0.0


@dataclass
class QueryResult:
    model_id: str
    prompt: str
    response: str
    tokens_in: int
    tokens_out: int
    latency_ms: float
    scores: Dict[str, float]
    timestamp: float


@dataclass
class ArenaMatch:
    id: str
    prompt: str
    category: ModelCapability
    results: List[QueryResult] = field(default_factory=list)
    winner_id: Optional[str] = None
    ensemble_output: Optional[str] = None
    reasoning_chain: List[str] = field(default_factory=list)


class ModelRegistry:
    """Register all available LLM models with capability scores."""

    def __init__(self):
        self._models: Dict[str, ModelAgent] = {}
        self._init_models()

    def _init_models(self):
        # Real-world models with simulated capability scores (0-1)
        models = [
            ("claude-3-5-sonnet", "Anthropic", "175B", {
                ModelCapability.REASONING: 0.92, ModelCapability.CODING: 0.91, ModelCapability.WRITING: 0.93,
                ModelCapability.MATH: 0.85, ModelCapability.SCIENCE: 0.88, ModelCapability.TRANSLATION: 0.82,
                ModelCapability.SUMMARIZATION: 0.90, ModelCapability.CREATIVITY: 0.87, ModelCapability.KNOWLEDGE: 0.89,
                ModelCapability.CONVERSATION: 0.94,
            }, 2500, 3.0, 0.98, 200000, True, False, True),
            ("gpt-4o", "OpenAI", "~1T", {
                ModelCapability.REASONING: 0.93, ModelCapability.CODING: 0.92, ModelCapability.WRITING: 0.90,
                ModelCapability.MATH: 0.88, ModelCapability.SCIENCE: 0.90, ModelCapability.TRANSLATION: 0.85,
                ModelCapability.SUMMARIZATION: 0.91, ModelCapability.CREATIVITY: 0.85, ModelCapability.KNOWLEDGE: 0.92,
                ModelCapability.CONVERSATION: 0.93,
            }, 1800, 5.0, 0.97, 128000, True, True, True),
            ("gemini-1.5-pro", "Google", "~1T", {
                ModelCapability.REASONING: 0.88, ModelCapability.CODING: 0.86, ModelCapability.WRITING: 0.85,
                ModelCapability.MATH: 0.90, ModelCapability.SCIENCE: 0.92, ModelCapability.TRANSLATION: 0.88,
                ModelCapability.SUMMARIZATION: 0.89, ModelCapability.CREATIVITY: 0.82, ModelCapability.KNOWLEDGE: 0.93,
                ModelCapability.CONVERSATION: 0.87,
            }, 2200, 3.5, 0.95, 2000000, True, True, True),
            ("llama-3-70b", "Meta", "70B", {
                ModelCapability.REASONING: 0.82, ModelCapability.CODING: 0.80, ModelCapability.WRITING: 0.78,
                ModelCapability.MATH: 0.75, ModelCapability.SCIENCE: 0.80, ModelCapability.TRANSLATION: 0.76,
                ModelCapability.SUMMARIZATION: 0.80, ModelCapability.CREATIVITY: 0.75, ModelCapability.KNOWLEDGE: 0.85,
                ModelCapability.CONVERSATION: 0.82,
            }, 800, 0.9, 0.92, 128000, True, False, True),
            ("llama-3-405b", "Meta", "405B", {
                ModelCapability.REASONING: 0.88, ModelCapability.CODING: 0.86, ModelCapability.WRITING: 0.84,
                ModelCapability.MATH: 0.82, ModelCapability.SCIENCE: 0.86, ModelCapability.TRANSLATION: 0.80,
                ModelCapability.SUMMARIZATION: 0.86, ModelCapability.CREATIVITY: 0.80, ModelCapability.KNOWLEDGE: 0.89,
                ModelCapability.CONVERSATION: 0.87,
            }, 1500, 2.5, 0.94, 128000, True, False, True),
            ("mixtral-8x22b", "Mistral", "176B", {
                ModelCapability.REASONING: 0.85, ModelCapability.CODING: 0.84, ModelCapability.WRITING: 0.80,
                ModelCapability.MATH: 0.78, ModelCapability.SCIENCE: 0.82, ModelCapability.TRANSLATION: 0.82,
                ModelCapability.SUMMARIZATION: 0.84, ModelCapability.CREATIVITY: 0.78, ModelCapability.KNOWLEDGE: 0.86,
                ModelCapability.CONVERSATION: 0.83,
            }, 1200, 1.5, 0.93, 65000, True, False, True),
            ("qwen-2-72b", "Alibaba", "72B", {
                ModelCapability.REASONING: 0.83, ModelCapability.CODING: 0.85, ModelCapability.WRITING: 0.79,
                ModelCapability.MATH: 0.86, ModelCapability.SCIENCE: 0.84, ModelCapability.TRANSLATION: 0.85,
                ModelCapability.SUMMARIZATION: 0.82, ModelCapability.CREATIVITY: 0.76, ModelCapability.KNOWLEDGE: 0.84,
                ModelCapability.CONVERSATION: 0.81,
            }, 900, 0.8, 0.91, 128000, True, False, True),
            ("deepseek-v2", "DeepSeek", "236B", {
                ModelCapability.REASONING: 0.87, ModelCapability.CODING: 0.89, ModelCapability.WRITING: 0.81,
                ModelCapability.MATH: 0.88, ModelCapability.SCIENCE: 0.85, ModelCapability.TRANSLATION: 0.80,
                ModelCapability.SUMMARIZATION: 0.84, ModelCapability.CREATIVITY: 0.77, ModelCapability.KNOWLEDGE: 0.87,
                ModelCapability.CONVERSATION: 0.84,
            }, 1100, 1.2, 0.93, 128000, True, False, True),
            ("phi-3-medium", "Microsoft", "14B", {
                ModelCapability.REASONING: 0.78, ModelCapability.CODING: 0.82, ModelCapability.WRITING: 0.75,
                ModelCapability.MATH: 0.76, ModelCapability.SCIENCE: 0.78, ModelCapability.TRANSLATION: 0.72,
                ModelCapability.SUMMARIZATION: 0.77, ModelCapability.CREATIVITY: 0.72, ModelCapability.KNOWLEDGE: 0.78,
                ModelCapability.CONVERSATION: 0.79,
            }, 400, 0.3, 0.88, 128000, True, False, True),
            ("magnatrix-7b", "MAGNATRIX", "7B", {
                ModelCapability.REASONING: 0.70, ModelCapability.CODING: 0.72, ModelCapability.WRITING: 0.68,
                ModelCapability.MATH: 0.65, ModelCapability.SCIENCE: 0.70, ModelCapability.TRANSLATION: 0.60,
                ModelCapability.SUMMARIZATION: 0.72, ModelCapability.CREATIVITY: 0.65, ModelCapability.KNOWLEDGE: 0.75,
                ModelCapability.CONVERSATION: 0.70,
            }, 300, 0.0, 0.85, 32768, True, False, True),
            ("magnatrix-1b", "MAGNATRIX", "1B", {
                ModelCapability.REASONING: 0.55, ModelCapability.CODING: 0.58, ModelCapability.WRITING: 0.52,
                ModelCapability.MATH: 0.50, ModelCapability.SCIENCE: 0.55, ModelCapability.TRANSLATION: 0.45,
                ModelCapability.SUMMARIZATION: 0.58, ModelCapability.CREATIVITY: 0.50, ModelCapability.KNOWLEDGE: 0.60,
                ModelCapability.CONVERSATION: 0.55,
            }, 150, 0.0, 0.80, 16384, True, False, True),
        ]
        for mid, provider, params, caps, latency, cost, reliability, ctx, tools, vision, stream in models:
            self._models[mid] = ModelAgent(
                id=mid, name=mid, provider=provider, param_count=params,
                capabilities=caps, latency_ms=latency, cost_per_1k=cost,
                reliability=reliability, context_window=ctx,
                supports_tools=tools, supports_vision=vision, supports_streaming=stream,
            )

    def get_best_for(self, capability: ModelCapability, top_n: int = 3) -> List[ModelAgent]:
        candidates = [m for m in self._models.values() if m.status == "active"]
        candidates.sort(key=lambda m: (m.capabilities.get(capability, 0), m.reliability), reverse=True)
        return candidates[:top_n]

    def get_model(self, model_id: str) -> Optional[ModelAgent]:
        return self._models.get(model_id)

    def all_models(self) -> List[ModelAgent]:
        return list(self._models.values())

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total": len(self._models),
            "active": sum(1 for m in self._models.values() if m.status == "active"),
            "avg_reliability": sum(m.reliability for m in self._models.values()) / len(self._models),
        }


class QuerySimulator:
    """Simulate querying an LLM model."""

    def __init__(self, registry: ModelRegistry):
        self.registry = registry

    def query(self, model_id: str, prompt: str, category: ModelCapability) -> QueryResult:
        model = self.registry.get_model(model_id)
        if not model:
            return QueryResult(model_id, prompt, "Error: Model not found", 0, 0, 0, {}, time.time())

        # Simulate latency with some variance
        latency = model.latency_ms * random.uniform(0.8, 1.5)
        tokens_in = len(prompt.split()) + len(prompt) // 4
        tokens_out = int(tokens_in * random.uniform(0.5, 3.0))

        # Simulate response quality based on capability + noise
        base_score = model.capabilities.get(category, 0.5)
        noise = random.uniform(-0.08, 0.08)
        quality_score = max(0.0, min(1.0, base_score + noise))

        # Generate simulated response
        responses = {
            ModelCapability.REASONING: f"Step-by-step analysis: 1) Identify premises 2) Apply logical inference 3) Verify conclusion. Score: {quality_score:.3f}",
            ModelCapability.CODING: f"```python\n# Solution with {quality_score:.1%} confidence\ndef solve():\n    return optimized_result\n```",
            ModelCapability.WRITING: f"Creative response crafted with {quality_score:.1%} coherence and style alignment.",
            ModelCapability.MATH: f"Mathematical derivation: Let x be... After substitution, result = {quality_score:.3f} accurate.",
            ModelCapability.SCIENCE: f"Scientific explanation based on peer-reviewed methodology. Confidence: {quality_score:.1%}",
            ModelCapability.KNOWLEDGE: f"Factual response with {quality_score:.1%} accuracy against verified sources.",
            ModelCapability.CONVERSATION: f"Natural, empathetic, context-aware response. Engagement score: {quality_score:.3f}",
        }
        response = responses.get(category, f"Response generated with {quality_score:.1%} quality score.")

        scores = {
            "quality": quality_score,
            "accuracy": max(0, min(1, quality_score + random.uniform(-0.05, 0.05))),
            "coherence": max(0, min(1, quality_score + random.uniform(-0.05, 0.05))),
            "helpfulness": max(0, min(1, quality_score + random.uniform(-0.05, 0.05))),
            "creativity": max(0, min(1, quality_score + random.uniform(-0.1, 0.1))),
        }

        model.total_calls += 1
        model.avg_score = (model.avg_score * (model.total_calls - 1) + quality_score) / model.total_calls

        return QueryResult(
            model_id=model_id, prompt=prompt, response=response,
            tokens_in=tokens_in, tokens_out=tokens_out, latency_ms=latency,
            scores=scores, timestamp=time.time(),
        )


class EnsembleEngine:
    """Combine multiple model outputs for superior results."""

    def __init__(self, registry: ModelRegistry, simulator: QuerySimulator):
        self.registry = registry
        self.simulator = simulator

    def query_ensemble(self, prompt: str, category: ModelCapability, strategy: VoteStrategy = VoteStrategy.CASCADE, models: List[str] = None) -> ArenaMatch:
        match_id = f"ARENA-{hashlib.sha256(f'{prompt}:{time.time()}'.encode()).hexdigest()[:8]}"

        # Select models
        if not models:
            models = [m.id for m in self.registry.get_best_for(category, top_n=5)]

        # Query all models
        results = [self.simulator.query(mid, prompt, category) for mid in models]

        # Apply strategy
        if strategy == VoteStrategy.BEST_SINGLE:
            winner = max(results, key=lambda r: r.scores["quality"])
            ensemble_output = winner.response
        elif strategy == VoteStrategy.MAJORITY:
            ensemble_output = self._majority_vote(results)
        elif strategy == VoteStrategy.WEIGHTED:
            ensemble_output = self._weighted_synthesis(results)
        elif strategy == VoteStrategy.CONSENSUS:
            ensemble_output = self._consensus_build(results)
        elif strategy == VoteStrategy.DEBATE:
            ensemble_output = self._debate_synthesis(results, category)
        elif strategy == VoteStrategy.CASCADE:
            ensemble_output = self._cascade_reasoning(results, prompt, category)
        else:
            ensemble_output = max(results, key=lambda r: r.scores["quality"]).response

        winner = max(results, key=lambda r: r.scores["quality"])

        match = ArenaMatch(
            id=match_id, prompt=prompt, category=category,
            results=results, winner_id=winner.model_id,
            ensemble_output=ensemble_output,
            reasoning_chain=[f"Queried {len(results)} models", f"Applied {strategy.value} strategy", f"Winner: {winner.model_id}"],
        )

        # Update winner stats
        winner_model = self.registry.get_model(winner.model_id)
        if winner_model:
            winner_model.win_count += 1

        return match

    def _majority_vote(self, results: List[QueryResult]) -> str:
        # Simple: pick the most common response pattern (simulated by quality)
        best = max(results, key=lambda r: r.scores["quality"])
        return f"[MAJORITY] {best.response}"

    def _weighted_synthesis(self, results: List[QueryResult]) -> str:
        total_quality = sum(r.scores["quality"] for r in results)
        if total_quality == 0:
            return results[0].response if results else ""
        # Simulated weighted synthesis
        best = max(results, key=lambda r: r.scores["quality"] * r.scores["accuracy"])
        return f"[WEIGHTED] Synthesized from {len(results)} models. Primary: {best.model_id} | Confidence: {best.scores['quality']:.3f}\n{best.response}"

    def _consensus_build(self, results: List[QueryResult]) -> str:
        avg_quality = sum(r.scores["quality"] for r in results) / len(results)
        best = max(results, key=lambda r: r.scores["quality"])
        return f"[CONSENSUS] Avg quality: {avg_quality:.3f} across {len(results)} models. Consensus reached via {best.model_id}.\n{best.response}"

    def _debate_synthesis(self, results: List[QueryResult], category: ModelCapability) -> str:
        # Simulate debate: each model critiques others' answers
        sorted_results = sorted(results, key=lambda r: r.scores["quality"], reverse=True)
        top_3 = sorted_results[:3]
        critiques = []
        for i, r in enumerate(top_3):
            critique = f"Model {r.model_id} argues: {r.response[:50]}... (score: {r.scores['quality']:.3f})"
            critiques.append(critique)
        winner = top_3[0]
        return f"[DEBATE] {len(top_3)} models debated.\n" + "\n".join(critiques) + f"\n\nWINNER: {winner.model_id}\n{winner.response}"

    def _cascade_reasoning(self, results: List[QueryResult], prompt: str, category: ModelCapability) -> str:
        # Cascade: use strongest model for reasoning, others for verification
        sorted_results = sorted(results, key=lambda r: r.scores["quality"], reverse=True)
        primary = sorted_results[0]
        verifiers = sorted_results[1:3]

        verification = ""
        if verifiers:
            avg_verification = sum(v.scores["accuracy"] for v in verifiers) / len(verifiers)
            verification = f"Verified by {len(verifiers)} models. Avg accuracy: {avg_verification:.3f}"

        return f"[CASCADE] Primary: {primary.model_id} | {verification}\n{primary.response}"

    def benchmark(self, prompts: List[Tuple[str, ModelCapability]], strategies: List[VoteStrategy] = None) -> Dict[str, Any]:
        strategies = strategies or [VoteStrategy.BEST_SINGLE, VoteStrategy.WEIGHTED, VoteStrategy.CASCADE]
        results = {s.value: [] for s in strategies}

        for prompt, category in prompts:
            for strategy in strategies:
                match = self.query_ensemble(prompt, category, strategy)
                avg_score = sum(r.scores["quality"] for r in match.results) / len(match.results)
                results[strategy.value].append({
                    "prompt": prompt[:50], "category": category.value,
                    "winner": match.winner_id, "ensemble_score": avg_score,
                })

        # Calculate which strategy wins most
        strategy_scores = {s: sum(r["ensemble_score"] for r in results[s]) / len(results[s]) for s in results}
        best_strategy = max(strategy_scores, key=strategy_scores.get)

        return {
            "strategy_scores": strategy_scores,
            "best_strategy": best_strategy,
            "total_matches": len(prompts) * len(strategies),
        }


class SelfPlayTrainer:
    """Models compete against each other to improve."""

    def __init__(self, registry: ModelRegistry, ensemble: EnsembleEngine):
        self.registry = registry
        self.ensemble = ensemble
        self._history: List[Dict[str, Any]] = []

    def run_tournament(self, prompts: List[Tuple[str, ModelCapability]], rounds: int = 3) -> Dict[str, Any]:
        """Run tournament where models compete head-to-head."""
        models = self.registry.all_models()
        scores = {m.id: 0 for m in models}

        for round_num in range(1, rounds + 1):
            for prompt, category in prompts:
                match = self.ensemble.query_ensemble(prompt, category, VoteStrategy.BEST_SINGLE)
                if match.winner_id:
                    scores[match.winner_id] += 1

        # Rank models
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Update model stats
        for model_id, score in ranked:
            model = self.registry.get_model(model_id)
            if model:
                model.win_count += score

        self._history.append({"rounds": rounds, "scores": scores, "ranked": ranked, "time": time.time()})

        return {
            "rounds": rounds,
            "ranking": [{"model_id": m, "wins": s} for m, s in ranked],
            "champion": ranked[0][0] if ranked else None,
        }

    def generate_synthetic_data(self, category: ModelCapability, count: int = 10) -> List[Dict[str, Any]]:
        """Generate high-quality synthetic training prompts from top models."""
        top_models = self.registry.get_best_for(category, top_n=3)
        data = []
        for i in range(count):
            prompt = f"Synthetic prompt {i} for {category.value}"
            match = self.ensemble.query_ensemble(prompt, category, VoteStrategy.CASCADE, models=[m.id for m in top_models])
            data.append({
                "prompt": prompt,
                "category": category.value,
                "best_response": match.ensemble_output,
                "winner_model": match.winner_id,
                "quality_score": max(r.scores["quality"] for r in match.results),
            })
        return data

    def get_stats(self) -> Dict[str, Any]:
        return {
            "tournaments": len(self._history),
            "total_matches": sum(h["rounds"] * len(h["scores"]) for h in self._history),
        }


class LLMArena:
    """Main orchestrator: the complete system that surpasses individual models."""

    def __init__(self):
        self.registry = ModelRegistry()
        self.simulator = QuerySimulator(self.registry)
        self.ensemble = EnsembleEngine(self.registry, self.simulator)
        self.trainer = SelfPlayTrainer(self.registry, self.ensemble)

    def query(self, prompt: str, category: ModelCapability = None, strategy: VoteStrategy = VoteStrategy.CASCADE) -> ArenaMatch:
        if not category:
            category = self._detect_category(prompt)
        return self.ensemble.query_ensemble(prompt, category, strategy)

    def _detect_category(self, prompt: str) -> ModelCapability:
        prompt_lower = prompt.lower()
        if any(k in prompt_lower for k in ["code", "function", "def ", "program", "script", "algorithm"]):
            return ModelCapability.CODING
        if any(k in prompt_lower for k in ["math", "calculate", "equation", "solve", "integral", "derivative"]):
            return ModelCapability.MATH
        if any(k in prompt_lower for k in ["why", "explain", "how does", "reason", "analyze", "logic"]):
            return ModelCapability.REASONING
        if any(k in prompt_lower for k in ["write", "essay", "story", "poem", "creative", "draft"]):
            return ModelCapability.WRITING
        if any(k in prompt_lower for k in ["translate", "language", "english", "indonesian", "french"]):
            return ModelCapability.TRANSLATION
        if any(k in prompt_lower for k in ["summarize", "summary", "tl;dr", "brief"]):
            return ModelCapability.SUMMARIZATION
        return ModelCapability.KNOWLEDGE

    def run_tournament(self, prompts: List[Tuple[str, ModelCapability]]) -> Dict[str, Any]:
        return self.trainer.run_tournament(prompts, rounds=3)

    def generate_training_data(self, category: ModelCapability, count: int = 10) -> List[Dict[str, Any]]:
        return self.trainer.generate_synthetic_data(category, count)

    def get_leaderboard(self) -> List[Dict[str, Any]]:
        models = self.registry.all_models()
        return sorted([
            {
                "model_id": m.id,
                "provider": m.provider,
                "wins": m.win_count,
                "calls": m.total_calls,
                "avg_score": round(m.avg_score, 4),
                "reliability": m.reliability,
            }
            for m in models
        ], key=lambda x: x["wins"], reverse=True)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "registry": self.registry.get_stats(),
            "ensemble": {"strategies": [s.value for s in VoteStrategy]},
            "trainer": self.trainer.get_stats(),
            "leaderboard": self.get_leaderboard(),
        }


if __name__ == "__main__":
    arena = LLMArena()
    print("=" * 60)
    print("[LLM-ARENA] Multi-Model Ensemble + Reasoning Engine")
    print("=" * 60)

    # 1. Test reasoning with cascade
    print("\n  [TEST] Complex reasoning")
    match = arena.query("A farmer has 17 sheep and all but 9 die. How many are left?", ModelCapability.REASONING, VoteStrategy.CASCADE)
    print(f"    Winner: {match.winner_id}")
    print(f"    Ensemble: {match.ensemble_output[:100]}...")

    # 2. Test coding with debate
    print("\n  [TEST] Coding challenge")
    match = arena.query("Write a Python function to find the longest palindrome in a string", ModelCapability.CODING, VoteStrategy.DEBATE)
    print(f"    Winner: {match.winner_id}")

    # 3. Test math with weighted
    print("\n  [TEST] Mathematical proof")
    match = arena.query("Prove that the sum of angles in a triangle equals 180 degrees", ModelCapability.MATH, VoteStrategy.WEIGHTED)
    print(f"    Winner: {match.winner_id}")

    # 4. Tournament
    print("\n  [TOURNAMENT] Running competition...")
    prompts = [
        ("Explain quantum entanglement simply", ModelCapability.SCIENCE),
        ("Write a haiku about AI", ModelCapability.CREATIVITY),
        ("Debug this code: for i in range(10): print(i)", ModelCapability.CODING),
        ("What are the implications of AGI?", ModelCapability.KNOWLEDGE),
        ("Solve: 2x + 5 = 13", ModelCapability.MATH),
    ]
    tournament = arena.run_tournament(prompts)
    print(f"    Champion: {tournament['champion']}")
    for r in tournament["ranking"][:5]:
        print(f"      {r['model_id']}: {r['wins']} wins")

    # 5. Leaderboard
    print("\n  [LEADERBOARD]")
    for m in arena.get_leaderboard()[:10]:
        print(f"    {m['model_id']:20} | wins={m['wins']:3} | avg_score={m['avg_score']:.3f} | calls={m['calls']}")

    # 6. Synthetic data
    print("\n  [SYNTHETIC] Generating training data...")
    data = arena.generate_training_data(ModelCapability.REASONING, 3)
    print(f"    Generated {len(data)} high-quality samples")

    print(f"\n[STATS] {json.dumps(arena.get_stats(), indent=2, default=str)}")
