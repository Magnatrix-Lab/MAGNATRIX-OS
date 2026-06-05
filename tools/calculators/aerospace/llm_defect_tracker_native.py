"""Native stdlib module: Defect Tracker
Tracks defect counts, Pareto analysis, and defect rates by category.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class Severity(Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    COSMETIC = "cosmetic"

@dataclass
class Defect:
    category: str
    severity: Severity
    count: int

@dataclass
class DefectTracker:
    product_name: str
    total_units_produced: int
    defects: List[Defect] = field(default_factory=list)

    def total_defects(self) -> int:
        return sum(d.count for d in self.defects)

    def defect_rate_ppm(self) -> float:
        if self.total_units_produced == 0:
            return 0.0
        return (self.total_defects() / self.total_units_produced) * 1_000_000

    def pareto(self) -> List[Dict]:
        total = self.total_defects()
        sorted_defects = sorted(self.defects, key=lambda d: d.count, reverse=True)
        cumulative = 0
        result = []
        for d in sorted_defects:
            cumulative += d.count
            result.append({
                "category": d.category,
                "count": d.count,
                "pct": round((d.count / max(1, total)) * 100, 1),
                "cumulative_pct": round((cumulative / max(1, total)) * 100, 1),
            })
        return result

    def by_severity(self) -> Dict[str, int]:
        counts = {}
        for d in self.defects:
            counts[d.severity.value] = counts.get(d.severity.value, 0) + d.count
        return counts

    def stats(self) -> Dict:
        return {
            "product": self.product_name,
            "total_defects": self.total_defects(),
            "defect_rate_ppm": round(self.defect_rate_ppm(), 1),
            "by_severity": self.by_severity(),
            "pareto_top": self.pareto()[:3],
        }

def run():
    dt = DefectTracker(
        product_name="Phone Case",
        total_units_produced=50000,
        defects=[
            Defect("scratch", Severity.COSMETIC, 120),
            Defect("dimension", Severity.MAJOR, 45),
            Defect("color", Severity.MINOR, 80),
            Defect("crack", Severity.CRITICAL, 15),
            Defect("flash", Severity.COSMETIC, 60),
        ]
    )
    print(dt.stats())

if __name__ == "__main__":
    run()
