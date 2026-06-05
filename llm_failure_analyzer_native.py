"""Native stdlib module: Failure Analyzer
Analyzes failure data by MTBF, MTTR, and availability.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class FailureRecord:
    component: str
    downtime_hours: float
    repair_hours: float

@dataclass
class FailureAnalyzer:
    system_name: str
    operating_hours: float
    records: List[FailureRecord] = field(default_factory=list)

    def total_failures(self) -> int:
        return len(self.records)

    def mtbf(self) -> float:
        if len(self.records) == 0:
            return self.operating_hours
        return self.operating_hours / len(self.records)

    def mttr(self) -> float:
        if not self.records:
            return 0.0
        return sum(r.repair_hours for r in self.records) / len(self.records)

    def availability(self) -> float:
        total_downtime = sum(r.downtime_hours for r in self.records)
        if self.operating_hours + total_downtime == 0:
            return 1.0
        return self.operating_hours / (self.operating_hours + total_downtime)

    def by_component(self) -> Dict[str, int]:
        counts = {}
        for r in self.records:
            counts[r.component] = counts.get(r.component, 0) + 1
        return counts

    def stats(self) -> Dict:
        return {
            "system": self.system_name,
            "total_failures": self.total_failures(),
            "mtbf_hours": round(self.mtbf(), 1),
            "mttr_hours": round(self.mttr(), 1),
            "availability_pct": round(self.availability() * 100, 2),
            "by_component": self.by_component(),
        }

def run():
    fa = FailureAnalyzer(
        system_name="Web Server Cluster",
        operating_hours=8760,
        records=[
            FailureRecord("disk", 4, 2),
            FailureRecord("memory", 2, 1),
            FailureRecord("disk", 6, 3),
            FailureRecord("network", 1, 0.5),
            FailureRecord("power", 8, 4),
        ]
    )
    print(fa.stats())

if __name__ == "__main__":
    run()
