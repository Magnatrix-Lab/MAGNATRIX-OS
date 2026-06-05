"""Maintenance Planner — predictive, preventive, MTBF, spare parts, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto
import time

class MaintenancePlanner:
    def __init__(self):
        self.assets: Dict[str, Dict] = {}
        self.schedule: List[Dict] = []
        self.spare_parts: Dict[str, int] = {}

    def add_asset(self, asset_id: str, mtbf: float, last_maintenance: float, criticality: int = 1):
        self.assets[asset_id] = {"mtbf": mtbf, "last": last_maintenance, "criticality": criticality, "health": 1.0}

    def predict_failure(self, asset_id: str, now: float = None) -> float:
        now = now or time.time()
        asset = self.assets.get(asset_id)
        if not asset:
            return 0.0
        age = now - asset["last"]
        prob = min(1.0, age / asset["mtbf"])
        asset["health"] = 1.0 - prob
        return prob

    def schedule_maintenance(self, horizon: float = 86400 * 30):
        now = time.time()
        for aid, asset in self.assets.items():
            prob = self.predict_failure(aid, now)
            if prob > 0.5:
                self.schedule.append({"asset": aid, "time": now + (1 - prob) * asset["mtbf"], "type": "predictive", "priority": asset["criticality"]})
            elif (now - asset["last"]) > asset["mtbf"] * 0.8:
                self.schedule.append({"asset": aid, "time": now + asset["mtbf"] * 0.2, "type": "preventive", "priority": asset["criticality"]})
        self.schedule.sort(key=lambda x: x["priority"])

    def add_spare(self, part_id: str, quantity: int):
        self.spare_parts[part_id] = self.spare_parts.get(part_id, 0) + quantity

    def stats(self) -> Dict:
        return {"assets": len(self.assets), "scheduled": len(self.schedule), "spares": len(self.spare_parts)}

def run():
    mp = MaintenancePlanner()
    mp.add_asset("P1", 86400 * 30, time.time() - 86400 * 25, 2)
    mp.add_asset("P2", 86400 * 60, time.time() - 86400 * 10, 1)
    mp.schedule_maintenance()
    print(mp.schedule)
    print(mp.stats())

if __name__ == "__main__":
    run()
