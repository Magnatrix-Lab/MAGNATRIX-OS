"""Content Recommender - Content-based recommendation for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto
import math

@dataclass
class ContentRecommender:
    item_features: Dict[str, List[float]] = field(default_factory=dict)
    user_profiles: Dict[str, List[float]] = field(default_factory=dict)

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot = sum(x*y for x, y in zip(a, b))
        norm = math.sqrt(sum(x**2 for x in a)) * math.sqrt(sum(x**2 for x in b))
        return dot / norm if norm > 0 else 0.0

    def build_profile(self, user_id: str, liked_items: List[str]) -> None:
        features = [self.item_features[it] for it in liked_items if it in self.item_features]
        if features:
            n = len(features[0])
            self.user_profiles[user_id] = [sum(f[i] for f in features) / len(features) for i in range(n)]

    def recommend(self, user_id: str, n_items: int = 3) -> List[tuple]:
        if user_id not in self.user_profiles:
            return []
        profile = self.user_profiles[user_id]
        scores = []
        for item_id, features in self.item_features.items():
            if item_id not in self.user_profiles.get(user_id + "_liked", []):
                scores.append((item_id, self.cosine_similarity(profile, features)))
        return sorted(scores, key=lambda x: x[1], reverse=True)[:n_items]

    def stats(self) -> dict:
        return {"items": len(self.item_features), "users": len(self.user_profiles)}

def run():
    cr = ContentRecommender()
    cr.item_features = {"item1": [1, 0, 1], "item2": [0, 1, 1], "item3": [1, 1, 0], "item4": [0, 0, 1]}
    cr.build_profile("user1", ["item1"])
    recs = cr.recommend("user1", 2)
    print("Recommendations:", recs)
    print("Stats:", cr.stats())

if __name__ == "__main__":
    run()
