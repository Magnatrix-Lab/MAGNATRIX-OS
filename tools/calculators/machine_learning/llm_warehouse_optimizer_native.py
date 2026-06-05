"""Warehouse Optimizer — slotting, picking path, zone balancing, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class WarehouseOptimizer:
    slots: Dict[str, Tuple[int, int]] = field(default_factory=dict)
    """slot_id -> (x, y)"""
    items: Dict[str, str] = field(default_factory=dict)
    """item_id -> slot_id"""

    def add_slot(self, slot: str, x: int, y: int):
        self.slots[slot] = (x, y)

    def place_item(self, item: str, slot: str):
        self.items[item] = slot

    def distance(self, s1: str, s2: str) -> float:
        a = self.slots.get(s1, (0, 0))
        b = self.slots.get(s2, (0, 0))
        return abs(a[0]-b[0]) + abs(a[1]-b[1])

    def picking_path(self, items: List[str], start: str = "dock") -> List[str]:
        remaining = [self.items[i] for i in items if i in self.items]
        path = [start]
        while remaining:
            current = path[-1]
            nearest = min(remaining, key=lambda s: self.distance(current, s))
            path.append(nearest)
            remaining.remove(nearest)
        path.append(start)
        return path

    def zone_balance(self, zones: Dict[str, List[str]]) -> Dict[str, int]:
        return {z: len(slots) for z, slots in zones.items()}

    def stats(self) -> Dict:
        return {"slots": len(self.slots), "items": len(self.items)}

def run():
    wo = WarehouseOptimizer()
    for i in range(5):
        for j in range(5):
            wo.add_slot(f"S{i}-{j}", i, j)
    wo.place_item("A", "S0-0")
    wo.place_item("B", "S2-3")
    wo.place_item("C", "S4-4")
    print(wo.picking_path(["A", "B", "C"]))
    print(wo.stats())

if __name__ == "__main__":
    run()
