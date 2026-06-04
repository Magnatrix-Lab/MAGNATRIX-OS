"""Order Fulfillment — order splitting, batching, priority queue, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import time
from heapq import heappush, heappop

class OrderPriority(Enum):
    STANDARD = 3
    EXPRESS = 2
    URGENT = 1

@dataclass
class Order:
    order_id: str
    items: Dict[str, int]
    priority: OrderPriority
    created_at: float
    status: str = "pending"

class OrderFulfillment:
    def __init__(self):
        self.orders: List[Order] = []
        self.queue = []
        self.inventory: Dict[str, int] = {}
        self.fulfilled: List[str] = []
        self.backorders: List[str] = []

    def add_inventory(self, item_id: str, quantity: int):
        self.inventory[item_id] = self.inventory.get(item_id, 0) + quantity

    def place_order(self, order: Order):
        self.orders.append(order)
        heappush(self.queue, (order.priority.value, order.created_at, order.order_id))

    def fulfill(self) -> List[str]:
        fulfilled_now = []
        while self.queue:
            _, _, order_id = heappop(self.queue)
            order = next((o for o in self.orders if o.order_id == order_id), None)
            if not order or order.status != "pending":
                continue
            can_fulfill = all(self.inventory.get(item, 0) >= qty for item, qty in order.items.items())
            if can_fulfill:
                for item, qty in order.items.items():
                    self.inventory[item] -= qty
                order.status = "fulfilled"
                self.fulfilled.append(order_id)
                fulfilled_now.append(order_id)
            else:
                order.status = "backordered"
                self.backorders.append(order_id)
        return fulfilled_now

    def stats(self) -> Dict:
        return {"orders": len(self.orders), "fulfilled": len(self.fulfilled), "backorders": len(self.backorders), "inventory": len(self.inventory)}

def run():
    of = OrderFulfillment()
    of.add_inventory("A", 100)
    of.add_inventory("B", 50)
    of.place_order(Order("O1", {"A": 10, "B": 5}, OrderPriority.STANDARD, time.time()))
    of.place_order(Order("O2", {"A": 200}, OrderPriority.URGENT, time.time()))
    of.place_order(Order("O3", {"A": 20, "B": 10}, OrderPriority.EXPRESS, time.time()))
    fulfilled = of.fulfill()
    print("Fulfilled:", fulfilled, "Backorders:", of.backorders)
    print(of.stats())

if __name__ == "__main__":
    run()
