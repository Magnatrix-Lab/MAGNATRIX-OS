"""Revenue Manager — ADR, RevPAR, occupancy, pricing, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class RevenueManager:
    rooms_total: int = 100
    rooms_sold: int = 70
    revenue: float = 7000.0

    def occupancy_rate(self) -> float:
        return self.rooms_sold / self.rooms_total if self.rooms_total > 0 else 0.0

    def adr(self) -> float:
        return self.revenue / self.rooms_sold if self.rooms_sold > 0 else 0.0

    def revpar(self) -> float:
        return self.revenue / self.rooms_total if self.rooms_total > 0 else 0.0

    def yield_rate(self, max_rate: float) -> float:
        return self.revpar() / max_rate if max_rate > 0 else 0.0

    def dynamic_price(self, demand_factor: float, comp_rate: float) -> float:
        base = self.adr()
        return base * (1 + demand_factor * 0.2) * (comp_rate / base) ** 0.5

    def length_of_stay_adjustment(self, los: int) -> float:
        if los >= 7: return 0.9
        elif los >= 3: return 0.95
        return 1.0

    def stats(self) -> Dict:
        return {"occupancy": round(self.occupancy_rate(), 3), "adr": round(self.adr(), 2), "revpar": round(self.revpar(), 2)}

def run():
    rm = RevenueManager(rooms_total=150, rooms_sold=120, revenue=18000)
    print(rm.stats())
    print("Dynamic price:", rm.dynamic_price(1.2, 180))

if __name__ == "__main__":
    run()
