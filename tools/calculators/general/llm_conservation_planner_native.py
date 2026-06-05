"""Conservation Planner — artifact condition, treatment priority, risk assessment, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
from math import sqrt, pow, fabs, log, exp, max as math_max
from datetime import datetime, timedelta

class ConditionState(Enum):
    EXCELLENT = auto()
    GOOD = auto()
    FAIR = auto()
    POOR = auto()
    CRITICAL = auto()

class RiskLevel(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    EXTREME = auto()

class TreatmentType(Enum):
    CLEANING = auto()
    CONSOLIDATION = auto()
    DESALINATION = auto()
    ADHESIVE_REPAIR = auto()
    ENVIRONMENTAL_CONTROL = auto()
    DOCUMENTATION = auto()

@dataclass
class ConditionFactor:
    name: str
    score: float  # 0-1, 1 = worst
    weight: float = 1.0

@dataclass
class ConservationArtifact:
    id: str
    name: str
    condition: ConditionState
    factors: List[ConditionFactor] = field(default_factory=list)
    risks: List[Tuple[RiskLevel, str]] = field(default_factory=list)
    treatments: List[Tuple[TreatmentType, str]] = field(default_factory=list)
    storage_conditions: Dict[str, float] = field(default_factory=dict)

    def condition_score(self) -> float:
        """Aggregate condition score 0-1."""
        if not self.factors:
            mapping = {ConditionState.EXCELLENT: 0.0, ConditionState.GOOD: 0.2, ConditionState.FAIR: 0.5, ConditionState.POOR: 0.8, ConditionState.CRITICAL: 1.0}
            return mapping.get(self.condition, 0.5)
        weighted_sum = sum(f.score * f.weight for f in self.factors)
        total_weight = sum(f.weight for f in self.factors)
        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def highest_risk(self) -> Optional[RiskLevel]:
        if not self.risks:
            return None
        order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.EXTREME]
        levels = [r[0] for r in self.risks]
        return max(levels, key=lambda x: order.index(x))

class ConservationPlanner:
    def __init__(self):
        self.artifacts: List[ConservationArtifact] = []

    def add_artifact(self, artifact: ConservationArtifact) -> None:
        self.artifacts.append(artifact)

    def priority_queue(self) -> List[ConservationArtifact]:
        """Sort by condition score descending, then by highest risk."""
        risk_order = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2, RiskLevel.EXTREME: 3}
        def sort_key(a):
            hr = a.highest_risk()
            return (-a.condition_score(), -risk_order.get(hr, 0))
        return sorted(self.artifacts, key=sort_key)

    def treatment_plan(self, artifact: ConservationArtifact) -> List[Dict]:
        plan = []
        score = artifact.condition_score()
        if score > 0.7:
            plan.append({"treatment": TreatmentType.CONSOLIDATION, "priority": "urgent", "estimated_hours": 40})
        if score > 0.5:
            plan.append({"treatment": TreatmentType.CLEANING, "priority": "high", "estimated_hours": 20})
        if score > 0.3:
            plan.append({"treatment": TreatmentType.DOCUMENTATION, "priority": "medium", "estimated_hours": 10})
        if any(r[0] == RiskLevel.HIGH for r in artifact.risks):
            plan.append({"treatment": TreatmentType.ENVIRONMENTAL_CONTROL, "priority": "urgent", "estimated_hours": 5})
        return plan

    def environmental_recommendations(self, artifact: ConservationArtifact) -> Dict[str, float]:
        rec = {"temperature_c": 20.0, "humidity_pct": 50.0, "light_lux": 50.0}
        if any(f.name == "organic" for f in artifact.factors):
            rec["temperature_c"] = 18.0
            rec["humidity_pct"] = 45.0
        if any(f.name == "metal" for f in artifact.factors):
            rec["humidity_pct"] = 35.0
        if any(f.name == "textile" for f in artifact.factors):
            rec["light_lux"] = 30.0
        return rec

    def batch_treatment_cost(self, hourly_rate: float = 50.0) -> float:
        total = 0.0
        for a in self.artifacts:
            for t in self.treatment_plan(a):
                total += t["estimated_hours"] * hourly_rate
        return total

    def stats(self) -> Dict[str, float]:
        by_condition = {}
        for a in self.artifacts:
            c = a.condition.name
            by_condition[c] = by_condition.get(c, 0) + 1
        scores = [a.condition_score() for a in self.artifacts]
        return {
            "artifact_count": len(self.artifacts),
            "critical_count": by_condition.get(ConditionState.CRITICAL.name, 0),
            "poor_count": by_condition.get(ConditionState.POOR.name, 0),
            "avg_condition_score": sum(scores) / len(scores) if scores else 0.0,
            "max_condition_score": max(scores) if scores else 0.0,
            "estimated_cost_usd": self.batch_treatment_cost()
        }

def run():
    planner = ConservationPlanner()
    art1 = ConservationArtifact("A1", "Bronze Statue", ConditionState.POOR, [
        ConditionFactor("corrosion", 0.8, 2.0), ConditionFactor("crack", 0.6, 1.5)
    ], risks=[(RiskLevel.HIGH, "active corrosion")], storage_conditions={"temp": 22, "humidity": 60})
    art2 = ConservationArtifact("A2", "Ceramic Vase", ConditionState.CRITICAL, [
        ConditionFactor("breakage", 0.9, 2.0), ConditionFactor("surface_loss", 0.7, 1.0)
    ], risks=[(RiskLevel.EXTREME, "structural collapse")])
    planner.add_artifact(art1)
    planner.add_artifact(art2)
    queue = planner.priority_queue()
    print(f"Priority order: {[a.name for a in queue]}")
    for a in queue:
        print(f"  {a.name}: score={a.condition_score():.2f}, risk={a.highest_risk().name if a.highest_risk() else 'None'}")
        print(f"  Plan: {planner.treatment_plan(a)}")
        print(f"  Environment: {planner.environmental_recommendations(a)}")
    print(planner.stats())

if __name__ == "__main__":
    run()
