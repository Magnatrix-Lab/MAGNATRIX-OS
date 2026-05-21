#!/usr/bin/env python3
"""Collective Brain — Multi-agent weighted consensus for trading"""

import random
import json

class CollectiveBrain:
    def __init__(self):
        self.agents = {
            "BULL": {"bias": 0.3, "reputation": 0.8},
            "BEAR": {"bias": -0.3, "reputation": 0.7},
            "NEUTRAL": {"bias": 0.0, "reputation": 0.9},
        }

    def debate(self, market_condition="bull"):
        votes = []
        for name, profile in self.agents.items():
            confidence = random.uniform(0.4, 0.9) + profile["bias"]
            confidence = max(0, min(1, confidence))
            weight = confidence * profile["reputation"]
            side = "BUY" if confidence > 0.5 else "SELL"
            votes.append({"agent": name, "side": side, "confidence": confidence, "weight": weight})

        buy_weight = sum(v["weight"] for v in votes if v["side"] == "BUY")
        sell_weight = sum(v["weight"] for v in votes if v["side"] == "SELL")
        total = buy_weight + sell_weight

        consensus = "BUY" if buy_weight > sell_weight else "SELL"
        conf = max(buy_weight, sell_weight) / total if total > 0 else 0

        result = {"consensus": consensus, "confidence": round(conf, 3), "votes": votes}
        with open("trading/collective_brain_history.json", "w") as f:
            json.dump(result, f, indent=2)
        return result

if __name__ == "__main__":
    brain = CollectiveBrain()
    for condition in ["bull", "bear", "choppy"]:
        r = brain.debate(condition)
        print(f"{condition.upper()}: {r['consensus']} | conf={r['confidence']}")
