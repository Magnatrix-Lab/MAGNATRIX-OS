"""
llm_prompt_optimizer_native.py
MAGNATRIX-OS Prompt Optimizer Engine
Native Python, stdlib only.
Provides prompt compression, token optimization, redundancy removal, and efficiency scoring.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class OptimizationResult:
    original: str
    optimized: str
    original_tokens: int
    optimized_tokens: int
    savings_percent: float
    techniques_applied: List[str]
    quality_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_tokens": self.original_tokens, "optimized_tokens": self.optimized_tokens,
            "savings_percent": self.savings_percent, "techniques": self.techniques_applied,
            "quality_score": self.quality_score,
        }


class PromptOptimizerEngine:
    """Prompt optimization for token efficiency and clarity."""

    def __init__(self, chars_per_token: float = 4.0) -> None:
        self.chars_per_token = chars_per_token

    def estimate_tokens(self, text: str) -> int:
        return int(len(text) / self.chars_per_token)

    def optimize(self, prompt: str, techniques: Optional[List[str]] = None) -> OptimizationResult:
        applied = []
        original = prompt
        optimized = prompt

        if not techniques or "deduplicate" in techniques:
            optimized = self._deduplicate_lines(optimized)
            applied.append("deduplicate")

        if not techniques or "remove_fluff" in techniques:
            optimized = self._remove_fluff(optimized)
            applied.append("remove_fluff")

        if not techniques or "compress_whitespace" in techniques:
            optimized = self._compress_whitespace(optimized)
            applied.append("compress_whitespace")

        if not techniques or "truncate_repetition" in techniques:
            optimized = self._truncate_repetition(optimized)
            applied.append("truncate_repetition")

        orig_tokens = self.estimate_tokens(original)
        opt_tokens = self.estimate_tokens(optimized)
        savings = (orig_tokens - opt_tokens) / orig_tokens * 100 if orig_tokens > 0 else 0

        quality = self._score_quality(original, optimized)

        return OptimizationResult(
            original=original, optimized=optimized,
            original_tokens=orig_tokens, optimized_tokens=opt_tokens,
            savings_percent=savings, techniques_applied=applied, quality_score=quality
        )

    def _deduplicate_lines(self, text: str) -> str:
        lines = text.splitlines()
        seen = set()
        result = []
        for line in lines:
            stripped = line.strip()
            if stripped and stripped.lower() not in seen:
                seen.add(stripped.lower())
                result.append(line)
            elif not stripped:
                result.append(line)
        return "\n".join(result)

    def _remove_fluff(self, text: str) -> str:
        fluff_patterns = [
            r'\b(please|kindly|if you could|I would like|it would be great|could you)\b',
            r'\b(thank you in advance|thanks a lot|appreciate it)\b',
        ]
        for pattern in fluff_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        return text

    def _compress_whitespace(self, text: str) -> str:
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n\n+', '\n\n', text)
        return text.strip()

    def _truncate_repetition(self, text: str, max_repeat: int = 3) -> str:
        words = text.split()
        result = []
        repeat_count = 1
        for i, word in enumerate(words):
            if i > 0 and word.lower() == words[i - 1].lower():
                repeat_count += 1
                if repeat_count <= max_repeat:
                    result.append(word)
            else:
                repeat_count = 1
                result.append(word)
        return " ".join(result)

    def _score_quality(self, original: str, optimized: str) -> float:
        # Simple quality score: penalize heavy truncation
        ratio = len(optimized) / len(original) if original else 1.0
        if ratio > 0.9:
            return 0.95
        elif ratio > 0.7:
            return 0.85
        elif ratio > 0.5:
            return 0.7
        return 0.5

    def batch_optimize(self, prompts: List[str]) -> List[OptimizationResult]:
        return [self.optimize(p) for p in prompts]


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Prompt Optimizer Engine")
    print("=" * 60)

    engine = PromptOptimizerEngine()

    prompts = [
        "Please help me understand quantum computing. Please help me understand quantum computing. It would be great if you could explain it simply. Thanks a lot!",
        "Generate a summary of the following text. Generate a summary of the following text. Generate a summary. The text is about machine learning and artificial intelligence.",
        "Write a Python function to sort a list. Write a Python function to sort a list. Please write a Python function to sort a list.",
    ]

    for prompt in prompts:
        result = engine.optimize(prompt)
        print(f"\nOriginal: {prompt[:60]}...")
        print(f"  Tokens: {result.original_tokens} -> {result.optimized_tokens}")
        print(f"  Savings: {result.savings_percent:.1f}%")
        print(f"  Quality: {result.quality_score:.2f}")
        print(f"  Techniques: {result.techniques_applied}")

    print("\nPrompt Optimizer test complete.")


if __name__ == "__main__":
    run()
