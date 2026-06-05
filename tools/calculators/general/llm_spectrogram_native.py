"""Spectrogram — STFT, frequency bins, power spectrum, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math
import cmath

class Spectrogram:
    def __init__(self, window_size: int = 256, hop_size: int = 128, sample_rate: int = 44100):
        self.window_size = window_size
        self.hop_size = hop_size
        self.sample_rate = sample_rate
        self.frames: List[List[float]] = []

    def _hann_window(self, n: int) -> List[float]:
        return [0.5 * (1 - math.cos(2 * math.pi * i / (n - 1))) for i in range(n)]

    def _fft(self, samples: List[float]) -> List[complex]:
        N = len(samples)
        if N <= 1:
            return [complex(x, 0) for x in samples]
        if N % 2 != 0:
            return [sum(samples[n] * cmath.exp(-2j * cmath.pi * k * n / N) for n in range(N)) for k in range(N)]
        even = self._fft(samples[::2])
        odd = self._fft(samples[1::2])
        result = [0j] * N
        for k in range(N // 2):
            t = cmath.exp(-2j * cmath.pi * k / N) * odd[k]
            result[k] = even[k] + t
            result[k + N // 2] = even[k] - t
        return result

    def compute(self, samples: List[float]) -> List[List[float]]:
        window = self._hann_window(self.window_size)
        self.frames = []
        for start in range(0, len(samples) - self.window_size, self.hop_size):
            frame = [samples[start + i] * window[i] for i in range(self.window_size)]
            spectrum = self._fft(frame)
            magnitudes = [abs(x) for x in spectrum[:self.window_size // 2]]
            self.frames.append(magnitudes)
        return self.frames

    def frequency_bins(self) -> List[float]:
        return [i * self.sample_rate / self.window_size for i in range(self.window_size // 2)]

    def time_bins(self) -> List[float]:
        return [i * self.hop_size / self.sample_rate for i in range(len(self.frames))]

    def stats(self) -> Dict:
        return {"window_size": self.window_size, "hop_size": self.hop_size, "frames": len(self.frames), "freq_bins": self.window_size // 2}

def run():
    spec = Spectrogram(64, 32, 44100)
    samples = [math.sin(2 * math.pi * 1000 * t / 44100) for t in range(1024)]
    frames = spec.compute(samples)
    print("Frames:", len(frames), "x", len(frames[0]) if frames else 0)
    print(spec.stats())

if __name__ == "__main__":
    run()
