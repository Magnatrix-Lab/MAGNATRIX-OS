"""Disinfection Calculator -- CT, chlorine, UV, ozone, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class DisinfectionCalculator:
    pathogen: str = "giardia"
    method: str = "chlorine"
    temperature_c: float = 20.0
    ph: float = 7.0

    def ct_required(self) -> float:
        ct_table = {
            "giardia": {"chlorine": 100, "chloramine": 700, "ozone": 0.5, "uv": 30},
            "cryptosporidium": {"chlorine": 10000, "chloramine": 3000, "ozone": 5, "uv": 10},
            "virus": {"chlorine": 4, "chloramine": 800, "ozone": 0.1, "uv": 20},
        }
        base = ct_table.get(self.pathogen, {}).get(self.method, 100)
        if self.method == "chlorine":
            temp_factor = max(0.5, 1 - (self.temperature_c - 20) * 0.02)
            ph_factor = max(0.5, 1 - (self.ph - 7) * 0.1)
            return base * temp_factor * ph_factor
        return base

    def chlorine_dose(self, ct: float, contact_time_min: float) -> float:
        if contact_time_min <= 0:
            return 0.0
        return ct / contact_time_min

    def uv_dose_mj_cm2(self) -> float:
        doses = {"giardia": 10, "cryptosporidium": 10, "virus": 40}
        return doses.get(self.pathogen, 20)

    def inactivation_pct(self, actual_ct: float) -> float:
        required = self.ct_required()
        if required <= 0:
            return 0.0
        return min(99.999, (1 - math.exp(-actual_ct / required * 3)) * 100)

    def stats(self, contact_time_min: float = 30) -> Dict:
        ct = self.ct_required()
        return {"ct_required": ct, "chlorine_dose_mg_l": round(self.chlorine_dose(ct, contact_time_min), 2), "uv_dose": self.uv_dose_mj_cm2(), "inactivation": round(self.inactivation_pct(ct), 3)}

def run():
    dc = DisinfectionCalculator("giardia", "chlorine")
    print(dc.stats())
    dc2 = DisinfectionCalculator("virus", "uv")
    print(dc2.stats())

if __name__ == "__main__":
    run()
