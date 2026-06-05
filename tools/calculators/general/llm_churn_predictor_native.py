"""Churn Predictor — behavioral signals, risk scoring, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto
import math

class ChurnPredictor:
    def __init__(self):
        self.signals = {
            "days_since_login": 0.3,
            "support_tickets": 0.2,
            "feature_usage_drop": 0.25,
            "payment_failures": 0.15,
            "competitor_mentions": 0.1,
        }
        self.risks: Dict[str, float] = {}

    def predict(self, customer_id: str, metrics: Dict[str, float]) -> float:
        score = 0.0
        for signal, weight in self.signals.items():
            val = metrics.get(signal, 0)
            score += min(val, 1.0) * weight
        self.risks[customer_id] = score
        return score

    def risk_level(self, score: float) -> str:
        if score >= 0.7:
            return "HIGH"
        elif score >= 0.4:
            return "MEDIUM"
        return "LOW"

    def at_risk(self, threshold: float = 0.5) -> List[str]:
        return [cid for cid, score in self.risks.items() if score >= threshold]

    def stats(self) -> Dict:
        return {"customers": len(self.risks), "high_risk": len(self.at_risk(0.7)), "medium_risk": len(self.at_risk(0.4)) - len(self.at_risk(0.7))}

def run():
    cp = ChurnPredictor()
    cp.predict("C1", {"days_since_login": 0.9, "support_tickets": 0.8, "feature_usage_drop": 0.7, "payment_failures": 0.2, "competitor_mentions": 0.1})
    cp.predict("C2", {"days_since_login": 0.1, "support_tickets": 0.0, "feature_usage_drop": 0.1, "payment_failures": 0.0, "competitor_mentions": 0.0})
    print(cp.at_risk(0.5))
    print(cp.stats())

if __name__ == "__main__":
    run()
