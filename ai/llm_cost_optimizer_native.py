#!/usr/bin/env python3
"""
ai/llm_cost_optimizer_native.py
MAGNATRIX-OS — Cost + Latency Optimizer for the LLM Arena
AMATI pattern: smart routing, cost modeling, streaming simulation

Pure Python, stdlib only. Simulates cost-per-token, latency estimation,
capability matching, and smart model routing.
"""
from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


# ───────────────────────────────────────────────────────────────
# 0. UTILITIES
# ───────────────────────────────────────────────────────────────

def _now() -> float:
    return time.time()


def _token_count(text: str) -> int:
    return len(text) // 4 + 1


# ───────────────────────────────────────────────────────────────
# 1. COST MODEL
# ───────────────────────────────────────────────────────────────

@dataclass
class ModelCostProfile:
    model_id: str
    input_price_per_1k: float
    output_price_per_1k: float
    speed_tok_per_sec: float
    quality_score: float
    reliability: float


class CostModel:
    """Price-per-token calculator for each registered model."""

    PROFILES = {
        "claude-3-5-sonnet": ModelCostProfile("claude-3-5-sonnet", 3.0, 15.0, 45.0, 0.95, 0.98),
        "gpt-4o": ModelCostProfile("gpt-4o", 5.0, 15.0, 60.0, 0.93, 0.97),
        "gpt-4o-mini": ModelCostProfile("gpt-4o-mini", 0.15, 0.6, 120.0, 0.78, 0.97),
        "gemini-1.5-pro": ModelCostProfile("gemini-1.5-pro", 3.5, 10.5, 50.0, 0.92, 0.95),
        "gemini-1.5-flash": ModelCostProfile("gemini-1.5-flash", 0.35, 1.05, 150.0, 0.80, 0.95),
        "llama-3-70b": ModelCostProfile("llama-3-70b", 0.9, 0.9, 35.0, 0.88, 0.92),
        "llama-3-8b": ModelCostProfile("llama-3-8b", 0.2, 0.2, 200.0, 0.72, 0.92),
        "deepseek-v2": ModelCostProfile("deepseek-v2", 0.14, 0.28, 55.0, 0.86, 0.93),
        "qwen-2-72b": ModelCostProfile("qwen-2-72b", 0.5, 0.5, 40.0, 0.85, 0.91),
        "magnatrix-7b": ModelCostProfile("magnatrix-7b", 0.0, 0.0, 100.0, 0.70, 0.85),
    }

    def estimate_cost(self, model_id: str, input_tokens: int, output_tokens: int) -> float:
        p = self.PROFILES.get(model_id)
        if not p:
            return 0.0
        return (input_tokens / 1000) * p.input_price_per_1k + (output_tokens / 1000) * p.output_price_per_1k

    def get_profile(self, model_id: str) -> Optional[ModelCostProfile]:
        return self.PROFILES.get(model_id)

    def all_profiles(self) -> List[ModelCostProfile]:
        return list(self.PROFILES.values())


# ───────────────────────────────────────────────────────────────
# 2. LATENCY ESTIMATOR
# ───────────────────────────────────────────────────────────────

class LatencyEstimator:
    """Estimate response time per model based on prompt length and model speed."""

    def estimate(self, model_id: str, prompt_tokens: int, expected_output_tokens: int = 500) -> float:
        cm = CostModel()
        p = cm.get_profile(model_id)
        if not p:
            return 10.0
        overhead = 0.3 + random.uniform(0.0, 0.2)
        input_time = prompt_tokens / p.speed_tok_per_sec
        output_time = expected_output_tokens / p.speed_tok_per_sec
        return round(overhead + input_time + output_time, 2)

    def estimate_batch(self, model_id: str, prompts: List[str], expected_output: int = 500) -> Dict[str, float]:
        return {f"prompt_{i}": self.estimate(model_id, _token_count(p), expected_output) for i, p in enumerate(prompts)}


# ───────────────────────────────────────────────────────────────
# 3. CAPABILITY MATCHER
# ───────────────────────────────────────────────────────────────

class CapabilityMatcher:
    """Determine minimum capability threshold needed for a prompt."""

    COMPLEXITY_KEYWORDS = {
        "simple": ["what is", "who is", "when", "where", "list", "define", "yes/no"],
        "medium": ["how to", "explain", "compare", "difference", "example", "steps"],
        "complex": ["analyze", "evaluate", "synthesize", "debug", "optimize", "prove", "design", "architecture"],
    }

    def match(self, prompt: str) -> Dict[str, Any]:
        text = prompt.lower()
        level = "simple"
        for kw in self.COMPLEXITY_KEYWORDS["complex"]:
            if kw in text:
                level = "complex"
                break
        if level == "simple":
            for kw in self.COMPLEXITY_KEYWORDS["medium"]:
                if kw in text:
                    level = "medium"
                    break

        min_quality = {"simple": 0.6, "medium": 0.75, "complex": 0.88}[level]
        expected_tokens = {"simple": 200, "medium": 500, "complex": 1000}[level]
        return {"level": level, "min_quality": min_quality, "expected_output_tokens": expected_tokens}


# ───────────────────────────────────────────────────────────────
# 4. SMART ROUTER
# ───────────────────────────────────────────────────────────────

class SmartRouter:
    """Route to cheapest model that meets capability threshold, with fallback."""

    def __init__(self) -> None:
        self.cost_model = CostModel()
        self.latency = LatencyEstimator()
        self.capability = CapabilityMatcher()

    def route(self, prompt: str, preferred_model: Optional[str] = None) -> Dict[str, Any]:
        req = self.capability.match(prompt)
        prompt_tokens = _token_count(prompt)

        candidates = []
        for p in self.cost_model.all_profiles():
            if p.quality_score >= req["min_quality"] and p.reliability >= 0.85:
                cost = self.cost_model.estimate_cost(p.model_id, prompt_tokens, req["expected_output_tokens"])
                latency = self.latency.estimate(p.model_id, prompt_tokens, req["expected_output_tokens"])
                score = (p.quality_score * 100) / (cost + 0.01) / (latency + 0.1)
                candidates.append({
                    "model_id": p.model_id,
                    "quality": p.quality_score,
                    "cost_usd": round(cost, 6),
                    "latency_sec": latency,
                    "score": round(score, 2),
                })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        primary = candidates[0] if candidates else None
        fallback = candidates[1] if len(candidates) > 1 else None

        return {
            "primary": primary,
            "fallback": fallback,
            "all_candidates": candidates[:5],
            "requirement": req,
            "prompt_tokens": prompt_tokens,
        }

    def route_batch(self, prompts: List[str]) -> List[Dict[str, Any]]:
        return [self.route(p) for p in prompts]


# ───────────────────────────────────────────────────────────────
# 5. STREAMING SIMULATOR
# ───────────────────────────────────────────────────────────────

class StreamingSimulator:
    """Simulate progressive token delivery with early termination."""

    def simulate_stream(self, model_id: str, text: str, chunk_size: int = 8, confidence_threshold: float = 0.95) -> List[Dict[str, Any]]:
        cm = CostModel()
        p = cm.get_profile(model_id)
        if not p:
            return []

        tokens = text.split()
        chunks = []
        delivered = []
        confidence = 0.0
        for i in range(0, len(tokens), chunk_size):
            chunk = tokens[i:i + chunk_size]
            delivered.extend(chunk)
            confidence = min(0.5 + (len(delivered) / len(tokens)) * 0.5, 1.0) if tokens else 1.0
            chunks.append({
                "chunk_id": len(chunks) + 1,
                "tokens": len(chunk),
                "text": " ".join(chunk),
                "confidence": round(confidence, 3),
                "elapsed_ms": round((len(delivered) / p.speed_tok_per_sec) * 1000, 1),
            })
            if confidence >= confidence_threshold and len(delivered) / len(tokens) > 0.7:
                break
        return chunks

    def estimate_stream_time(self, model_id: str, total_tokens: int) -> float:
        cm = CostModel()
        p = cm.get_profile(model_id)
        if not p:
            return 1.0
        return round(total_tokens / p.speed_tok_per_sec, 2)


# ───────────────────────────────────────────────────────────────
# 6. BUDGET TRACKER
# ───────────────────────────────────────────────────────────────

class BudgetTracker:
    """Track spend per session/project, enforce limits."""

    def __init__(self, budget_usd: float = 10.0) -> None:
        self.budget = budget_usd
        self.spent = 0.0
        self.calls = 0
        self._history: List[Dict[str, Any]] = []

    def record(self, model_id: str, input_tokens: int, output_tokens: int, cost: float) -> None:
        self.spent += cost
        self.calls += 1
        self._history.append({
            "model_id": model_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": round(cost, 6),
            "timestamp": _now(),
        })

    def remaining(self) -> float:
        return round(self.budget - self.spent, 6)

    def is_exceeded(self) -> bool:
        return self.spent >= self.budget

    def stats(self) -> Dict[str, Any]:
        return {
            "budget": self.budget,
            "spent": round(self.spent, 6),
            "remaining": self.remaining(),
            "calls": self.calls,
            "avg_cost_per_call": round(self.spent / self.calls, 6) if self.calls else 0,
            "history_count": len(self._history),
        }

    def alert(self) -> Optional[str]:
        if self.spent >= self.budget * 0.9:
            return f"ALERT: Budget 90% spent (${self.spent:.4f} / ${self.budget})"
        if self.spent >= self.budget * 0.75:
            return f"WARNING: Budget 75% spent (${self.spent:.4f} / ${self.budget})"
        return None


# ───────────────────────────────────────────────────────────────
# 7. COST OPTIMIZER
# ───────────────────────────────────────────────────────────────

class CostOptimizer:
    """Main orchestrator: cost + latency + capability + streaming."""

    def __init__(self, budget_usd: float = 10.0) -> None:
        self.router = SmartRouter()
        self.streaming = StreamingSimulator()
        self.budget = BudgetTracker(budget_usd)

    def optimize(self, prompt: str, prefer_cheap: bool = True) -> Dict[str, Any]:
        route = self.router.route(prompt)
        primary = route["primary"]
        if not primary:
            return {"success": False, "error": "No suitable model found"}

        self.budget.record(
            primary["model_id"],
            route["prompt_tokens"],
            route["requirement"]["expected_output_tokens"],
            primary["cost_usd"],
        )

        dummy_response = "This is a simulated response generated by the model for the given prompt."
        stream_chunks = self.streaming.simulate_stream(
            primary["model_id"], dummy_response, chunk_size=4, confidence_threshold=0.92
        )

        return {
            "success": True,
            "selected_model": primary["model_id"],
            "cost_usd": primary["cost_usd"],
            "latency_sec": primary["latency_sec"],
            "quality": primary["quality"],
            "fallback": route["fallback"]["model_id"] if route["fallback"] else None,
            "stream_chunks": len(stream_chunks),
            "budget_status": self.budget.stats(),
            "alert": self.budget.alert(),
        }

    def optimize_batch(self, prompts: List[str]) -> List[Dict[str, Any]]:
        return [self.optimize(p) for p in prompts]

    def global_stats(self) -> Dict[str, Any]:
        return {"budget": self.budget.stats(), "models_available": len(self.router.cost_model.all_profiles())}


# ───────────────────────────────────────────────────────────────
# 8. DEMO
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Cost Optimizer Demo")
    print("=" * 60)

    optimizer = CostOptimizer(budget_usd=5.0)

    prompts = [
        "What is 2+2?",
        "Explain the theory of relativity in detail.",
        "Design a distributed system architecture for a real-time trading platform with sub-millisecond latency.",
    ]

    for i, prompt in enumerate(prompts, 1):
        print(f"\n[{i}] Prompt: {prompt[:60]}...")
        result = optimizer.optimize(prompt)
        if result["success"]:
            print(f"    Selected: {result['selected_model']}")
            print(f"    Cost: ${result['cost_usd']:.6f}")
            print(f"    Latency: {result['latency_sec']:.2f}s")
            print(f"    Quality: {result['quality']:.2f}")
            print(f"    Fallback: {result['fallback']}")
            print(f"    Stream chunks: {result['stream_chunks']}")
        else:
            print(f"    ERROR: {result['error']}")

    print("\n[Budget Status]")
    print(f"    {json.dumps(optimizer.budget.stats(), indent=2)}")
    if optimizer.budget.alert():
        print(f"    {optimizer.budget.alert()}")

    print("\n" + "=" * 60)
    print("Demo complete. Cost Optimizer ready for LLM Arena.")
    print("=" * 60)
