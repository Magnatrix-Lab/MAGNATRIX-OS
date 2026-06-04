"""Warehouse Optimizer — slotting, pick path, zone balancing, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

@dataclass
class WarehouseSlot:
    slot_id: str
    x: float
    y: float
    capacity: int
    items: Dict[str, int] = field(default_factory=dict)

class WarehouseOptimizer:
    def __init__(self, width: float = 100, height: float = 100):
        self.width = width
        self.height = height
        self.slots: Dict[str, WarehouseSlot] = {}
        self.dock = (0.0, 0.0)
        self.item_velocity: Dict[str, float] = {}

    def add_slot(self, slot: WarehouseSlot):
        self.slots[slot.slot_id] = slot

    def assign_item(self, item_id: str, quantity: int, velocity: float = 1.0):
        self.item_velocity[item_id] = velocity
        # Assign to closest slot with capacity
        candidates = sorted(self.slots.values(), key=lambda s: self._distance(s, self.dock))
        for slot in candidates:
            total = sum(slot.items.values())
            if total + quantity <= slot.capacity:
                slot.items[item_id] = slot.items.get(item_id, 0) + quantity
                return slot.slot_id
        return None

    def _distance(self, slot: WarehouseSlot, point: Tuple[float, float]) -> float:
        return math.sqrt((slot.x - point[0]) ** 2 + (slot.y - point[1]) ** 2)

    def optimize_layout(self):
        # Move high-velocity items closer to dock
        for slot in self.slots.values():
            for item_id, qty in list(slot.items.items()):
                vel = self.item_velocity.get(item_id, 0)
                if vel > 5:
                    closer = min(self.slots.values(), key=lambda s: self._distance(s, self.dock) if s != slot else float('inf'))
                    if closer and closer != slot:
                        total = sum(closer.items.values())
                        if total + qty <= closer.capacity:
                            closer.items[item_id] = closer.items.get(item_id, 0) + qty
                            del slot.items[item_id]

    def pick_path(self, items: List[str]) -> List[str]:
        # Greedy nearest neighbor TSP
        slots_needed = set()
        for item_id in items:
            for sid, slot in self.slots.items():
                if item_id in slot.items and slot.items[item_id] > 0:
                    slots_needed.add(sid)
        path = []
        current = self.dock
        remaining = set(slots_needed)
        while remaining:
            nearest = min(remaining, key=lambda sid: math.sqrt((self.slots[sid].x - current[0])**2 + (self.slots[sid].y - current[1])**2))
            path.append(nearest)
            current = (self.slots[nearest].x, self.slots[nearest].y)
            remaining.remove(nearest)
        return path

    def stats(self) -> Dict:
        return {"slots": len(self.slots), "capacity_used": sum(sum(s.items.values()) for s in self.slots.values())}

def run():
    wh = WarehouseOptimizer(50, 50)
    for i in range(10):
        wh.add_slot(WarehouseSlot(f"S{i}", i*5, i*3, 20))
    wh.assign_item("A", 10, 10)
    wh.assign_item("B", 5, 1)
    wh.optimize_layout()
    print("Pick path:", wh.pick_path(["A", "B"]))
    print(wh.stats())

if __name__ == "__main__":
    run()
