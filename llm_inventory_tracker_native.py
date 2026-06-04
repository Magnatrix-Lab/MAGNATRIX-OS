"""Inventory Tracker — stock levels, reorder alerts, FIFO/LIFO, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import time
from collections import deque

class InventoryMethod(Enum):
    FIFO = auto()
    LIFO = auto()

@dataclass
class StockItem:
    item_id: str
    name: str
    quantity: int
    unit_cost: float
    timestamp: float

class InventoryTracker:
    def __init__(self, method: InventoryMethod = InventoryMethod.FIFO):
        self.method = method
        self.inventory: Dict[str, deque] = {}
        self.reorder_points: Dict[str, int] = {}
        self.alerts: List[Dict] = []

    def add_stock(self, item_id: str, name: str, quantity: int, unit_cost: float):
        if item_id not in self.inventory:
            self.inventory[item_id] = deque()
        self.inventory[item_id].append(StockItem(item_id, name, quantity, unit_cost, time.time()))

    def consume(self, item_id: str, quantity: int) -> List[StockItem]:
        if item_id not in self.inventory or not self.inventory[item_id]:
            return []
        consumed = []
        remaining = quantity
        while remaining > 0 and self.inventory[item_id]:
            if self.method == InventoryMethod.FIFO:
                batch = self.inventory[item_id][0]
            else:
                batch = self.inventory[item_id][-1]
            take = min(remaining, batch.quantity)
            consumed.append(StockItem(batch.item_id, batch.name, take, batch.unit_cost, batch.timestamp))
            batch.quantity -= take
            remaining -= take
            if batch.quantity == 0:
                if self.method == InventoryMethod.FIFO:
                    self.inventory[item_id].popleft()
                else:
                    self.inventory[item_id].pop()
        self._check_reorder(item_id)
        return consumed

    def set_reorder_point(self, item_id: str, threshold: int):
        self.reorder_points[item_id] = threshold

    def _check_reorder(self, item_id: str):
        total = sum(b.quantity for b in self.inventory.get(item_id, []))
        threshold = self.reorder_points.get(item_id, 0)
        if total <= threshold:
            self.alerts.append({"item_id": item_id, "level": total, "threshold": threshold, "time": time.time()})

    def get_total(self, item_id: str) -> int:
        return sum(b.quantity for b in self.inventory.get(item_id, []))

    def get_value(self, item_id: str) -> float:
        return sum(b.quantity * b.unit_cost for b in self.inventory.get(item_id, []))

    def stats(self) -> Dict:
        return {"items": len(self.inventory), "alerts": len(self.alerts), "method": self.method.name}

def run():
    inv = InventoryTracker(InventoryMethod.FIFO)
    inv.add_stock("A001", "Widget", 100, 5.0)
    inv.add_stock("A001", "Widget", 50, 6.0)
    inv.set_reorder_point("A001", 30)
    consumed = inv.consume("A001", 80)
    print("Consumed:", sum(c.quantity for c in consumed), "Remaining:", inv.get_total("A001"))
    print(inv.stats())

if __name__ == "__main__":
    run()
