"""Irrigation Scheduler — ET-based, soil moisture, deficit, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class IrrigationScheduler:
    field_capacity: float = 0.3
    wilting_point: float = 0.1
    current_moisture: float = 0.25
    crop_factor: float = 1.0
    et0: float = 5.0

    def available_water(self) -> float:
        return self.field_capacity - self.wilting_point

    def depletion(self) -> float:
        return (self.field_capacity - self.current_moisture) / self.available_water()

    def et_crop(self) -> float:
        return self.et0 * self.crop_factor

    def need_irrigation(self, threshold: float = 0.5) -> bool:
        return self.depletion() > threshold

    def irrigation_amount(self, target: float = 0.8) -> float:
        target_moisture = self.wilting_point + target * self.available_water()
        return max(0, target_moisture - self.current_moisture)

    def schedule(self, days: int) -> List[float]:
        amounts = []
        for _ in range(days):
            self.current_moisture -= self.et_crop() / 100
            if self.need_irrigation(0.6):
                amt = self.irrigation_amount()
                self.current_moisture += amt
                amounts.append(amt)
            else:
                amounts.append(0)
        return amounts

    def stats(self) -> Dict:
        return {"moisture": round(self.current_moisture, 3), "depletion": round(self.depletion(), 3), "need": self.need_irrigation()}

def run():
    isr = IrrigationScheduler(current_moisture=0.18)
    print(isr.stats())
    print("Schedule:", isr.schedule(7))

if __name__ == "__main__":
    run()
