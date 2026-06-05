"""Fleet Manager — dispatch, capacity, maintenance, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class Vehicle:
    id: str
    capacity: float
    current_load: float = 0.0
    mileage: float = 0.0
    status: str = "available"

class FleetManager:
    def __init__(self):
        self.vehicles: List[Vehicle] = []
        self.routes: Dict[str, List[str]] = {}

    def add_vehicle(self, v: Vehicle):
        self.vehicles.append(v)

    def available(self) -> List[Vehicle]:
        return [v for v in self.vehicles if v.status == "available"]

    def assign(self, vehicle_id: str, route: List[str], load: float) -> bool:
        v = next((x for x in self.vehicles if x.id == vehicle_id), None)
        if not v or v.status != "available" or v.capacity - v.current_load < load:
            return False
        v.current_load += load
        v.status = "assigned"
        self.routes[vehicle_id] = route
        return True

    def complete(self, vehicle_id: str, distance: float):
        v = next((x for x in self.vehicles if x.id == vehicle_id), None)
        if v:
            v.status = "available"
            v.current_load = 0
            v.mileage += distance

    def maintenance_due(self, threshold: float = 10000.0) -> List[str]:
        return [v.id for v in self.vehicles if v.mileage > threshold]

    def stats(self) -> Dict:
        return {"total": len(self.vehicles), "available": len(self.available()), "total_mileage": sum(v.mileage for v in self.vehicles)}

def run():
    fm = FleetManager()
    fm.add_vehicle(Vehicle("V1", 1000))
    fm.add_vehicle(Vehicle("V2", 1500))
    fm.assign("V1", ["A", "B", "C"], 800)
    print(fm.stats())
    print("Maintenance:", fm.maintenance_due(5000))

if __name__ == "__main__":
    run()
