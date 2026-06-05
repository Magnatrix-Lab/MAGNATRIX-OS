"""Coffee Roast — development time, color, charge temp, rate of rise, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class CoffeeRoast:
    charge_temp: float = 200.0
    first_crack: float = 380.0
    drop_temp: float = 420.0
    development_time: float = 60.0

    def total_roast_time(self, ror: float = 10.0) -> float:
        return (self.drop_temp - self.charge_temp) / ror

    def development_ratio(self) -> float:
        total = self.total_roast_time()
        return self.development_time / total if total > 0 else 0.0

    def color_estimate(self) -> str:
        if self.drop_temp < 390: return "light"
        elif self.drop_temp < 410: return "medium"
        elif self.drop_temp < 430: return "medium-dark"
        return "dark"

    def agtron_estimate(self) -> int:
        return int(130 - (self.drop_temp - 350) * 0.5)

    def moisture_loss(self, initial: float = 12.0) -> float:
        return initial * (1 - (self.drop_temp - 350) / 300)

    def stats(self) -> Dict:
        return {"color": self.color_estimate(), "agtron": self.agtron_estimate(), "dev_ratio": round(self.development_ratio(), 3)}

def run():
    cr = CoffeeRoast(charge_temp=180, first_crack=395, drop_temp=415, development_time=45)
    print(cr.stats())
    print("Moisture loss:", cr.moisture_loss())

if __name__ == "__main__":
    run()
