"""Food Safety Tracker — HACCP, temperature logs, recall, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto
import time

class FoodSafetyTracker:
    def __init__(self):
        self.products: Dict[str, Dict] = {}
        self.temperature_logs: List[Dict] = []
        self.recalls: List[Dict] = []
        self.hazards: List[str] = []

    def register_product(self, product_id: str, batch: str, temp_min: float, temp_max: float, shelf_life: int):
        self.products[product_id] = {
            "batch": batch,
            "temp_min": temp_min,
            "temp_max": temp_max,
            "shelf_life": shelf_life,
            "registered": time.time(),
            "status": "OK",
        }

    def log_temperature(self, product_id: str, temp: float, timestamp: float = None):
        timestamp = timestamp or time.time()
        self.temperature_logs.append({"product": product_id, "temp": temp, "time": timestamp})
        prod = self.products.get(product_id)
        if prod and (temp < prod["temp_min"] or temp > prod["temp_max"]):
            prod["status"] = "ALERT"
            self.hazards.append(f"Temperature violation: {product_id} at {temp}")

    def check_expiry(self, now: float = None) -> List[str]:
        now = now or time.time()
        expired = []
        for pid, prod in self.products.items():
            if now - prod["registered"] > prod["shelf_life"] * 86400:
                expired.append(pid)
                prod["status"] = "EXPIRED"
        return expired

    def recall(self, batch: str, reason: str):
        for pid, prod in self.products.items():
            if prod["batch"] == batch:
                prod["status"] = "RECALLED"
                self.recalls.append({"batch": batch, "reason": reason, "time": time.time()})

    def stats(self) -> Dict:
        statuses = {}
        for p in self.products.values():
            s = p["status"]
            statuses[s] = statuses.get(s, 0) + 1
        return {"products": len(self.products), "recalls": len(self.recalls), "hazards": len(self.hazards), "statuses": statuses}

def run():
    fst = FoodSafetyTracker()
    fst.register_product("P1", "B001", 2, 8, 7)
    fst.log_temperature("P1", 10)
    fst.log_temperature("P1", 5)
    print(fst.check_expiry())
    fst.recall("B001", "Contamination risk")
    print(fst.stats())

if __name__ == "__main__":
    run()
