"""Building Automation — HVAC, lighting, occupancy, energy, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum, auto
import time

class BuildingAutomation:
    def __init__(self, building_id: str = "B1"):
        self.building_id = building_id
        self.zones: Dict[str, Dict] = {}
        self.occupancy: Dict[str, int] = {}
        self.energy = 0.0

    def add_zone(self, zone_id: str, area: float, base_temp: float = 22.0):
        self.zones[zone_id] = {
            "area": area,
            "target_temp": base_temp,
            "current_temp": base_temp,
            "lighting": 0.0,  # 0-1
            "hvac_on": False,
        }
        self.occupancy[zone_id] = 0

    def set_occupancy(self, zone_id: str, count: int):
        self.occupancy[zone_id] = count
        zone = self.zones.get(zone_id)
        if zone:
            if count > 0:
                zone["target_temp"] = 22.0
                zone["lighting"] = 1.0
            else:
                zone["target_temp"] = 18.0
                zone["lighting"] = 0.2

    def step(self, dt: float):
        for zone_id, zone in self.zones.items():
            diff = zone["target_temp"] - zone["current_temp"]
            if abs(diff) > 0.5:
                zone["hvac_on"] = True
                zone["current_temp"] += diff * 0.1 * dt
                self.energy += zone["area"] * 0.1 * dt
            else:
                zone["hvac_on"] = False
            self.energy += zone["area"] * zone["lighting"] * 0.05 * dt

    def total_energy(self) -> float:
        return self.energy

    def comfort_score(self) -> float:
        total = 0.0
        for zone_id, zone in self.zones.items():
            temp_diff = abs(zone["current_temp"] - 22.0)
            total += max(0, 1.0 - temp_diff / 5.0)
        return total / len(self.zones) if self.zones else 0

    def stats(self) -> Dict:
        return {"building": self.building_id, "zones": len(self.zones), "energy": self.energy, "comfort": self.comfort_score()}

def run():
    ba = BuildingAutomation("Office")
    ba.add_zone("Floor1", 500)
    ba.add_zone("Floor2", 400)
    ba.set_occupancy("Floor1", 20)
    ba.set_occupancy("Floor2", 0)
    for _ in range(10):
        ba.step(1.0)
    print(ba.stats())

if __name__ == "__main__":
    run()
