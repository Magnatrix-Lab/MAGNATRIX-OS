"""Throughput Optimizer — bottleneck analysis, line balancing, OEE, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto

class ThroughputOptimizer:
    def __init__(self):
        self.stations: List[Dict] = []
        self.bottleneck = None

    def add_station(self, station_id: str, cycle_time: float, uptime: float = 1.0, quality_rate: float = 1.0):
        self.stations.append({"id": station_id, "cycle_time": cycle_time, "uptime": uptime, "quality": quality_rate, "oee": uptime * quality_rate * 1.0})

    def find_bottleneck(self) -> str:
        if not self.stations:
            return ""
        bottleneck = max(self.stations, key=lambda s: s["cycle_time"] / (s["oee"] + 1e-6))
        self.bottleneck = bottleneck["id"]
        return self.bottleneck

    def line_balance(self, target_takt: float) -> List[Dict]:
        improvements = []
        for s in self.stations:
            if s["cycle_time"] > target_takt:
                needed = s["cycle_time"] - target_takt
                improvements.append({"station": s["id"], "reduce_by": needed, "suggestion": "add_parallel_station"})
        return improvements

    def overall_oee(self) -> float:
        if not self.stations:
            return 0.0
        return sum(s["oee"] for s in self.stations) / len(self.stations)

    def throughput(self) -> float:
        if not self.stations:
            return 0.0
        bottleneck = max(self.stations, key=lambda s: s["cycle_time"] / (s["oee"] + 1e-6))
        return 1.0 / (bottleneck["cycle_time"] / (bottleneck["oee"] + 1e-6)) * 3600

    def stats(self) -> Dict:
        return {"stations": len(self.stations), "bottleneck": self.bottleneck, "oee": self.overall_oee(), "throughput": self.throughput()}

def run():
    to = ThroughputOptimizer()
    to.add_station("S1", 2.0, 0.95, 0.99)
    to.add_station("S2", 3.0, 0.90, 0.98)
    to.add_station("S3", 2.5, 0.92, 0.97)
    print("Bottleneck:", to.find_bottleneck())
    print("Balance:", to.line_balance(2.0))
    print(to.stats())

if __name__ == "__main__":
    run()
