"""Sonar Processor — echo detection, depth, bathymetry, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class SonarProcessor:
    speed_of_sound: float = 1500.0
    pulse_duration: float = 0.001

    def depth(self, travel_time: float) -> float:
        return self.speed_of_sound * travel_time / 2

    def detect_echoes(self, signal: List[float], threshold: float = 0.5) -> List[int]:
        echoes = []
        for i in range(1, len(signal) - 1):
            if signal[i] > threshold and signal[i] > signal[i-1] and signal[i] > signal[i+1]:
                echoes.append(i)
        return echoes

    def bathymetry(self, pings: List[List[float]]) -> List[float]:
        depths = []
        for ping in pings:
            echoes = self.detect_echoes(ping)
            if echoes:
                depths.append(self.depth(echoes[0] * self.pulse_duration))
            else:
                depths.append(0.0)
        return depths

    def slant_range(self, depth: float, angle: float) -> float:
        return depth / math.cos(math.radians(angle))

    def stats(self) -> Dict:
        return {"speed": self.speed_of_sound, "pulse": self.pulse_duration}

def run():
    sp = SonarProcessor()
    pings = [[0.1, 0.2, 0.9, 0.3], [0.1, 0.3, 0.8, 0.2]]
    print("Depths:", sp.bathymetry(pings))
    print(sp.stats())

if __name__ == "__main__":
    run()
