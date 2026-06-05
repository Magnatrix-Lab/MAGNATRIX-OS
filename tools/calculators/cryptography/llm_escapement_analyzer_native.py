"""Escapement Analyzer — beat rate, amplitude, daily rate, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class EscapementAnalyzer:
    beat_rate: float = 4.0
    """Hz"""
    amplitude: float = 270.0
    """degrees"""
    daily_rate: float = 0.0
    """seconds per day"""

    def beats_per_day(self) -> float:
        return self.beat_rate * 2 * 3600 * 24

    def beat_error(self) -> float:
        return abs(self.daily_rate) / (self.beat_rate * 2)

    def isochronism_error(self, amplitude_change: float) -> float:
        return amplitude_change * 0.01

    def power_reserve(self, mainspring_turns: float, gear_ratio: float) -> float:
        return mainspring_turns / gear_ratio / (self.beat_rate * 2 * 60)

    def quality_grade(self) -> str:
        if abs(self.daily_rate) <= 4 and self.amplitude >= 250:
            return "chronometer"
        elif abs(self.daily_rate) <= 10:
            return "high grade"
        elif abs(self.daily_rate) <= 30:
            return "standard"
        return "needs service"

    def stats(self) -> Dict:
        return {"bpd": self.beats_per_day(), "grade": self.quality_grade(), "beat_error": round(self.beat_error(), 3)}

def run():
    ea = EscapementAnalyzer(beat_rate=3, amplitude=280, daily_rate=2)
    print(ea.stats())
    print("Power reserve:", ea.power_reserve(8, 1/4))

if __name__ == "__main__":
    run()
