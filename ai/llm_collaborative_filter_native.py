"""Collaborative Filter - User-item collaborative filtering for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

class SimilarityMetric(Enum):
    COSINE = auto()
    PEARSON = auto()
    EUCLIDEAN = auto()

@dataclass
class CollaborativeFilter:
    similarity_metric: SimilarityMetric = SimilarityMetric.COSINE
    k_neighbors: int = 3
    user_ratings: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def similarity(self, a: Dict[str, float], b: Dict[str, float]) -> float:
        common = set(a.keys()) & set(b.keys())
        if not common:
            return 0.0
        if self.similarity_metric == SimilarityMetric.COSINE:
            dot = sum(a[i]*b[i] for i in common)
            norm_a = math.sqrt(sum(a[i]**2 for i in common))
            norm_b = math.sqrt(sum(b[i]**2 for i in common))
            return dot / (norm_a * norm_b) if norm_a * norm_b > 0 else 0.0
        if self.similarity_metric == SimilarityMetric.PEARSON:
            mean_a = sum(a[i] for i in common) / len(common)
            mean_b = sum(b[i] for i in common) / len(common)
            num = sum((a[i]-mean_a)*(b[i]-mean_b) for i in common)
            den = math.sqrt(sum((a[i]-mean_a)**2 for i in common)) * math.sqrt(sum((b[i]-mean_b)**2 for i in common))
            return num / den if den > 0 else 0.0
        if self.similarity_metric == SimilarityMetric.EUCLIDEAN:
            return 1.0 / (1.0 + math.sqrt(sum((a[i]-b[i])**2 for i in common)))
        return 0.0

    def recommend(self, user_id: str, n_items: int = 3) -> List[Tuple[str, float]]:
        if user_id not in self.user_ratings:
            return []
        target = self.user_ratings[user_id]
        similarities = []
        for other_id, ratings in self.user_ratings.items():
            if other_id != user_id:
                sim = self.similarity(target, ratings)
                similarities.append((other_id, sim))
        similarities.sort(key=lambda x: x[1], reverse=True)
        neighbors = similarities[:self.k_neighbors]
        scores = {}
        for item in set().union(*[self.user_ratings[uid].keys() for uid, _ in neighbors]) - set(target.keys()):
            weighted_sum = sum(self.user_ratings[uid].get(item, 0) * sim for uid, sim in neighbors)
            sim_sum = sum(sim for uid, sim in neighbors if item in self.user_ratings[uid])
            scores[item] = weighted_sum / sim_sum if sim_sum > 0 else 0
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:n_items]

    def stats(self) -> dict:
        return {"users": len(self.user_ratings), "metric": self.similarity_metric.name, "k": self.k_neighbors}

def run():
    cf = CollaborativeFilter(SimilarityMetric.COSINE, 2)
    cf.user_ratings = {"u1": {"a": 5, "b": 3, "c": 4}, "u2": {"a": 4, "b": 5, "d": 2}, "u3": {"b": 2, "c": 5, "d": 3}}
    recs = cf.recommend("u1", 2)
    print("Recommendations:", recs)
    print("Stats:", cf.stats())

if __name__ == "__main__":
    run()
