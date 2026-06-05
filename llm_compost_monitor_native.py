"""Compost Monitor -- temperature, moisture, C/N, maturity, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class CompostMonitor:
    temperature_c: float = 55.0
    moisture_pct: float = 50.0
    carbon_nitrogen_ratio: float = 30.0
    ph: float = 7.0

    def temperature_status(self) -> str:
        if self.temperature_c < 40: return "too low - add nitrogen"
        elif self.temperature_c > 65: return "too high - turn pile"
        return "optimal"

    def moisture_status(self) -> str:
        if self.moisture_pct < 40: return "too dry - add water"
        elif self.moisture_pct > 60: return "too wet - add browns"
        return "optimal"

    def cn_status(self) -> str:
        if self.carbon_nitrogen_ratio < 20: return "too low - add browns"
        elif self.carbon_nitrogen_ratio > 40: return "too high - add greens"
        return "optimal"

    def maturity_estimate(self, days: int) -> str:
        if days < 14: return "active phase"
        elif days < 30: return "curing phase"
        elif days < 60: return "maturing"
        return "mature"

    def turning_needed(self, days_since_turn: int) -> bool:
        return days_since_turn >= 3 and self.temperature_c > 55

    def stats(self) -> Dict:
        return {"temp": self.temperature_status(), "moisture": self.moisture_status(), "cn": self.cn_status(), "maturity": self.maturity_estimate(45)}

def run():
    cm = CompostMonitor(temperature_c=58, moisture_pct=45, carbon_nitrogen_ratio=25, ph=7.5)
    print(cm.stats())
    print("Turn needed:", cm.turning_needed(4))

if __name__ == "__main__":
    run()
