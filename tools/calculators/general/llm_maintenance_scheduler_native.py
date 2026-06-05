"""Maintenance Scheduler — interval, predictive, downtime, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class MaintenanceTask:
    name: str
    interval_km: float
    last_km: float
    duration_hours: float
    cost: float

class MaintenanceScheduler:
    def __init__(self):
        self.tasks: List[MaintenanceTask] = []
        self.current_km: float = 0.0

    def add_task(self, t: MaintenanceTask):
        self.tasks.append(t)

    def due_tasks(self) -> List[MaintenanceTask]:
        return [t for t in self.tasks if self.current_km - t.last_km >= t.interval_km]

    def next_due(self) -> Optional[MaintenanceTask]:
        due = self.due_tasks()
        return due[0] if due else None

    def km_to_next(self, task_name: str) -> float:
        t = next((x for x in self.tasks if x.name == task_name), None)
        if not t:
            return float('inf')
        return max(0, t.interval_km - (self.current_km - t.last_km))

    def total_cost(self, period_km: float) -> float:
        cost = 0.0
        for t in self.tasks:
            times = int(period_km / t.interval_km) if t.interval_km > 0 else 0
            cost += times * t.cost
        return cost

    def downtime(self, period_km: float) -> float:
        hours = 0.0
        for t in self.tasks:
            times = int(period_km / t.interval_km) if t.interval_km > 0 else 0
            hours += times * t.duration_hours
        return hours

    def stats(self) -> Dict:
        return {
            "due_now": len(self.due_tasks()),
            "next_task": self.next_due().name if self.next_due() else None,
            "total_cost_10k": round(self.total_cost(10000), 2)
        }

def run():
    ms = MaintenanceScheduler(current_km=50000)
    ms.add_task(MaintenanceTask("Oil", 10000, 45000, 1, 50))
    ms.add_task(MaintenanceTask("Tires", 20000, 35000, 2, 400))
    ms.add_task(MaintenanceTask("Brakes", 30000, 25000, 3, 300))
    print(ms.stats())
    print("KM to oil change:", ms.km_to_next("Oil"))

if __name__ == "__main__":
    run()
