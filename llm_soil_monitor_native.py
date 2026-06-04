"""Soil Monitor — moisture, pH, nutrients, irrigation trigger, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto
import time

class SoilMonitor:
    def __init__(self, zone_count: int = 10):
        self.zones = {f"Z{i}": {"moisture": 50.0, "ph": 7.0, "n": 100.0, "p": 50.0, "k": 80.0} for i in range(zone_count)}
        self.thresholds = {"moisture": 30.0, "ph_min": 6.0, "ph_max": 8.0, "n": 50.0}
        self.alerts: List[Dict] = []
        self.history: List[Dict] = []

    def read(self, zone_id: str, moisture: float, ph: float, n: float, p: float, k: float):
        if zone_id in self.zones:
            self.zones[zone_id] = {"moisture": moisture, "ph": ph, "n": n, "p": p, "k": k}
            self.history.append({"zone": zone_id, "time": time.time(), "moisture": moisture})

    def check(self) -> List[Dict]:
        alerts = []
        for zid, data in self.zones.items():
            if data["moisture"] < self.thresholds["moisture"]:
                alerts.append({"zone": zid, "issue": "low_moisture", "value": data["moisture"]})
            if data["ph"] < self.thresholds["ph_min"] or data["ph"] > self.thresholds["ph_max"]:
                alerts.append({"zone": zid, "issue": "ph_imbalance", "value": data["ph"]})
            if data["n"] < self.thresholds["n"]:
                alerts.append({"zone": zid, "issue": "low_nitrogen", "value": data["n"]})
        self.alerts.extend(alerts)
        return alerts

    def irrigate_zones(self) -> List[str]:
        return [zid for zid, data in self.zones.items() if data["moisture"] < self.thresholds["moisture"]]

    def stats(self) -> Dict:
        return {"zones": len(self.zones), "alerts": len(self.alerts), "history": len(self.history)}

def run():
    sm = SoilMonitor(5)
    sm.read("Z0", 25, 6.5, 40, 30, 60)
    sm.read("Z1", 45, 7.2, 80, 50, 70)
    print(sm.check())
    print("Irrigate:", sm.irrigate_zones())
    print(sm.stats())

if __name__ == "__main__":
    run()
