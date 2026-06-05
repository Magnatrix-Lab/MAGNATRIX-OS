"""Predictive Maintenance — vibration, temperature, RUL, anomaly, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class PredictiveMaintenance:
    vibration: List[float] = field(default_factory=list)
    temperature: List[float] = field(default_factory=list)
    baseline_vib: float = 2.0
    baseline_temp: float = 60.0

    def vibration_rms(self) -> float:
        if not self.vibration:
            return 0.0
        return math.sqrt(sum(v**2 for v in self.vibration) / len(self.vibration))

    def anomaly_score(self) -> float:
        vib_rms = self.vibration_rms()
        temp_avg = sum(self.temperature) / len(self.temperature) if self.temperature else 0.0
        vib_score = max(0, (vib_rms - self.baseline_vib) / self.baseline_vib)
        temp_score = max(0, (temp_avg - self.baseline_temp) / self.baseline_temp)
        return min(1.0, vib_score * 0.5 + temp_score * 0.5)

    def rul(self, threshold: float = 0.8) -> float:
        score = self.anomaly_score()
        if score >= threshold:
            return 0.0
        return (threshold - score) / threshold * 100

    def maintenance_needed(self) -> bool:
        return self.anomaly_score() > 0.5

    def stats(self) -> Dict:
        return {"vib_rms": round(self.vibration_rms(), 3), "anomaly": round(self.anomaly_score(), 3), "rul": round(self.rul(), 1)}

def run():
    pm = PredictiveMaintenance(vibration=[2.1,2.5,3.0,4.5], temperature=[62,65,70,75])
    print(pm.stats())
    print("Maintenance needed:", pm.maintenance_needed())

if __name__ == "__main__":
    run()
