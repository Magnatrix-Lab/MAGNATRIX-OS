"""MES Scheduler — manufacturing orders, machine allocation, WIP tracking, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto
import time
from heapq import heappush, heappop

class MESScheduler:
    def __init__(self):
        self.machines: Dict[str, Dict] = {}
        self.orders: List[Dict] = []
        self.wip: Dict[str, Dict] = {}
        self.completed: List[str] = []

    def add_machine(self, machine_id: str, capacity: float, setup_time: float = 0):
        self.machines[machine_id] = {"capacity": capacity, "setup": setup_time, "available": 0, "queue": []}

    def add_order(self, order_id: str, product: str, quantity: float, steps: List[str], due: float):
        self.orders.append({"id": order_id, "product": product, "qty": quantity, "steps": steps, "due": due, "status": "pending"})

    def schedule(self):
        for order in sorted(self.orders, key=lambda o: o["due"]):
            for step in order["steps"]:
                available = [m for m, info in self.machines.items() if step in m or "general" in m]
                if available:
                    best = min(available, key=lambda m: self.machines[m]["available"])
                    finish = self.machines[best]["available"] + self.machines[best]["setup"] + order["qty"] / self.machines[best]["capacity"]
                    self.machines[best]["available"] = finish
                    self.machines[best]["queue"].append(order["id"])
            order["status"] = "scheduled"
            self.wip[order["id"]] = order

    def complete(self, order_id: str):
        if order_id in self.wip:
            self.wip[order_id]["status"] = "completed"
            self.completed.append(order_id)
            del self.wip[order_id]

    def stats(self) -> Dict:
        return {"machines": len(self.machines), "orders": len(self.orders), "wip": len(self.wip), "completed": len(self.completed)}

def run():
    mes = MESScheduler()
    mes.add_machine("M1-Cut", 10, 0.5)
    mes.add_machine("M2-Drill", 8, 0.3)
    mes.add_machine("M3-Assembly", 5, 1.0)
    mes.add_order("O1", "A", 50, ["M1-Cut", "M2-Drill"], time.time() + 86400)
    mes.add_order("O2", "B", 30, ["M1-Cut", "M3-Assembly"], time.time() + 43200)
    mes.schedule()
    print(mes.stats())

if __name__ == "__main__":
    run()
