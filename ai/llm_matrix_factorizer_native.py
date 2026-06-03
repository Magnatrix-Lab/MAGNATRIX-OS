"""Matrix Factorizer - SVD-style matrix factorization for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto
import random
import math

@dataclass
class MatrixFactorizer:
    num_factors: int = 2
    learning_rate: float = 0.01
    regularization: float = 0.01
    iterations: int = 100
    user_factors: Dict[str, List[float]] = field(default_factory=dict)
    item_factors: Dict[str, List[float]] = field(default_factory=dict)

    def fit(self, ratings: Dict[str, Dict[str, float]], seed: int = 42) -> None:
        random.seed(seed)
        users = list(ratings.keys())
        items = list(set().union(*[r.keys() for r in ratings.values()]))
        for u in users:
            self.user_factors[u] = [random.uniform(0, 0.1) for _ in range(self.num_factors)]
        for i in items:
            self.item_factors[i] = [random.uniform(0, 0.1) for _ in range(self.num_factors)]
        for _ in range(self.iterations):
            for u, user_ratings in ratings.items():
                for item, rating in user_ratings.items():
                    pred = sum(self.user_factors[u][f] * self.item_factors[item][f] for f in range(self.num_factors))
                    err = rating - pred
                    for f in range(self.num_factors):
                        u_f = self.user_factors[u][f]
                        i_f = self.item_factors[item][f]
                        self.user_factors[u][f] += self.learning_rate * (err * i_f - self.regularization * u_f)
                        self.item_factors[item][f] += self.learning_rate * (err * u_f - self.regularization * i_f)

    def predict(self, user: str, item: str) -> float:
        if user not in self.user_factors or item not in self.item_factors:
            return 0.0
        return sum(self.user_factors[user][f] * self.item_factors[item][f] for f in range(self.num_factors))

    def stats(self) -> dict:
        return {"factors": self.num_factors, "users": len(self.user_factors), "items": len(self.item_factors)}

def run():
    mf = MatrixFactorizer(2, 0.01, 0.01, 50)
    ratings = {"u1": {"a": 5, "b": 3}, "u2": {"a": 4, "c": 2}}
    mf.fit(ratings)
    print("Prediction u1-a:", round(mf.predict("u1", "a"), 4))
    print("Prediction u1-c:", round(mf.predict("u1", "c"), 4))
    print("Stats:", mf.stats())

if __name__ == "__main__":
    run()
