#!/usr/bin/env python3
"""Recommendation Engine for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

class RecommendationEngine:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.user_ratings: Dict[str, Dict[str, float]] = {}
        self.item_features: Dict[str, Dict[str, float]] = {}
    def add_rating(self, user: str, item: str, rating: float):
        if user not in self.user_ratings:
            self.user_ratings[user] = {}
        self.user_ratings[user][item] = rating
    def recommend_collaborative(self, user: str, top_k: int = 5) -> List[str]:
        if user not in self.user_ratings: return []
        scores: Dict[str, float] = {}
        for other, ratings in self.user_ratings.items():
            if other == user: continue
            common = set(self.user_ratings[user]) & set(ratings)
            if not common: continue
            sim = sum(abs(self.user_ratings[user][i] - ratings[i]) for i in common)
            if sim == 0: sim = 1
            for item, rating in ratings.items():
                if item not in self.user_ratings[user]:
                    scores[item] = scores.get(item, 0) + rating / sim
        return [item for item, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]]
    def recommend_content(self, item: str, top_k: int = 5) -> List[str]:
        if item not in self.item_features: return []
        target = self.item_features[item]
        scores = []
        for other, features in self.item_features.items():
            if other == item: continue
            sim = sum(abs(target.get(k, 0) - features.get(k, 0)) for k in set(target) | set(features))
            scores.append((other, 1/(1+sim)))
        return [item for item, _ in sorted(scores, key=lambda x: x[1], reverse=True)[:top_k]]
    def to_dict(self): return {"users": len(self.user_ratings), "items": len(self.item_features)}
