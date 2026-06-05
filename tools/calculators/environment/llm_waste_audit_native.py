"""Native stdlib module: Waste Audit Calculator
Calculates waste diversion rates, recycling percentages, and landfill volumes.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class WasteType(Enum):
    LANDFILL = "landfill"
    RECYCLING = "recycling"
    COMPOST = "compost"
    HAZARDOUS = "hazardous"
    E_WASTE = "e_waste"

@dataclass
class WasteStream:
    waste_type: WasteType
    weight_kg: float
    recyclable: bool = False

@dataclass
class WasteAuditCalculator:
    facility_name: str
    audit_period: str
    streams: List[WasteStream] = field(default_factory=list)

    def total_waste_kg(self) -> float:
        return sum(s.weight_kg for s in self.streams)

    def waste_by_type(self) -> Dict[str, float]:
        totals = {}
        for s in self.streams:
            totals[s.waste_type.value] = totals.get(s.waste_type.value, 0) + s.weight_kg
        return totals

    def diversion_rate_pct(self) -> float:
        diverted = sum(s.weight_kg for s in self.streams if s.waste_type in [WasteType.RECYCLING, WasteType.COMPOST, WasteType.E_WASTE])
        if self.total_waste_kg() == 0:
            return 0.0
        return (diverted / self.total_waste_kg()) * 100

    def landfill_rate_pct(self) -> float:
        return 100 - self.diversion_rate_pct()

    def recycling_rate_pct(self) -> float:
        if self.total_waste_kg() == 0:
            return 0.0
        recycled = sum(s.weight_kg for s in self.streams if s.waste_type == WasteType.RECYCLING)
        return (recycled / self.total_waste_kg()) * 100

    def stats(self) -> Dict:
        return {
            "facility": self.facility_name,
            "total_waste_kg": round(self.total_waste_kg(), 1),
            "diversion_rate_pct": round(self.diversion_rate_pct(), 1),
            "landfill_rate_pct": round(self.landfill_rate_pct(), 1),
            "recycling_rate_pct": round(self.recycling_rate_pct(), 1),
            "by_type": {k: round(v, 1) for k, v in self.waste_by_type().items()},
        }

def run():
    wa = WasteAuditCalculator(
        facility_name="Office Building A",
        audit_period="June 2024",
        streams=[
            WasteStream(WasteType.LANDFILL, 500),
            WasteStream(WasteType.RECYCLING, 350, True),
            WasteStream(WasteType.COMPOST, 120, True),
            WasteStream(WasteType.E_WASTE, 30, True),
        ]
    )
    print(wa.stats())

if __name__ == "__main__":
    run()
