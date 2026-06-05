"""Native stdlib module: Mushroom Yield Tracker
Tracks biological efficiency, flush yields, and revenue per batch.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class FlushRecord:
    flush_number: int
    yield_kg: float
    days_after_bagging: int

@dataclass
class MushroomYieldTracker:
    batch_id: str
    species: str
    substrate_dry_weight_kg: float
    flushes: List[FlushRecord] = field(default_factory=list)
    price_per_kg: float = 0.0

    def total_yield_kg(self) -> float:
        return sum(f.yield_kg for f in self.flushes)

    def biological_efficiency_pct(self) -> float:
        if self.substrate_dry_weight_kg == 0:
            return 0.0
        return (self.total_yield_kg() / self.substrate_dry_weight_kg) * 100

    def avg_yield_per_flush(self) -> float:
        if not self.flushes:
            return 0.0
        return self.total_yield_kg() / len(self.flushes)

    def revenue(self) -> float:
        return self.total_yield_kg() * self.price_per_kg

    def flush_count(self) -> int:
        return len(self.flushes)

    def stats(self) -> Dict:
        return {
            "batch": self.batch_id,
            "species": self.species,
            "total_yield_kg": round(self.total_yield_kg(), 1),
            "biological_efficiency_pct": round(self.biological_efficiency_pct(), 1),
            "avg_per_flush_kg": round(self.avg_yield_per_flush(), 1),
            "flush_count": self.flush_count(),
            "revenue": round(self.revenue(), 2) if self.price_per_kg else None,
        }

def run():
    myt = MushroomYieldTracker(
        batch_id="B-2024-06",
        species="Oyster",
        substrate_dry_weight_kg=50,
        price_per_kg=8,
        flushes=[
            FlushRecord(1, 18, 14),
            FlushRecord(2, 12, 21),
            FlushRecord(3, 8, 28),
        ]
    )
    print(myt.stats())

if __name__ == "__main__":
    run()
