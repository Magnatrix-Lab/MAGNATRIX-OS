"""Traffic Simulator — flow, density, shockwave, queue, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class TrafficSimulator:
    road_length: float = 1000.0
    lanes: int = 2
    free_flow_speed: float = 60.0
    jam_density: float = 150.0

    def greenshield(self, density: float) -> float:
        return self.free_flow_speed * (1 - density / self.jam_density)

    def flow(self, density: float) -> float:
        return density * self.greenshield(density)

    def capacity(self) -> float:
        return self.jam_density * self.free_flow_speed / 4

    def shockwave_speed(self, k1: float, k2: float) -> float:
        if k1 == k2:
            return 0.0
        q1 = self.flow(k1)
        q2 = self.flow(k2)
        return (q2 - q1) / (k2 - k1)

    def queue_delay(self, arrival_rate: float, service_rate: float, time: float) -> float:
        if arrival_rate >= service_rate:
            return float('inf')
        rho = arrival_rate / service_rate
        return rho / (service_rate * (1 - rho))

    def stats(self) -> Dict:
        return {"capacity": round(self.capacity(), 1), "free_flow": self.free_flow_speed}

def run():
    ts = TrafficSimulator()
    print(ts.stats())
    print("Speed at 50 veh/km:", ts.greenshield(50))
    print("Flow at 50:", ts.flow(50))

if __name__ == "__main__":
    run()
