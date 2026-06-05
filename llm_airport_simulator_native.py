"""Airport Simulator — gates, runways, capacity, delays, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class Flight:
    id: str
    arrival_time: float
    departure_time: float
    gate_needed: bool = True

class AirportSimulator:
    def __init__(self):
        self.gates: int = 10
        self.runways: int = 2
        self.flights: List[Flight] = []
        self.gate_schedule: Dict[int, List[Flight]] = {}

    def add_flight(self, f: Flight):
        self.flights.append(f)

    def gate_utilization(self) -> float:
        if not self.flights:
            return 0.0
        total_gate_time = sum(f.departure_time - f.arrival_time for f in self.flights if f.gate_needed)
        available = self.gates * 24
        return total_gate_time / available if available > 0 else 0.0

    def max_concurrent_flights(self) -> int:
        events = []
        for f in self.flights:
            events.append((f.arrival_time, 1))
            events.append((f.departure_time, -1))
        events.sort()
        max_count = 0
        current = 0
        for _, delta in events:
            current += delta
            max_count = max(max_count, current)
        return max_count

    def delay_probability(self, demand: int) -> float:
        if demand <= self.gates:
            return 0.0
        return min(1.0, (demand - self.gates) / self.gates)

    def runway_capacity(self, separation_min: float = 3.0) -> float:
        return self.runways * (60 / separation_min) * 24

    def stats(self) -> Dict:
        return {
            "flights": len(self.flights),
            "gate_util": round(self.gate_utilization(), 3),
            "max_concurrent": self.max_concurrent_flights(),
            "runway_capacity": self.runway_capacity()
        }

def run():
    aps = AirportSimulator()
    aps.add_flight(Flight("F1", 8, 10))
    aps.add_flight(Flight("F2", 9, 11))
    aps.add_flight(Flight("F3", 10, 12))
    aps.add_flight(Flight("F4", 11, 13))
    print(aps.stats())
    print("Delay prob:", aps.delay_probability(15))

if __name__ == "__main__":
    run()
