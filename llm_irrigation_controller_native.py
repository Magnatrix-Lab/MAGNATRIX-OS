"""Irrigation Controller — zones, scheduling, ET-based, weather skip, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto
import time

class IrrigationController:
    def __init__(self, flow_rate: float = 10.0):
        self.flow_rate = flow_rate
        self.zones: Dict[str, Dict] = {}
        self.schedule: List[Dict] = []
        self.water_used = 0.0

    def add_zone(self, zone_id: str, area: float, crop_factor: float = 1.0):
        self.zones[zone_id] = {"area": area, "crop_factor": crop_factor, "moisture": 50.0, "last_irrigated": 0}

    def schedule_irrigation(self, et0: float, rain_forecast: float = 0):
        for zid, zone in self.zones.items():
            need = max(0, zone["area"] * et0 * zone["crop_factor"] - rain_forecast)
            if zone["moisture"] < 30 or need > 5:
                duration = need / self.flow_rate
                self.schedule.append({"zone": zid, "duration": duration, "amount": need})
                self.water_used += need

    def run_schedule(self):
        for task in self.schedule:
            zid = task["zone"]
            if zid in self.zones:
                self.zones[zid]["moisture"] += task["amount"] * 2
                self.zones[zid]["last_irrigated"] = time.time()
        self.schedule = []

    def skip_rain(self, rain_mm: float):
        self.schedule = [t for t in self.schedule if t["amount"] > rain_mm]

    def stats(self) -> Dict:
        return {"zones": len(self.zones), "water_used": self.water_used, "pending": len(self.schedule)}

def run():
    ic = IrrigationController(15)
    ic.add_zone("Z1", 10, 0.8)
    ic.add_zone("Z2", 15, 1.2)
    ic.schedule_irrigation(5, 2)
    print(ic.schedule)
    ic.run_schedule()
    print(ic.stats())

if __name__ == "__main__":
    run()
