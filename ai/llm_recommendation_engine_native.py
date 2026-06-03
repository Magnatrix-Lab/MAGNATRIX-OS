#!/usr/bin/env python3
"""
MAGNATRIX-OS — Recommendation Engine
ai/llm_recommendation_engine_native.py

Features:
- Collaborative filtering (user-item similarity)
- Content-based filtering (item similarity)
- Hybrid scoring (combine CF + content)
- Popularity and trending boost
- Cold-start handling (new user/item fallback)

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("recommendation")


@dataclass
class UserItemInteraction:
    user_id: str
    item_id: str
    rating: float
    timestamp: float


@dataclass
class Item:
    id: str
    features: Dict[str, float]
    popularity: float = 0.0


class RecommendationEngine:
    """Hybrid recommendation engine."""

    def __init__(self):
        self._interactions: List[UserItemInteraction] = []
        self._items: Dict[str, Item] = {}
        self._user_items: Dict[str, List[str]] = defaultdict(list)
        self._item_users: Dict[str, List[str]] = defaultdict(list)
        self._user_ratings: Dict[str, Dict[str, float]] = defaultdict(dict)

    def add_item(self, item: Item) -> None:
        self._items[item.id] = item

    def add_interaction(self, interaction: UserItemInteraction) -> None:
        self._interactions.append(interaction)
        self._user_items[interaction.user_id].append(interaction.item_id)
        self._item_users[interaction.item_id].append(interaction.user_id)
        self._user_ratings[interaction.user_id][interaction.item_id] = interaction.rating

    def _user_similarity(self, u1: str, u2: str) -> float:
        items1 = set(self._user_items[u1])
        items2 = set(self._user_items[u2])
        intersection = items1 & items2
        if not intersection:
            return 0.0
        union = items1 | items2
        return len(intersection) / len(union)

    def _item_similarity(self, i1: str, i2: str) -> float:
        item1 = self._items.get(i1)
        item2 = self._items.get(i2)
        if not item1 or not item2:
            return 0.0
        all_keys = set(item1.features.keys()) | set(item2.features.keys())
        if not all_keys:
            return 0.0
        dot = sum(item1.features.get(k, 0) * item2.features.get(k, 0) for k in all_keys)
        norm1 = math.sqrt(sum(v * v for v in item1.features.values()))
        norm2 = math.sqrt(sum(v * v for v in item2.features.values()))
        return dot / (norm1 * norm2 + 1e-6)

    def recommend(self, user_id: str, n: int = 5) -> List[Tuple[str, float]]:
        if user_id not in self._user_items or not self._user_items[user_id]:
            return self._popularity_recommend(n)

        scores = defaultdict(float)
        # Collaborative filtering
        for other_user in self._user_ratings:
            if other_user == user_id:
                continue
            sim = self._user_similarity(user_id, other_user)
            for item_id, rating in self._user_ratings[other_user].items():
                if item_id not in self._user_items[user_id]:
                    scores[item_id] += sim * rating

        # Content-based
        user_items = self._user_items[user_id]
        for item_id, item in self._items.items():
            if item_id in user_items:
                continue
            max_sim = max(self._item_similarity(item_id, ui) for ui in user_items) if user_items else 0
            scores[item_id] += max_sim * 3.0

        # Popularity boost
        for item_id, item in self._items.items():
            scores[item_id] += item.popularity * 0.5

        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores[:n]

    def _popularity_recommend(self, n: int) -> List[Tuple[str, float]]:
        items = sorted(self._items.values(), key=lambda x: x.popularity, reverse=True)
        return [(item.id, item.popularity) for item in items[:n]]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "users": len(self._user_items),
            "items": len(self._items),
            "interactions": len(self._interactions),
        }


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Recommendation Engine")
    print("ai/llm_recommendation_engine_native.py")
    print("=" * 60)

    engine = RecommendationEngine()

    # Add items
    items = [
        Item("i1", {"tech": 1.0, "python": 1.0, "web": 0.0}, 0.9),
        Item("i2", {"tech": 1.0, "python": 0.5, "web": 0.5}, 0.7),
        Item("i3", {"tech": 1.0, "python": 0.0, "web": 1.0}, 0.8),
        Item("i4", {"tech": 0.5, "python": 1.0, "ml": 1.0}, 0.6),
        Item("i5", {"tech": 0.0, "python": 0.0, "web": 1.0, "design": 1.0}, 0.5),
    ]
    for item in items:
        engine.add_item(item)

    # Add interactions
    interactions = [
        ("alice", "i1", 5.0), ("alice", "i2", 4.0),
        ("bob", "i2", 5.0), ("bob", "i3", 4.0), ("bob", "i5", 3.0),
        ("carol", "i1", 4.0), ("carol", "i4", 5.0),
    ]
    for user, item, rating in interactions:
        engine.add_interaction(UserItemInteraction(user, item, rating, 0.0))

    # Recommend
    for user in ["alice", "bob", "carol", "dave"]:
        recs = engine.recommend(user, n=3)
        print(f"\nRecommendations for {user}:")
        for item_id, score in recs:
            print(f"  {item_id}: score={score:.2f}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
