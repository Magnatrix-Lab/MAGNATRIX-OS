"""LLM Attention Analyzer — Native Python (stdlib only)."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class AttentionPattern(Enum):
    UNIFORM = auto()
    FOCUSED = auto()
    DIFFUSE = auto()
    HEAD_SPLIT = auto()

class AttentionAnalyzer:
    def __init__(self) -> None:
        self._history: List[List[List[float]]] = []

    def add_attention_matrix(self, matrix: List[List[float]]) -> None:
        self._history.append(matrix)

    def analyze_entropy(self, matrix: List[List[float]]) -> List[float]:
        entropies = []
        for row in matrix:
            entropy = 0.0
            for p in row:
                if p > 0:
                    entropy -= p * math.log2(p)
            entropies.append(entropy)
        return entropies

    def analyze_focus(self, matrix: List[List[float]]) -> List[int]:
        focus_positions = []
        for row in matrix:
            max_val = max(row)
            focus_positions.append(row.index(max_val))
        return focus_positions

    def detect_pattern(self, matrix: List[List[float]]) -> AttentionPattern:
        entropies = self.analyze_entropy(matrix)
        avg_entropy = sum(entropies) / len(entropies) if entropies else 0.0
        if avg_entropy < 1.0:
            return AttentionPattern.FOCUSED
        elif avg_entropy > 3.0:
            return AttentionPattern.DIFFUSE
        return AttentionPattern.UNIFORM

    def get_stats(self, matrix: List[List[float]]) -> Dict[str, Any]:
        entropies = self.analyze_entropy(matrix)
        return {"heads": len(matrix), "avg_entropy": sum(entropies) / len(entropies) if entropies else 0.0, "pattern": self.detect_pattern(matrix).name}

def run() -> None:
    print("Attention Analyzer test")
    e = AttentionAnalyzer()
    matrix = [
        [0.9, 0.05, 0.05],
        [0.1, 0.8, 0.1],
        [0.2, 0.2, 0.6]
    ]
    e.add_attention_matrix(matrix)
    print("  Entropies: " + str(e.analyze_entropy(matrix)))
    print("  Focus: " + str(e.analyze_focus(matrix)))
    print("  Pattern: " + e.detect_pattern(matrix).name)
    print("  Stats: " + str(e.get_stats(matrix)))
    print("Attention Analyzer test complete.")

if __name__ == "__main__":
    run()
