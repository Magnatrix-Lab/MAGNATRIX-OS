"""Energy Optimizer — load scheduling, peak shaving, demand response, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto

class EnergyOptimizer:
    def __init__(self, peak_limit: float = 1000):
        self.peak_limit = peak_limit
        self.loads: Dict[str, Dict] = {}
        self.schedule: List[Dict] = []

    def add_load(self, load_id: str, power: float, priority: int, flexible: bool = False, duration: float = 1.0):
        self.loads[load_id] = {"power": power, "priority": priority, "flexible": flexible, "duration": duration, "scheduled": False}

    def optimize(self, time_slots: int = 24) -> List[Dict]:
        self.schedule = []
        for t in range(time_slots):
            slot_loads = []
            total = 0.0
            for lid, l in sorted(self.loads.items(), key=lambda x: x[1]["priority"]):
                if l["scheduled"]:
                    continue
                if total + l["power"] <= self.peak_limit:
                    slot_loads.append(lid)
                    total += l["power"]
                    if not l["flexible"]:
                        l["scheduled"] = True
            self.schedule.append({"time": t, "loads": slot_loads, "total": total})
        return self.schedule

    def peak_shave(self, baseline: List[float]) -> List[float]:
        shaved = []
        for val in baseline:
            if val > self.peak_limit:
                shaved.append(self.peak_limit)
            else:
                shaved.append(val)
        return shaved

    def stats(self) -> Dict:
        return {"loads": len(self.loads), "peak_limit": self.peak_limit, "scheduled_slots": len(self.schedule)}

def run():
    eo = EnergyOptimizer(100)
    eo.add_load("HVAC", 60, 1, False)
    eo.add_load("EV", 40, 2, True, 4)
    eo.add_load("Lighting", 20, 3, True)
    eo.add_load("Pool", 30, 4, True)
    schedule = eo.optimize(8)
    print(schedule[:3])
    print(eo.stats())

if __name__ == "__main__":
    run()
