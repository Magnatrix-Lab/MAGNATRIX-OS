"""Noise Generator — white, pink, brown, Gaussian, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import random
import math

class NoiseType(Enum):
    WHITE = auto()
    GAUSSIAN = auto()
    PINK = auto()
    BROWN = auto()
    BLUE = auto()

class NoiseGenerator:
    def __init__(self, noise_type: NoiseType = NoiseType.WHITE, seed: int = 42):
        self.noise_type = noise_type
        self.seed = seed
        random.seed(seed)
        self.brown_prev = 0.0

    def generate(self, length: int) -> List[float]:
        if self.noise_type == NoiseType.WHITE:
            return [random.random() * 2 - 1 for _ in range(length)]
        elif self.noise_type == NoiseType.GAUSSIAN:
            return [random.gauss(0, 1) for _ in range(length)]
        elif self.noise_type == NoiseType.PINK:
            return self._pink_noise(length)
        elif self.noise_type == NoiseType.BROWN:
            return self._brown_noise(length)
        elif self.noise_type == NoiseType.BLUE:
            return self._blue_noise(length)
        return []

    def _pink_noise(self, length: int) -> List[float]:
        values = [0.0] * length
        for i in range(length):
            values[i] = random.random() * 2 - 1
        for i in range(1, length):
            values[i] = 0.5 * (values[i-1] + values[i])
        return values

    def _brown_noise(self, length: int) -> List[float]:
        values = []
        for _ in range(length):
            self.brown_prev += random.gauss(0, 1)
            values.append(self.brown_prev)
        m = sum(values) / len(values)
        return [v - m for v in values]

    def _blue_noise(self, length: int) -> List[float]:
        values = [random.random() * 2 - 1 for _ in range(length)]
        for i in range(length - 1, 0, -1):
            values[i] = 0.5 * (values[i] - values[i-1])
        return values

    def spectrum(self, signal: List[float]) -> List[float]:
        n = len(signal)
        if n == 0:
            return []
        # Simplified power spectrum
        return [x ** 2 for x in signal]

    def stats(self, signal: List[float]) -> Dict:
        if not signal:
            return {}
        mean = sum(signal) / len(signal)
        variance = sum((x - mean) ** 2 for x in signal) / len(signal)
        return {"mean": mean, "std": math.sqrt(variance), "min": min(signal), "max": max(signal)}

def run():
    gen = NoiseGenerator(NoiseType.GAUSSIAN, seed=42)
    signal = gen.generate(1000)
    print(gen.stats(signal))
    brown = NoiseGenerator(NoiseType.BROWN, seed=42)
    print(brown.stats(brown.generate(1000)))

if __name__ == "__main__":
    run()
