"""Neural Signal Processor — spike detection, filtering, FFT, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math, cmath

@dataclass
class NeuralSignalProcessor:
    sampling_rate: float = 1000.0
    signals: List[float] = field(default_factory=list)

    def bandpass_filter(self, data: List[float], low: float, high: float) -> List[float]:
        out = []
        alpha = 0.1
        prev = 0.0
        for s in data:
            prev = prev + alpha * (s - prev)
            out.append(prev)
        return out

    def detect_spikes(self, threshold: float = 3.0) -> List[int]:
        if not self.signals:
            return []
        mean = sum(self.signals) / len(self.signals)
        std = math.sqrt(sum((x - mean)**2 for x in self.signals) / len(self.signals))
        spikes = []
        for i, v in enumerate(self.signals):
            if abs(v - mean) > threshold * std:
                spikes.append(i)
        return spikes

    def power_spectral_density(self) -> List[float]:
        if not self.signals:
            return []
        N = len(self.signals)
        fft = [sum(self.signals[n] * cmath.exp(-2j * math.pi * k * n / N) for n in range(N)) for k in range(N//2)]
        return [abs(v)**2 / N for v in fft]

    def stats(self) -> Dict:
        return {"samples": len(self.signals), "rate": self.sampling_rate, "duration": len(self.signals)/self.sampling_rate}

def run():
    nsp = NeuralSignalProcessor(signals=[0.1,0.2,5.0,0.1,0.2,0.1,4.5,0.2])
    print("Spikes:", nsp.detect_spikes(2.0))
    print(nsp.stats())

if __name__ == "__main__":
    run()
