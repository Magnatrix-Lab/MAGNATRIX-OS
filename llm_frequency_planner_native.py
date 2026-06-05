"""Frequency Planner — channel allocation, interference, reuse, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
import math

@dataclass
class FrequencyPlanner:
    channels: List[int] = field(default_factory=list)
    cell_size: float = 1.0
    reuse_factor: int = 7

    def co_channel_distance(self) -> float:
        return math.sqrt(3 * self.reuse_factor) * self.cell_size

    def carrier_to_interference(self, n: int = 4) -> float:
        d = self.co_channel_distance()
        if d <= 0 or self.cell_size <= 0:
            return 0.0
        return (d / self.cell_size) ** n / 6

    def allocate(self, cells: int) -> Dict[int, int]:
        allocation = {}
        for i in range(cells):
            allocation[i] = self.channels[i % len(self.channels)] if self.channels else i
        return allocation

    def interference_free(self, channel_a: int, channel_b: int, min_separation: int = 1) -> bool:
        return abs(channel_a - channel_b) >= min_separation

    def stats(self) -> Dict:
        return {"channels": len(self.channels), "reuse_distance": round(self.co_channel_distance(), 2), "c_i": round(self.carrier_to_interference(), 1)}

def run():
    fp = FrequencyPlanner(channels=[1,2,3,4,5,6,7], cell_size=2, reuse_factor=7)
    print(fp.stats())
    print("Allocation:", fp.allocate(10))
    print("Interference free 1-3:", fp.interference_free(1, 3))

if __name__ == "__main__":
    run()
