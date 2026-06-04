"""Parking Allocator — space assignment, reservation, dynamic pricing, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum, auto
import time

@dataclass
class ParkingSpot:
    spot_id: str
    x: float
    y: float
    occupied: bool = False
    reserved: bool = False
    rate: float = 1.0
    vehicle_id: str = ""

class ParkingAllocator:
    def __init__(self):
        self.spots: Dict[str, ParkingSpot] = {}
        self.reservations: Dict[str, str] = {}
        self.revenue = 0.0

    def add_spot(self, spot: ParkingSpot):
        self.spots[spot.spot_id] = spot

    def find_nearest(self, x: float, y: float) -> Optional[str]:
        available = [s for s in self.spots.values() if not s.occupied and not s.reserved]
        if not available:
            return None
        nearest = min(available, key=lambda s: (s.x - x) ** 2 + (s.y - y) ** 2)
        return nearest.spot_id

    def allocate(self, vehicle_id: str, x: float, y: float, duration: float) -> Optional[str]:
        spot_id = self.find_nearest(x, y)
        if spot_id and spot_id not in self.reservations.values():
            spot = self.spots[spot_id]
            spot.occupied = True
            spot.vehicle_id = vehicle_id
            self.reservations[vehicle_id] = spot_id
            self.revenue += spot.rate * duration
            return spot_id
        return None

    def release(self, vehicle_id: str):
        spot_id = self.reservations.pop(vehicle_id, None)
        if spot_id:
            spot = self.spots[spot_id]
            spot.occupied = False
            spot.vehicle_id = ""

    def dynamic_price(self, demand_ratio: float):
        for spot in self.spots.values():
            spot.rate = max(0.5, spot.rate * (1 + demand_ratio * 0.5))

    def occupancy(self) -> float:
        total = len(self.spots)
        occupied = sum(1 for s in self.spots.values() if s.occupied)
        return occupied / total if total else 0

    def stats(self) -> Dict:
        return {"spots": len(self.spots), "occupied": sum(1 for s in self.spots.values() if s.occupied), "revenue": self.revenue, "occupancy": self.occupancy()}

def run():
    pa = ParkingAllocator()
    for i in range(20):
        pa.add_spot(ParkingSpot(f"S{i}", i*2, 0, rate=2.0))
    pa.allocate("V1", 5, 0, 2)
    pa.allocate("V2", 15, 0, 3)
    pa.dynamic_price(0.8)
    print(pa.stats())

if __name__ == "__main__":
    run()
