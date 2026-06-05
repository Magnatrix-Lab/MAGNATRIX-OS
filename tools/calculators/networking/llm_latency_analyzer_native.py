"""Latency Analyzer — RTT, jitter, propagation, queuing, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class LatencyAnalyzer:
    distances_km: List[float] = field(default_factory=list)
    propagation_speed: float = 200000.0
    """km/s in fiber"""
    packet_size: float = 1500.0
    bandwidth: float = 1000.0

    def propagation_delay(self, distance: float) -> float:
        return distance / self.propagation_speed if self.propagation_speed > 0 else 0.0

    def transmission_delay(self) -> float:
        return (self.packet_size * 8) / (self.bandwidth * 1000) if self.bandwidth > 0 else 0.0

    def total_rtt(self, distance: float) -> float:
        return 2 * (self.propagation_delay(distance) + self.transmission_delay())

    def jitter(self, rtts: List[float]) -> float:
        if len(rtts) < 2:
            return 0.0
        avg = sum(rtts) / len(rtts)
        return sum(abs(r - avg) for r in rtts) / len(rtts)

    def sla_compliance(self, measured: List[float], target: float) -> float:
        if not measured:
            return 0.0
        compliant = sum(1 for m in measured if m <= target)
        return compliant / len(measured)

    def stats(self, distance: float) -> Dict:
        return {"propagation": round(self.propagation_delay(distance) * 1000, 2), "transmission": round(self.transmission_delay() * 1000, 2), "rtt": round(self.total_rtt(distance) * 1000, 2)}

def run():
    la = LatencyAnalyzer(bandwidth=1000)
    print(la.stats(5000))
    print("Jitter:", la.jitter([10, 12, 11, 15, 13]))
    print("SLA 99% at 15ms:", la.sla_compliance([10, 12, 11, 15, 13], 15))

if __name__ == "__main__":
    run()
