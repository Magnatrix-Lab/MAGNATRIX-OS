"""LLM Audio Analyzer — Native Python (stdlib only)."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class AudioAnalyzer:
    def __init__(self) -> None:
        self._samples: List[float] = []

    def add_samples(self, samples: List[float]) -> None:
        self._samples.extend(samples)

    def rms(self) -> float:
        if not self._samples:
            return 0.0
        squares = sum(s * s for s in self._samples)
        return math.sqrt(squares / len(self._samples))

    def peak(self) -> float:
        if not self._samples:
            return 0.0
        return max(abs(s) for s in self._samples)

    def zero_crossing_rate(self) -> float:
        if len(self._samples) < 2:
            return 0.0
        crossings = sum(1 for i in range(1, len(self._samples)) if self._samples[i] * self._samples[i-1] < 0)
        return crossings / (len(self._samples) - 1)

    def energy(self) -> float:
        return sum(s * s for s in self._samples)

    def dft(self, n: int = None) -> List[float]:
        samples = self._samples[:n] if n else self._samples
        N = len(samples)
        if N == 0:
            return []
        magnitudes = []
        for k in range(N // 2):
            real = sum(samples[n] * math.cos(2 * math.pi * k * n / N) for n in range(N))
            imag = sum(samples[n] * math.sin(2 * math.pi * k * n / N) for n in range(N))
            magnitudes.append(math.sqrt(real * real + imag * imag))
        return magnitudes

    def dominant_frequency(self, sample_rate: float = 44100) -> float:
        dft = self.dft()
        if not dft:
            return 0.0
        max_idx = max(range(len(dft)), key=lambda i: dft[i])
        return max_idx * sample_rate / len(self._samples)

    def get_stats(self) -> Dict[str, Any]:
        return {"samples": len(self._samples), "rms": self.rms(), "peak": self.peak(), "zcr": self.zero_crossing_rate(), "energy": self.energy()}

def run() -> None:
    print("Audio Analyzer test")
    e = AudioAnalyzer()
    import math
    samples = [math.sin(2 * math.pi * 440 * i / 44100) for i in range(2048)]
    e.add_samples(samples)
    print("  RMS: " + str(e.rms()))
    print("  Peak: " + str(e.peak()))
    print("  ZCR: " + str(e.zero_crossing_rate()))
    print("  Dominant freq: " + str(e.dominant_frequency(44100)))
    print("  Stats: " + str(e.get_stats()))
    print("Audio Analyzer test complete.")

if __name__ == "__main__":
    run()
