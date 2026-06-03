"""
llm_toxicity_filter_native.py
MAGNATRIX-OS Toxicity Filter Engine
Native Python, stdlib only.
Provides toxicity detection, severity classification, and content filtering.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional


class ToxicityLevel(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    SEVERE = "severe"


class ToxicityFilterEngine:
    def __init__(self) -> None:
        self._patterns: Dict[str, List[tuple]] = {
            "profanity": [(r"\b(damn|hell|shit|fuck|ass)\b", 0.3), (r"\b(bitch|crap|bastard)\b", 0.4)],
            "hate": [(r"\b(hate|kill|die|destroy)\b", 0.5), (r"\b(racist|nazi|terrorist)\b", 0.8)],
            "harassment": [(r"\b(stupid|idiot|moron|loser)\b", 0.3), (r"\b(ugly|worthless)\b", 0.5)],
            "threat": [(r"\b(will hurt|going to kill|better watch)\b", 0.9), (r"\b(die|death|murder)\b", 0.7)],
        }

    def analyze(self, text: str) -> Dict[str, Any]:
        total_score = 0.0
        matches = []
        for category, patterns in self._patterns.items():
            for pattern, weight in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    total_score += weight
                    matches.append((category, match.group(), weight))
        if total_score >= 2.0:
            level = ToxicityLevel.SEVERE
        elif total_score >= 1.5:
            level = ToxicityLevel.HIGH
        elif total_score >= 0.8:
            level = ToxicityLevel.MEDIUM
        elif total_score >= 0.3:
            level = ToxicityLevel.LOW
        else:
            level = ToxicityLevel.NONE
        return {"level": level.value, "score": total_score, "matches": matches}

    def is_safe(self, text: str, threshold: float = 0.8) -> bool:
        return self.analyze(text)["score"] < threshold

    def censor(self, text: str) -> str:
        for category, patterns in self._patterns.items():
            for pattern, weight in patterns:
                text = re.sub(pattern, "***", text, flags=re.IGNORECASE)
        return text


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Toxicity Filter")
    print("=" * 60)
    e = ToxicityFilterEngine()
    texts = ["Hello world", "You are stupid and ugly", "I will kill you", "This is fine"]
    for t in texts:
        result = e.analyze(t)
        print(f"  '{t[:30]}' -> {result['level']} (score={result['score']:.2f})")
    print("\nToxicity Filter test complete.")


if __name__ == "__main__":
    run()
