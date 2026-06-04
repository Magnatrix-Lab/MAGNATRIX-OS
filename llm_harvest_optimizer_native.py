"""Harvest Optimizer — timing, labor, equipment, weather window, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto

class HarvestOptimizer:
    def __init__(self, field_area: float = 100):
        self.field_area = field_area
        self.machines: List[Dict] = []
        self.labor: List[Dict] = []
        self.weather_window: List[bool] = []

    def add_machine(self, machine_id: str, capacity: float, cost_per_hour: float):
        self.machines.append({"id": machine_id, "capacity": capacity, "cost": cost_per_hour, "available": True})

    def add_labor(self, worker_id: str, skill: str, wage: float):
        self.labor.append({"id": worker_id, "skill": skill, "wage": wage, "available": True})

    def set_weather(self, days: List[bool]):
        self.weather_window = days

    def optimize(self, crop_maturity: List[float]) -> Dict:
        # Find best harvest window
        good_days = [i for i, ok in enumerate(self.weather_window) if ok]
        if not good_days:
            return {"days": [], "cost": 0, "feasible": False}
        # Assign machines
        total_capacity = sum(m["capacity"] for m in self.machines)
        days_needed = int(self.field_area / total_capacity) + 1 if total_capacity > 0 else 999
        selected_days = good_days[:days_needed]
        cost = sum(m["cost"] * 8 for m in self.machines) * len(selected_days)
        cost += sum(w["wage"] * 8 for w in self.labor) * len(selected_days)
        return {"days": selected_days, "cost": cost, "feasible": len(selected_days) >= days_needed}

    def stats(self) -> Dict:
        return {"machines": len(self.machines), "labor": len(self.labor), "good_days": sum(self.weather_window)}

def run():
    ho = HarvestOptimizer(200)
    ho.add_machine("M1", 50, 100)
    ho.add_machine("M2", 30, 80)
    ho.add_labor("W1", "driver", 20)
    ho.set_weather([True, True, False, True, True, True, False])
    print(ho.optimize([0.9, 0.95, 1.0]))
    print(ho.stats())

if __name__ == "__main__":
    run()
