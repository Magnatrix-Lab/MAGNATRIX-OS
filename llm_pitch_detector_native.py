"""Pitch Detector — autocorrelation, YIN, peak picking, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

class PitchDetector:
    def __init__(self, sample_rate: int = 44100, min_freq: float = 50, max_freq: float = 2000):
        self.sample_rate = sample_rate
        self.min_freq = min_freq
        self.max_freq = max_freq
        self.min_period = int(sample_rate / max_freq)
        self.max_period = int(sample_rate / min_freq)

    def autocorrelation(self, samples: List[float]) -> List[float]:
        N = len(samples)
        result = []
        for lag in range(self.min_period, min(self.max_period, N)):
            corr = sum(samples[i] * samples[i + lag] for i in range(N - lag))
            result.append(corr)
        return result

    def yin(self, samples: List[float]) -> Optional[float]:
        N = len(samples)
        diffs = []
        for tau in range(1, min(self.max_period, N)):
            diff = sum((samples[i] - samples[i + tau]) ** 2 for i in range(N - tau))
            diffs.append(diff)
        # Cumulative mean normalized difference
        cmnd = []
        for tau in range(len(diffs)):
            if tau == 0:
                cmnd.append(1.0)
            else:
                sum_diffs = sum(diffs[:tau+1])
                cmnd.append(diffs[tau] / (sum_diffs / (tau + 1)) if sum_diffs > 0 else 1.0)
        # Find first minimum below threshold
        threshold = 0.1
        for tau in range(self.min_period, len(cmnd)):
            if cmnd[tau] < threshold:
                # Parabolic interpolation
                return self.sample_rate / tau
        return None

    def detect_pitch(self, samples: List[float]) -> Optional[float]:
        return self.yin(samples)

    def midi_note(self, freq: float) -> int:
        return int(69 + 12 * math.log2(freq / 440.0)) if freq > 0 else 0

    def stats(self) -> Dict:
        return {"sample_rate": self.sample_rate, "min_freq": self.min_freq, "max_freq": self.max_freq}

def run():
    pd = PitchDetector(44100)
    samples = [math.sin(2 * math.pi * 440 * t / 44100) for t in range(4096)]
    pitch = pd.detect_pitch(samples)
    print("Pitch:", pitch, "Hz, MIDI:", pd.midi_note(pitch) if pitch else None)
    print(pd.stats())

if __name__ == "__main__":
    run()
