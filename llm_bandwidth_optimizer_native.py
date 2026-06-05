"""Bandwidth Optimizer — throughput, QoS, shaping, scheduling, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class Flow:
    id: str
    priority: int
    rate_mbps: float
    burst_size: float

class BandwidthOptimizer:
    def __init__(self):
        self.total_bw: float = 1000.0
        self.flows: List[Flow] = []

    def add_flow(self, f: Flow):
        self.flows.append(f)

    def allocated_bw(self, fair: bool = True) -> Dict[str, float]:
        if fair:
            total_weight = sum(1 / f.priority for f in self.flows) if self.flows else 1
            return {f.id: (self.total_bw / f.priority) / total_weight for f in self.flows}
        else:
            return {f.id: self.total_bw / len(self.flows) for f in self.flows} if self.flows else {}

    def utilization(self) -> float:
        total = sum(f.rate_mbps for f in self.flows)
        return total / self.total_bw if self.total_bw > 0 else 0.0

    def qos_violations(self) -> List[str]:
        alloc = self.allocated_bw()
        return [f.id for f in self.flows if f.rate_mbps > alloc.get(f.id, 0)]

    def shaping_needed(self, max_util: float = 0.8) -> bool:
        return self.utilization() > max_util

    def stats(self) -> Dict:
        return {
            "total_bw": self.total_bw,
            "utilization": round(self.utilization(), 3),
            "violations": len(self.qos_violations()),
            "shaping_needed": self.shaping_needed()
        }

def run():
    bo = BandwidthOptimizer()
    bo.add_flow(Flow("VoIP", 1, 10, 5))
    bo.add_flow(Flow("Video", 2, 100, 50))
    bo.add_flow(Flow("Web", 3, 500, 200))
    print(bo.stats())
    print("Allocation:", bo.allocated_bw())

if __name__ == "__main__":
    run()
