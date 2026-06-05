"""Latency Analyzer — RTT, jitter, packet loss, MOS, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class LatencyAnalyzer:
    rtt_samples: List[float] = field(default_factory=list)
    packet_loss_pct: float = 0.0

    def avg_rtt(self) -> float:
        return sum(self.rtt_samples) / len(self.rtt_samples) if self.rtt_samples else 0.0

    def jitter(self) -> float:
        if len(self.rtt_samples) < 2:
            return 0.0
        diffs = [abs(self.rtt_samples[i] - self.rtt_samples[i-1]) for i in range(1, len(self.rtt_samples))]
        return sum(diffs) / len(diffs)

    def mos_score(self, codec_factor: float = 1.0) -> float:
        """MOS score approximation."""
        rtt = self.avg_rtt()
        jitter = self.jitter()
        loss = self.packet_loss_pct
        r = rtt + jitter * 2 + loss * 10
        if r < 150:
            return 4.5 - r / 300
        elif r < 300:
            return 4.0 - (r - 150) / 300
        elif r < 450:
            return 3.0 - (r - 300) / 150
        return max(1.0, 1.0 - (r - 450) / 100)

    def qos_rating(self) -> str:
        mos = self.mos_score()
        if mos >= 4.0: return "excellent"
        elif mos >= 3.5: return "good"
        elif mos >= 3.0: return "fair"
        elif mos >= 2.0: return "poor"
        return "unacceptable"

    def stats(self) -> Dict:
        return {
            "avg_rtt": round(self.avg_rtt(), 1),
            "jitter": round(self.jitter(), 1),
            "packet_loss": self.packet_loss_pct,
            "mos": round(self.mos_score(), 2),
            "qos": self.qos_rating()
        }

def run():
    la = LatencyAnalyzer([50, 55, 52, 60, 58, 53], packet_loss_pct=0.5)
    print(la.stats())

if __name__ == "__main__":
    run()
