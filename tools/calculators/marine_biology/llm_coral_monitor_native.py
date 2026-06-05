"""Coral Monitor — bleaching index, health score, coverage, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class CoralMonitor:
    temperature: float = 28.0
    dhw: float = 0.0
    """Degree Heating Weeks"""
    coverage_pct: float = 50.0
    species_count: int = 10

    def bleaching_risk(self) -> str:
        if self.dhw < 4:
            return "low"
        elif self.dhw < 8:
            return "moderate"
        elif self.dhw < 12:
            return "high"
        return "severe"

    def health_score(self) -> float:
        temp_stress = max(0, (self.temperature - 27) / 5)
        dhw_stress = min(1, self.dhw / 12)
        return max(0, 100 - temp_stress * 20 - dhw_stress * 50 - (100 - self.coverage_pct) * 0.3)

    def recovery_time(self) -> float:
        if self.dhw > 8:
            return 10.0
        elif self.dhw > 4:
            return 5.0
        return 2.0

    def trend(self, history: List[float]) -> str:
        if len(history) < 2:
            return "stable"
        if history[-1] > history[0] * 1.1:
            return "improving"
        elif history[-1] < history[0] * 0.9:
            return "declining"
        return "stable"

    def stats(self) -> Dict:
        return {"risk": self.bleaching_risk(), "health": round(self.health_score(), 1), "recovery_years": self.recovery_time()}

def run():
    cm = CoralMonitor(temperature=30, dhw=6, coverage_pct=40)
    print(cm.stats())
    print("Trend:", cm.trend([50, 48, 45, 40]))

if __name__ == "__main__":
    run()
