"""Kiln Controller — firing curve, soak, ramp, cone, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class KilnController:
    target_temp: float = 1200.0
    ramp_rate: float = 100.0
    soak_time: float = 0.5
    cooling_rate: float = 50.0

    def time_to_target(self, start_temp: float = 25.0) -> float:
        return (self.target_temp - start_temp) / self.ramp_rate if self.ramp_rate > 0 else 0.0

    def total_cycle_time(self, start_temp: float = 25.0) -> float:
        heat = self.time_to_target(start_temp)
        cool = (self.target_temp - 100) / self.cooling_rate if self.cooling_rate > 0 else 0.0
        return heat + self.soak_time + cool

    def cone_equivalent(self) -> str:
        if self.target_temp < 1100: return "cone 010"
        elif self.target_temp < 1140: return "cone 06"
        elif self.target_temp < 1180: return "cone 04"
        elif self.target_temp < 1220: return "cone 1"
        elif self.target_temp < 1260: return "cone 6"
        elif self.target_temp < 1300: return "cone 10"
        return "cone 12+"

    def ramp_schedule(self, segments: int = 5) -> List[float]:
        step = (self.target_temp - 25) / segments
        return [25 + i * step for i in range(1, segments + 1)]

    def stats(self) -> Dict:
        return {"target": self.target_temp, "cone": self.cone_equivalent(), "cycle_time": round(self.total_cycle_time(), 1)}

def run():
    kc = KilnController(target_temp=1240, ramp_rate=150, soak_time=1)
    print(kc.stats())
    print("Ramp schedule:", kc.ramp_schedule())

if __name__ == "__main__":
    run()
