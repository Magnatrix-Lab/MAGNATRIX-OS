"""Bandwidth Estimator - Throughput calculation for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict
import time

@dataclass
class BandwidthEstimator:
    window_size: float = 1.0
    samples: List[Dict] = field(default_factory=list)

    def record(self, bytes_transferred: int) -> None:
        self.samples.append({"timestamp": time.time(), "bytes": bytes_transferred})
        cutoff = time.time() - self.window_size
        self.samples = [s for s in self.samples if s["timestamp"] > cutoff]

    def estimate(self) -> float:
        if not self.samples: return 0.0
        total = sum(s["bytes"] for s in self.samples)
        duration = self.samples[-1]["timestamp"] - self.samples[0]["timestamp"] if len(self.samples) > 1 else self.window_size
        return total / max(duration, 0.001)

    def stats(self) -> dict:
        return {"bps": round(self.estimate(), 2), "samples": len(self.samples)}

def run():
    be = BandwidthEstimator(5.0)
    for b in [1000, 2000, 1500]:
        be.record(b)
    print("Bandwidth:", round(be.estimate(), 2))
    print("Stats:", be.stats())

if __name__ == "__main__": run()
