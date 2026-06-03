"""LLM Financial Risk Scorer — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class RiskLevel(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()

@dataclass
class RiskFactor:
    id: str
    name: str
    weight: float
    score: float
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)

class FinancialRiskScorer:
    def __init__(self) -> None:
        self._factors: List[RiskFactor] = []

    def add_factor(self, factor: RiskFactor) -> None:
        self._factors.append(factor)

    def calculate_score(self) -> float:
        if not self._factors:
            return 0.0
        total_weight = sum(f.weight for f in self._factors)
        weighted_score = sum(f.weight * f.score for f in self._factors)
        return weighted_score / total_weight if total_weight > 0 else 0.0

    def get_risk_level(self, score: float) -> RiskLevel:
        if score < 0.3:
            return RiskLevel.LOW
        elif score < 0.6:
            return RiskLevel.MEDIUM
        elif score < 0.8:
            return RiskLevel.HIGH
        return RiskLevel.CRITICAL

    def stress_test(self, scenario: Dict[str, float]) -> float:
        adjusted = []
        for factor in self._factors:
            multiplier = scenario.get(factor.id, 1.0)
            adjusted.append(RiskFactor(factor.id, factor.name, factor.weight, factor.score * multiplier, factor.description))
        temp_scorer = FinancialRiskScorer()
        temp_scorer._factors = adjusted
        return temp_scorer.calculate_score()

    def get_contributors(self, top_n: int = 3) -> List[RiskFactor]:
        sorted_factors = sorted(self._factors, key=lambda f: f.weight * f.score, reverse=True)
        return sorted_factors[:top_n]

    def get_stats(self) -> Dict[str, Any]:
        score = self.calculate_score()
        return {"factors": len(self._factors), "score": score, "level": self.get_risk_level(score).name}

def run() -> None:
    print("Financial Risk Scorer test")
    e = FinancialRiskScorer()
    e.add_factor(RiskFactor("f1", "Market Volatility", 0.3, 0.7, "High market swings"))
    e.add_factor(RiskFactor("f2", "Credit Default", 0.25, 0.2, "Low default risk"))
    e.add_factor(RiskFactor("f3", "Liquidity", 0.2, 0.4, "Moderate liquidity"))
    e.add_factor(RiskFactor("f4", "Regulatory", 0.15, 0.6, "Changing regulations"))
    e.add_factor(RiskFactor("f5", "Operational", 0.1, 0.3, "Stable operations"))
    score = e.calculate_score()
    print("  Score: " + str(score))
    print("  Level: " + e.get_risk_level(score).name)
    print("  Stress test: " + str(e.stress_test({"f1": 1.5, "f3": 2.0})))
    print("  Top contributors: " + str([f.name for f in e.get_contributors(3)]))
    print("  Stats: " + str(e.get_stats()))
    print("Financial Risk Scorer test complete.")

if __name__ == "__main__":
    run()
