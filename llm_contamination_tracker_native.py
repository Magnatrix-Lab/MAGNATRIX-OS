"""Native stdlib module: Contamination Tracker
Tracks contamination rates, sources, and prevention effectiveness.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class ContaminationType(Enum):
    GREEN_MOLD = "green_mold"
    BLACK_MOLD = "black_mold"
    BACTERIA = "bacteria"
    YEAST = "yeast"
    DRY_BUBBLE = "dry_bubble"

@dataclass
class BatchRecord:
    batch_id: str
    total_bags: int
    contaminated_bags: int
    contamination_type: ContaminationType

@dataclass
class ContaminationTracker:
    farm_name: str
    batches: List[BatchRecord] = field(default_factory=list)

    def total_bags(self) -> int:
        return sum(b.total_bags for b in self.batches)

    def total_contaminated(self) -> int:
        return sum(b.contaminated_bags for b in self.batches)

    def contamination_rate_pct(self) -> float:
        if self.total_bags() == 0:
            return 0.0
        return (self.total_contaminated() / self.total_bags()) * 100

    def by_type(self) -> Dict[str, int]:
        counts = {}
        for b in self.batches:
            counts[b.contamination_type.value] = counts.get(b.contamination_type.value, 0) + b.contaminated_bags
        return counts

    def clean_rate_pct(self) -> float:
        return 100 - self.contamination_rate_pct()

    def stats(self) -> Dict:
        return {
            "farm": self.farm_name,
            "total_batches": len(self.batches),
            "total_bags": self.total_bags(),
            "contaminated": self.total_contaminated(),
            "contamination_rate_pct": round(self.contamination_rate_pct(), 2),
            "clean_rate_pct": round(self.clean_rate_pct(), 2),
            "by_type": self.by_type(),
        }

def run():
    ct = ContaminationTracker(
        farm_name="Mushroom Farm",
        batches=[
            BatchRecord("B001", 100, 5, ContaminationType.GREEN_MOLD),
            BatchRecord("B002", 100, 3, ContaminationType.GREEN_MOLD),
            BatchRecord("B003", 100, 2, ContaminationType.BACTERIA),
            BatchRecord("B004", 100, 1, ContaminationType.YEAST),
        ]
    )
    print(ct.stats())

if __name__ == "__main__":
    run()
