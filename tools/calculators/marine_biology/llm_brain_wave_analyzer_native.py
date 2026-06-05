"""Brain Wave Analyzer — band power, delta/theta/alpha/beta/gamma, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math, cmath

@dataclass
class BrainWaveAnalyzer:
    sampling_rate: float = 256.0
    bands: Dict[str, Tuple[float, float]] = field(default_factory=lambda: {
        "delta": (0.5, 4), "theta": (4, 8), "alpha": (8, 13), "beta": (13, 30), "gamma": (30, 100)
    })

    def band_power(self, signal: List[float], band: str) -> float:
        if not signal or band not in self.bands:
            return 0.0
        low, high = self.bands[band]
        N = len(signal)
        freqs = [k * self.sampling_rate / N for k in range(N//2)]
        psd = self._psd(signal)
        return sum(p for f, p in zip(freqs, psd) if low <= f < high)

    def _psd(self, signal: List[float]) -> List[float]:
        N = len(signal)
        fft = [sum(signal[n] * cmath.exp(-2j * math.pi * k * n / N) for n in range(N)) for k in range(N//2)]
        return [abs(v)**2 / N for v in fft]

    def dominant_band(self, signal: List[float]) -> str:
        powers = {b: self.band_power(signal, b) for b in self.bands}
        return max(powers, key=powers.get)

    def band_ratios(self, signal: List[float]) -> Dict[str, float]:
        total = sum(self.band_power(signal, b) for b in self.bands)
        if total == 0:
            return {b: 0 for b in self.bands}
        return {b: self.band_power(signal, b) / total for b in self.bands}

    def stats(self, signal: List[float]) -> Dict:
        return {"dominant": self.dominant_band(signal), "ratios": self.band_ratios(signal)}

def run():
    bwa = BrainWaveAnalyzer()
    import random
    sig = [random.random() * math.sin(2*math.pi*10*t/bwa.sampling_rate) for t in range(256)]
    print("Alpha power:", bwa.band_power(sig, "alpha"))
    print(bwa.stats(sig))

if __name__ == "__main__":
    run()
