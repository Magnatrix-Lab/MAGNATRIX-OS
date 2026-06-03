"""LLM Output Evaluator — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class EvalDimension(Enum):
    RELEVANCE = auto()
    COHERENCE = auto()
    COMPLETENESS = auto()
    FACTUALITY = auto()
    SAFETY = auto()

@dataclass
class EvalResult:
    dimension: EvalDimension
    score: float
    feedback: str
    metadata: Dict[str, Any] = field(default_factory=dict)

class OutputEvaluator:
    def __init__(self) -> None:
        self._evaluators: Dict[EvalDimension, Any] = {}

    def register(self, dimension: EvalDimension, evaluator) -> None:
        self._evaluators[dimension] = evaluator

    def evaluate(self, input_text: str, output_text: str) -> List[EvalResult]:
        results = []
        for dim, evaluator in self._evaluators.items():
            score, feedback = evaluator(input_text, output_text)
            results.append(EvalResult(dim, score, feedback))
        return results

    def overall_score(self, results: List[EvalResult]) -> float:
        if not results:
            return 0.0
        return sum(r.score for r in results) / len(results)

    def get_stats(self, results: List[EvalResult]) -> Dict[str, Any]:
        return {"dimensions": len(results), "overall": self.overall_score(results), "min": min(r.score for r in results), "max": max(r.score for r in results)}

def run() -> None:
    print("Output Evaluator test")
    e = OutputEvaluator()
    e.register(EvalDimension.RELEVANCE, lambda i, o: (0.9, "Highly relevant"))
    e.register(EvalDimension.COHERENCE, lambda i, o: (0.8, "Good flow"))
    e.register(EvalDimension.COMPLETENESS, lambda i, o: (0.7, "Some details missing"))
    results = e.evaluate("What is AI?", "AI is artificial intelligence.")
    for r in results:
        print("  " + r.dimension.name + ": " + str(r.score) + " - " + r.feedback)
    print("  Overall: " + str(e.overall_score(results)))
    print("  Stats: " + str(e.get_stats(results)))
    print("Output Evaluator test complete.")

if __name__ == "__main__":
    run()
