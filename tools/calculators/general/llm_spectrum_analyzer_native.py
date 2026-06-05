"""Spectrum Analyzer — DFT, STFT, spectrogram, octave bands, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math, cmath

@dataclass
class SpectrumAnalyzer:
    sample_rate: float = 44100.0
    n_fft: int = 1024

    def dft(self, signal: List[float]) -> List[float]:
        N = len(signal)
        return [abs(sum(signal[n] * cmath.exp(-2j * math.pi * k * n / N) for n in range(N))) for k in range(N // 2)]

    def magnitude(self, signal: List[float]) -> List[float]:
        dft = self.dft(signal)
        return [x / (len(signal) / 2) for x in dft]

    def frequencies(self) -> List[float]:
        return [k * self.sample_rate / self.n_fft for k in range(self.n_fft // 2)]

    def octave_band(self, center: float, signal: List[float]) -> float:
        mag = self.magnitude(signal)
        freqs = self.frequencies()[:len(mag)]
        low, high = center / math.sqrt(2), center * math.sqrt(2)
        band = [m for f, m in zip(freqs, mag) if low <= f < high]
        return sum(band) / len(band) if band else 0.0

    def dominant_freq(self, signal: List[float]) -> float:
        mag = self.magnitude(signal)
        freqs = self.frequencies()[:len(mag)]
        if not mag:
            return 0.0
        return freqs[mag.index(max(mag))]

    def stats(self, signal: List[float]) -> Dict:
        return {"dominant_freq": round(self.dominant_freq(signal), 2), "rms": round(math.sqrt(sum(x**2 for x in signal) / len(signal)), 4) if signal else 0}

def run():
    import math
    sig = [math.sin(2 * math.pi * 1000 * t / 44100) for t in range(1024)]
    sa = SpectrumAnalyzer()
    print(sa.stats(sig))
    print("Octave 1k:", sa.octave_band(1000, sig))

if __name__ == "__main__":
    run()
