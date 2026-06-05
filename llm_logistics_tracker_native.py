"""Logistics Tracker — shipment, ETA, delay, route status, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class Shipment:
    id: str
    origin: Tuple[float, float]
    destination: Tuple[float, float]
    speed: float
    status: str = "in_transit"
    distance_traveled: float = 0.0

class LogisticsTracker:
    def __init__(self):
        self.shipments: List[Shipment] = []

    def add_shipment(self, s: Shipment):
        self.shipments.append(s)

    def total_distance(self, s: Shipment) -> float:
        lat1, lon1 = s.origin
        lat2, lon2 = s.destination
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        return 2 * 6371 * math.asin(min(1, math.sqrt(a)))

    def eta(self, s: Shipment) -> float:
        remaining = self.total_distance(s) - s.distance_traveled
        return remaining / s.speed if s.speed > 0 else float('inf')

    def progress_pct(self, s: Shipment) -> float:
        total = self.total_distance(s)
        return s.distance_traveled / total if total > 0 else 0.0

    def delayed(self, threshold_hours: float = 2.0) -> List[Shipment]:
        return [s for s in self.shipments if self.eta(s) > threshold_hours and s.status == "in_transit"]

    def stats(self) -> Dict:
        return {
            "shipments": len(self.shipments),
            "in_transit": sum(1 for s in self.shipments if s.status == "in_transit"),
            "delayed": len(self.delayed())
        }

def run():
    lt = LogisticsTracker()
    lt.add_shipment(Shipment("S1", (40.7, -74.0), (51.5, -0.1), 800, distance_traveled=4000))
    lt.add_shipment(Shipment("S2", (35.7, 139.7), (37.8, -122.4), 900, distance_traveled=200))
    print(lt.stats())
    for s in lt.shipments:
        print(f"{s.id}: {lt.progress_pct(s):.1%} ETA {lt.eta(s):.1f}h")

if __name__ == "__main__":
    run()
