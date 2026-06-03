"""Similarity Engine - Vector similarity computation for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum, auto
import math

class SimilarityType(Enum):
    COSINE = auto()
    EUCLIDEAN = auto()
    MANHATTAN = auto()
    JACCARD = auto()
    HAMMING = auto()

@dataclass
class SimilarityEngine:
    similarity_type: SimilarityType = SimilarityType.COSINE

    def compute(self, a: List[float], b: List[float]) -> float:
        if self.similarity_type == SimilarityType.COSINE:
            dot = sum(x*y for x, y in zip(a, b))
            norm = math.sqrt(sum(x**2 for x in a)) * math.sqrt(sum(x**2 for x in b))
            return dot / norm if norm > 0 else 0.0
        if self.similarity_type == SimilarityType.EUCLIDEAN:
            return 1.0 / (1.0 + math.sqrt(sum((x-y)**2 for x, y in zip(a, b))))
        if self.similarity_type == SimilarityType.MANHATTAN:
            return 1.0 / (1.0 + sum(abs(x-y) for x, y in zip(a, b)))
        if self.similarity_type == SimilarityType.JACCARD:
            a_set, b_set = set(a), set(b)
            intersection = len(a_set & b_set)
            union = len(a_set | b_set)
            return intersection / union if union > 0 else 0.0
        if self.similarity_type == SimilarityType.HAMMING:
            return sum(1 for x, y in zip(a, b) if x == y) / len(a) if a else 0.0
        return 0.0

    def find_nearest(self, query: List[float], candidates: Dict[str, List[float]], top_k: int = 3) -> List[tuple]:
        scores = [(name, self.compute(query, vec)) for name, vec in candidates.items()]
        return sorted(scores, key=lambda x: x[1], reverse=True)[:top_k]

    def stats(self) -> dict:
        return {"type": self.similarity_type.name}

def run():
    se = SimilarityEngine(SimilarityType.COSINE)
    candidates = {"doc1": [1, 0, 1], "doc2": [0, 1, 1], "doc3": [1, 1, 0]}
    nearest = se.find_nearest([1, 0, 1], candidates, 2)
    print("Nearest:", nearest)
    for st in [SimilarityType.COSINE, SimilarityType.EUCLIDEAN, SimilarityType.MANHATTAN]:
        print(f"{st.name}: {se.compute([1,2,3], [2,3,4])}")
    print("Stats:", se.stats())

if __name__ == "__main__":
    run()
