"""Hotel Optimizer — occupancy, ADR, RevPAR, yield, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class HotelOptimizer:
    rooms: int = 100
    occupied: int = 70
    room_rate: float = 150.0
    operating_costs: float = 5000.0

    def occupancy_rate(self) -> float:
        return self.occupied / self.rooms if self.rooms > 0 else 0.0

    def adr(self) -> float:
        return self.room_rate

    def revpar(self) -> float:
        return self.occupancy_rate() * self.adr()

    def gop(self) -> float:
        return self.occupied * self.room_rate - self.operating_costs

    def yield_adjustment(self, demand_factor: float) -> float:
        return self.room_rate * (1 + demand_factor)

    def stats(self) -> Dict:
        return {
            "occupancy": round(self.occupancy_rate(), 3),
            "adr": self.adr(),
            "revpar": round(self.revpar(), 2),
            "gop": round(self.gop(), 2)
        }

def run():
    ho = HotelOptimizer(rooms=200, occupied=160, room_rate=180, operating_costs=15000)
    print(ho.stats())
    print("Adjusted rate:", ho.yield_adjustment(0.2))

if __name__ == "__main__":
    run()
