"""Synth Optimizer — ADSR, harmonics, filter, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class SynthOptimizer:
    freq_hz: float = 440.0
    harmonics: int = 4
    filter_cutoff_hz: float = 2000.0

    def harmonic_series(self) -> List[float]:
        return [self.freq_hz * (i + 1) for i in range(self.harmonics)]

    def adsr_duration(self, attack: float = 0.01, decay: float = 0.2, sustain: float = 0.5, release: float = 0.3) -> float:
        return attack + decay + sustain + release

    def filter_attenuation(self, harmonic_freq: float) -> float:
        return 1.0 / (1.0 + (harmonic_freq / self.filter_cutoff_hz) ** 2) if self.filter_cutoff_hz > 0 else 0.0

    def stats(self) -> Dict:
        return {"harmonics": self.harmonic_series(), "adsr_total": round(self.adsr_duration(), 3), "filter_3rd": round(self.filter_attenuation(self.freq_hz * 3), 3)}

def run():
    so = SynthOptimizer(freq_hz=220, harmonics=6, filter_cutoff_hz=1500)
    print(so.stats())

if __name__ == "__main__":
    run()
