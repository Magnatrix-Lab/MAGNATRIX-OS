"""Sludge Processor -- dewatering, digestion, cake, volume reduction, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class SludgeProcessor:
    volume_m3: float = 100.0
    dry_solid_pct: float = 2.0
    target_dry_solid_pct: float = 20.0
    digestion_days: int = 20

    def dry_mass(self) -> float:
        return self.volume_m3 * self.dry_solid_pct / 100 * 1000

    def final_volume(self) -> float:
        return self.dry_mass() / (self.target_dry_solid_pct / 100) / 1000

    def volume_reduction(self) -> float:
        if self.volume_m3 == 0:
            return 0.0
        return (self.volume_m3 - self.final_volume()) / self.volume_m3

    def biogas_potential(self) -> float:
        return self.dry_mass() * 0.5 * 0.4

    def cake_weight(self) -> float:
        return self.dry_mass() / (self.target_dry_solid_pct / 100)

    def hauling_trips(self, truck_capacity_kg: float = 20000) -> int:
        return int(self.cake_weight() / truck_capacity_kg) + 1

    def stats(self) -> Dict:
        return {"dry_mass_kg": round(self.dry_mass(), 0), "final_volume": round(self.final_volume(), 1), "reduction": round(self.volume_reduction(), 3), "biogas_m3": round(self.biogas_potential(), 0)}

def run():
    sp = SludgeProcessor()
    print(sp.stats())
    print("Hauling trips:", sp.hauling_trips())

if __name__ == "__main__":
    run()
