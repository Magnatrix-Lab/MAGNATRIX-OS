"""Food Safety Tracker — HACCP, CCP, temperature logs, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime

@dataclass
class TemperatureLog:
    timestamp: str
    ccp: str
    temp: float
    acceptable_range: Tuple[float, float]

class FoodSafetyTracker:
    def __init__(self):
        self.logs: List[TemperatureLog] = []
        self.ccps: Dict[str, Tuple[float, float]] = {}

    def add_ccp(self, name: str, min_temp: float, max_temp: float):
        self.ccps[name] = (min_temp, max_temp)

    def log(self, entry: TemperatureLog):
        self.logs.append(entry)

    def violations(self) -> List[TemperatureLog]:
        return [l for l in self.logs if l.temp < l.acceptable_range[0] or l.temp > l.acceptable_range[1]]

    def violation_rate(self) -> float:
        if not self.logs:
            return 0.0
        return len(self.violations()) / len(self.logs)

    def ccp_status(self, ccp: str) -> str:
        ccp_logs = [l for l in self.logs if l.ccp == ccp]
        if not ccp_logs:
            return "no_data"
        latest = ccp_logs[-1]
        min_t, max_t = latest.acceptable_range
        if min_t <= latest.temp <= max_t:
            return "safe"
        return "critical"

    def stats(self) -> Dict:
        return {"logs": len(self.logs), "violations": len(self.violations()), "rate": round(self.violation_rate(), 3)}

def run():
    fst = FoodSafetyTracker()
    fst.add_ccp("Cooking", 70, 100)
    fst.add_ccp("Cooling", 0, 5)
    fst.log(TemperatureLog("2024-01-01T10:00", "Cooking", 75, (70, 100)))
    fst.log(TemperatureLog("2024-01-01T11:00", "Cooking", 65, (70, 100)))
    fst.log(TemperatureLog("2024-01-01T12:00", "Cooling", 3, (0, 5)))
    print(fst.stats())
    print("CCP Cooking:", fst.ccp_status("Cooking"))

if __name__ == "__main__":
    run()
