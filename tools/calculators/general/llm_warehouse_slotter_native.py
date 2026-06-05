"""Native stdlib module: Warehouse Slotter
Optimizes warehouse slot assignments by item velocity, size, and zone.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class Zone(Enum):
    A = "a"
    B = "b"
    C = "c"

@dataclass
class SKU:
    sku_id: str
    picks_per_month: int
    volume_m3: float
    weight_kg: float

@dataclass
class WarehouseSlotter:
    warehouse_name: str
    skus: List[SKU] = field(default_factory=list)
    a_zone_capacity: int = 20
    b_zone_capacity: int = 40
    c_zone_capacity: int = 100

    def _abc_class(self, sku: SKU) -> Zone:
        total_picks = sum(s.picks_per_month for s in self.skus)
        if total_picks == 0:
            return Zone.C
        sku_pct = sku.picks_per_month / total_picks
        if sku_pct >= 0.05:
            return Zone.A
        elif sku_pct >= 0.02:
            return Zone.B
        return Zone.C

    def slot_assignments(self) -> Dict[str, str]:
        a_count = 0
        b_count = 0
        c_count = 0
        assignments = {}
        for sku in sorted(self.skus, key=lambda s: s.picks_per_month, reverse=True):
            zone = self._abc_class(sku)
            if zone == Zone.A and a_count < self.a_zone_capacity:
                a_count += 1
                assignments[sku.sku_id] = "A"
            elif zone == Zone.B and b_count < self.b_zone_capacity:
                b_count += 1
                assignments[sku.sku_id] = "B"
            elif c_count < self.c_zone_capacity:
                c_count += 1
                assignments[sku.sku_id] = "C"
            else:
                assignments[sku.sku_id] = "overflow"
        return assignments

    def stats(self) -> Dict:
        zones = {"A": 0, "B": 0, "C": 0, "overflow": 0}
        for z in self.slot_assignments().values():
            zones[z] = zones.get(z, 0) + 1
        return {
            "warehouse": self.warehouse_name,
            "total_skus": len(self.skus),
            "zone_distribution": zones,
        }

def run():
    ws = WarehouseSlotter(
        warehouse_name="Central DC",
        skus=[
            SKU("SKU-001", 500, 0.5, 2.0),
            SKU("SKU-002", 300, 0.3, 1.5),
            SKU("SKU-003", 150, 1.2, 5.0),
            SKU("SKU-004", 80, 0.8, 3.0),
            SKU("SKU-005", 40, 2.0, 10.0),
            SKU("SKU-006", 20, 0.1, 0.5),
        ]
    )
    print(ws.stats())

if __name__ == "__main__":
    run()
