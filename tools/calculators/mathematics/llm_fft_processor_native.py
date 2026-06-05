"""FFT Processor — Fast Fourier Transform, DFT, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math
import cmath

class FFTDirection(Enum):
    FORWARD = auto()
    INVERSE = auto()

class FFTProcessor:
    def __init__(self):
        self.cache: Dict[int, List[complex]] = {}

    def dft(self, signal: List[float]) -> List[complex]:
        N = len(signal)
        result = []
        for k in range(N):
            s = 0j
            for n in range(N):
                s += signal[n] * cmath.exp(-2j * math.pi * k * n / N)
            result.append(s)
        return result

    def idft(self, spectrum: List[complex]) -> List[float]:
        N = len(spectrum)
        result = []
        for n in range(N):
            s = 0j
            for k in range(N):
                s += spectrum[k] * cmath.exp(2j * math.pi * k * n / N)
            result.append(s.real / N)
        return result

    def fft(self, signal: List[float]) -> List[complex]:
        N = len(signal)
        if N <= 1:
            return [complex(x, 0) for x in signal]
        if N % 2 != 0:
            return self.dft(signal)
        even = self.fft(signal[::2])
        odd = self.fft(signal[1::2])
        result = [0j] * N
        for k in range(N // 2):
            t = cmath.exp(-2j * math.pi * k / N) * odd[k]
            result[k] = even[k] + t
            result[k + N // 2] = even[k] - t
        return result

    def ifft(self, spectrum: List[complex]) -> List[float]:
        conj = [x.conjugate() for x in spectrum]
        transformed = self.fft([x.real for x in conj])
        return [x.real / len(spectrum) for x in [y.conjugate() for y in transformed]]

    def magnitude_spectrum(self, spectrum: List[complex]) -> List[float]:
        return [abs(x) for x in spectrum]

    def phase_spectrum(self, spectrum: List[complex]) -> List[float]:
        return [cmath.phase(x) for x in spectrum]

    def frequency_bins(self, sample_rate: float, N: int) -> List[float]:
        return [i * sample_rate / N for i in range(N)]

    def stats(self) -> Dict:
        return {"supported": ["DFT", "FFT", "IDFT", "IFFT"]}

def run():
    fft = FFTProcessor()
    signal = [math.sin(2 * math.pi * 5 * t / 64) for t in range(64)]
    spectrum = fft.fft(signal)
    mag = fft.magnitude_spectrum(spectrum)
    print("Max freq bin:", mag.index(max(mag[:32])))
    print(fft.stats())

if __name__ == "__main__":
    run()
