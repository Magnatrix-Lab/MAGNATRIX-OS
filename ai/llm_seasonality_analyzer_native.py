"""Seasonality Analyzer - Seasonal pattern detection for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum, auto
import math

class SeasonalityType(Enum):
    DAILY = auto()
    WEEKLY = auto()
    MONTHLY = auto()
    YEARLY = auto()
    CUSTOM = auto()

@dataclass
class SeasonalityAnalyzer:
    seasonality_type: SeasonalityType = SeasonalityType.WEEKLY
    custom_period: int = 7

    def get_period(self) -> int:
        if self.seasonality_type == SeasonalityType.DAILY: return 24
        if self.seasonality_type == SeasonalityType.WEEKLY: return 7
        if self.seasonality_type == SeasonalityType.MONTHLY: return 30
        if self.seasonality_type == SeasonalityType.YEARLY: return 365
        return self.custom_period

    def analyze(self, data: List[float]) -> Dict[str, List[float]]:
        period = self.get_period()
        pattern = []
        for i in range(period):
            values = [data[j] for j in range(i, len(data), period)]
            pattern.append(sum(values) / len(values) if values else 0.0)
        strength = max(pattern) - min(pattern) if pattern else 0.0
        return {"pattern": pattern, "strength": round(strength, 4), "period": period}

    def remove_seasonality(self, data: List[float]) -> List[float]:
        period = self.get_period()
        pattern = self.analyze(data)["pattern"]
        mean_p = sum(pattern) / len(pattern)
        return [data[i] - (pattern[i % period] - mean_p) for i in range(len(data))]

    def stats(self) -> dict:
        return {"type": self.seasonality_type.name, "period": self.get_period()}

def run():
    sa = SeasonalityAnalyzer(SeasonalityType.WEEKLY)
    data = [10, 12, 15, 14, 11, 9, 8, 11, 13, 16, 15, 12, 10, 9]
    result = sa.analyze(data)
    print("Pattern:", [round(v, 2) for v in result["pattern"]])
    print("Strength:", result["strength"])
    print("Stats:", sa.stats())

if __name__ == "__main__":
    run()
