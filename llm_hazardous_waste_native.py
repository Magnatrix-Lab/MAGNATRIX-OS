"""Native stdlib module: Hazardous Waste Tracker
Tracks hazardous waste generation, storage, and disposal compliance.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class HazardClass(Enum):
    FLAMMABLE = "flammable"
    CORROSIVE = "corrosive"
    TOXIC = "toxic"
    REACTIVE = "reactive"
    BIOHAZARD = "biohazard"

@dataclass
class HazardousEntry:
    waste_id: str
    hazard_class: HazardClass
    weight_kg: float
    storage_days: int
    max_storage_days: int = 90

@dataclass
class HazardousWasteTracker:
    facility_name: str
    entries: List[HazardousEntry] = field(default_factory=list)

    def total_weight_kg(self) -> float:
        return sum(e.weight_kg for e in self.entries)

    def by_hazard_class(self) -> Dict[str, float]:
        totals = {}
        for e in self.entries:
            totals[e.hazard_class.value] = totals.get(e.hazard_class.value, 0) + e.weight_kg
        return totals

    def overdue_entries(self) -> List[str]:
        return [e.waste_id for e in self.entries if e.storage_days > e.max_storage_days]

    def compliance_pct(self) -> float:
        if not self.entries:
            return 100.0
        compliant = sum(1 for e in self.entries if e.storage_days <= e.max_storage_days)
        return (compliant / len(self.entries)) * 100

    def stats(self) -> Dict:
        return {
            "facility": self.facility_name,
            "total_weight_kg": round(self.total_weight_kg(), 1),
            "entries": len(self.entries),
            "overdue": self.overdue_entries(),
            "compliance_pct": round(self.compliance_pct(), 1),
            "by_hazard_class": {k: round(v, 1) for k, v in self.by_hazard_class().items()},
        }

def run():
    hwt = HazardousWasteTracker(
        facility_name="Chemical Plant",
        entries=[
            HazardousEntry("HW-001", HazardClass.FLAMMABLE, 50, 30, 90),
            HazardousEntry("HW-002", HazardClass.CORROSIVE, 30, 95, 90),
            HazardousEntry("HW-003", HazardClass.TOXIC, 20, 60, 90),
            HazardousEntry("HW-004", HazardClass.BIOHAZARD, 15, 45, 60),
        ]
    )
    print(hwt.stats())

if __name__ == "__main__":
    run()
