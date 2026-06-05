"""IV Calculator — drip rate, infusion time, volume, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class IVCalculator:
    total_volume_ml: float = 1000.0
    time_hours: float = 8.0
    drop_factor: float = 20.0
    """gtt/ml"""
    pump_rate_ml_hr: float = 0.0

    def drip_rate_gtt_min(self) -> float:
        if self.time_hours <= 0:
            return 0.0
        return (self.total_volume_ml * self.drop_factor) / (self.time_hours * 60)

    def ml_per_hour(self) -> float:
        if self.time_hours <= 0:
            return 0.0
        return self.total_volume_ml / self.time_hours

    def infusion_time(self, rate_ml_hr: float) -> float:
        if rate_ml_hr <= 0:
            return float('inf')
        return self.total_volume_ml / rate_ml_hr

    def remaining_volume(self, infused_ml: float) -> float:
        return max(0, self.total_volume_ml - infused_ml)

    def time_remaining(self, infused_ml: float, rate_ml_hr: float) -> float:
        return self.remaining_volume(infused_ml) / rate_ml_hr if rate_ml_hr > 0 else 0.0

    def macro_micro_check(self, rate_ml_hr: float) -> str:
        if rate_ml_hr > 100: return "macro drip suitable"
        elif rate_ml_hr < 10: return "micro drip required"
        return "either macro or micro"

    def stats(self, rate_ml_hr: float = None) -> Dict:
        r = rate_ml_hr or self.ml_per_hour()
        return {
            "drip_rate": round(self.drip_rate_gtt_min(), 1),
            "ml_per_hour": round(self.ml_per_hour(), 1),
            "infusion_time": round(self.infusion_time(r), 2) if r > 0 else None
        }

def run():
    iv = IVCalculator(total_volume_ml=500, time_hours=4, drop_factor=15)
    print(iv.stats())
    print("Macro/micro check:", iv.macro_micro_check(8))
    print("Time remaining 200ml at 125ml/hr:", iv.time_remaining(200, 125))

if __name__ == "__main__":
    run()
