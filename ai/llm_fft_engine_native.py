"""FFT Engine - Fast Fourier Transform for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
import math
import cmath

@dataclass
class FFTEngine:

    def dft(self, signal: List[float]) -> List[complex]:
        N = len(signal)
        return [sum(signal[n] * cmath.exp(-2j*cmath.pi*k*n/N) for n in range(N)) for k in range(N)]

    def idft(self, spectrum: List[complex]) -> List[float]:
        N = len(spectrum)
        return [sum(spectrum[k] * cmath.exp(2j*cmath.pi*k*n/N) for k in range(N)).real / N for n in range(N)]

    def magnitude(self, spectrum: List[complex]) -> List[float]:
        return [abs(x) for x in spectrum]

    def stats(self, signal: List[float]) -> dict:
        spec = self.dft(signal)
        mag = self.magnitude(spec)
        return {"length": len(signal), "max_freq": max(mag), "dominant": mag.index(max(mag))}

def run():
    fft = FFTEngine()
    signal = [1.0, 0.0, -1.0, 0.0]
    spec = fft.dft(signal)
    mag = fft.magnitude(spec)
    print("Magnitudes:", [round(m,4) for m in mag])
    print("Stats:", fft.stats(signal))

if __name__ == "__main__": run()
