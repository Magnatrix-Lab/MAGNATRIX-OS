"""Bandwidth Calculator — Shannon, Nyquist, throughput, utilization, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class BandwidthCalculator:
    bandwidth_hz: float = 1000000.0
    snr_db: float = 30.0

    def shannon_capacity(self) -> float:
        snr_linear = 10 ** (self.snr_db / 10)
        return self.bandwidth_hz * math.log2(1 + snr_linear)

    def nyquist_rate(self, levels: int = 2) -> float:
        return 2 * self.bandwidth_hz * math.log2(levels) if levels > 1 else 2 * self.bandwidth_hz

    def throughput(self, efficiency: float = 0.8) -> float:
        return self.shannon_capacity() * efficiency

    def utilization(self, actual_data: float) -> float:
        cap = self.shannon_capacity()
        return actual_data / cap if cap > 0 else 0.0

    def snr_required(self, target_rate: float) -> float:
        if self.bandwidth_hz <= 0:
            return 0.0
        required_snr = 2 ** (target_rate / self.bandwidth_hz) - 1
        return 10 * math.log10(required_snr) if required_snr > 0 else 0.0

    def stats(self) -> Dict:
        return {"shannon": round(self.shannon_capacity(), 0), "nyquist": round(self.nyquist_rate(), 0), "throughput": round(self.throughput(), 0)}

def run():
    bc = BandwidthCalculator(bandwidth_hz=20e6, snr_db=20)
    print(bc.stats())
    print("Utilization at 50M:", bc.utilization(50e6))
    print("SNR for 100M:", bc.snr_required(100e6))

if __name__ == "__main__":
    run()
