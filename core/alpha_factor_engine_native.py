#!/usr/bin/env python3
"""Alpha Factor Engine for MAGNATRIX-OS."""
from __future__ import annotations
import statistics
from typing import Any, Dict, List, Optional

class AlphaFactorEngine:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.factors: Dict[str, Any] = {}
    def add_factor(self, name: str, fn: callable):
        self.factors[name] = fn
    def calculate_alpha158(self, prices: List[float], volumes: List[float]) -> Dict[str, float]:
        if not prices or len(prices) < 20:
            return {"error": "insufficient data"}
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        factors = {
            "alpha_001": returns[-1] if returns else 0,
            "alpha_002": (prices[-1] - prices[-5]) / prices[-5] if len(prices) >= 5 else 0,
            "alpha_003": (prices[-1] - prices[-20]) / prices[-20] if len(prices) >= 20 else 0,
            "alpha_004": statistics.mean(returns[-5:]) if len(returns) >= 5 else 0,
            "alpha_005": statistics.stdev(returns[-10:]) if len(returns) >= 10 else 0,
            "alpha_006": volumes[-1] / statistics.mean(volumes[-5:]) if len(volumes) >= 5 and statistics.mean(volumes[-5:]) > 0 else 0,
            "alpha_007": (max(prices[-5:]) - min(prices[-5:])) / prices[-1] if len(prices) >= 5 and prices[-1] > 0 else 0,
            "alpha_008": (prices[-1] - statistics.mean(prices[-10:])) / statistics.stdev(prices[-10:]) if len(prices) >= 10 and statistics.stdev(prices[-10:]) > 0 else 0,
        }
        return factors
    def normalize(self, factors: Dict[str, float]) -> Dict[str, float]:
        values = list(factors.values())
        if not values: return factors
        mean = statistics.mean(values)
        std = statistics.stdev(values) if len(values) > 1 else 1
        if std == 0: std = 1
        return {k: (v - mean) / std for k, v in factors.items()}
    def to_dict(self): return {"factors": len(self.factors)}
