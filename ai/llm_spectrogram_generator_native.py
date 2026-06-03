"""Spectrogram Generator - Time-frequency analysis for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List
import math
import cmath

@dataclass
class SpectrogramGenerator:
    window_size: int = 4; hop_size: int = 2

    def hanning(self, n: int) -> List[float]:
        return [0.5*(1-math.cos(2*math.pi*i/(n-1))) for i in range(n)]

    def stft(self, signal: List[float]) -> List[List[float]]:
        n = len(signal); w = self.window_size; h = self.hop_size
        window = self.hanning(w)
        frames = []
        for i in range(0, n-w+1, h):
            frame = [signal[i+j]*window[j] for j in range(w)]
            spectrum = [sum(frame[t]*cmath.exp(-2j*cmath.pi*k*t/w) for t in range(w)) for k in range(w)]
            frames.append([abs(x) for x in spectrum])
        return frames

    def stats(self, signal: List[float]) -> dict:
        spec = self.stft(signal)
        return {"frames": len(spec), "freq_bins": len(spec[0]) if spec else 0}

def run():
    sg = SpectrogramGenerator(4, 2)
    signal = [1.0, 0.5, -0.5, -1.0, -0.5, 0.5, 1.0, 0.5]
    spec = sg.stft(signal)
    print("Spectrogram shape:", len(spec), "x", len(spec[0]) if spec else 0)
    print("Stats:", sg.stats(signal))

if __name__ == "__main__": run()
