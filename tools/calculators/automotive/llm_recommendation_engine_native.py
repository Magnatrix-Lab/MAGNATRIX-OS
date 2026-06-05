"""Recommendation Engine — collaborative, content-based, similarity, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
import math

@dataclass
class RecommendationEngine:
    user_ratings: Dict[str, Dict[str, float]] = field(default_factory=dict)
    item_features: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def add_rating(self, user: str, item: str, rating: float):
        self.user_ratings.setdefault(user, {})[item] = rating

    def user_similarity(self, u1: str, u2: str) -> float:
        r1 = self.user_ratings.get(u1, {})
        r2 = self.user_ratings.get(u2, {})
        common = set(r1.keys()) & set(r2.keys())
        if not common:
            return 0.0
        dot = sum(r1[i] * r2[i] for i in common)
        n1 = math.sqrt(sum(r1[i]**2 for i in common))
        n2 = math.sqrt(sum(r2[i]**2 for i in common))
        return dot / (n1 * n2) if n1 * n2 > 0 else 0.0

    def recommend_collaborative(self, user: str, n: int = 3) -> List[Tuple[str, float]]:
        scores = {}
        for other, sim in ((u, self.user_similarity(user, u)) for u in self.user_ratings if u != user):
            if sim <= 0:
                continue
            for item, rating in self.user_ratings[other].items():
                if item not in self.user_ratings.get(user, {}):
                    scores[item] = scores.get(item, 0) + sim * rating
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:n]

    def content_similarity(self, item1: str, item2: str) -> float:
        f1 = self.item_features.get(item1, {})
        f2 = self.item_features.get(item2, {})
        if not f1 or not f2:
            return 0.0
        common = set(f1.keys()) & set(f2.keys())
        if not common:
            return 0.0
        dot = sum(f1[k] * f2[k] for k in common)
        n1 = math.sqrt(sum(f1[k]**2 for k in common))
        n2 = math.sqrt(sum(f2[k]**2 for k in common))
        return dot / (n1 * n2) if n1 * n2 > 0 else 0.0

    def stats(self, user: str) -> Dict:
        return {"users": len(self.user_ratings), "items": len(self.item_features), "recommendations": len(self.recommend_collaborative(user))}

def run():
    re = RecommendationEngine()
    re.add_rating("U1", "A", 5)
    re.add_rating("U1", "B", 3)
    re.add_rating("U2", "A", 4)
    re.add_rating("U2", "C", 5)
    re.add_rating("U3", "B", 4)
    re.add_rating("U3", "C", 5)
    print(re.recommend_collaborative("U1"))
    print(re.stats("U1"))

if __name__ == "__main__":
    run()
