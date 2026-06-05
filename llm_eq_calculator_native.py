"""Native stdlib module: EQ Calculator
Calculates filter frequencies, Q factors, and bandwidth for audio equalization.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class EQCalculator:
    center_freq_hz: float
    gain_db: float
    q_factor: float

    def bandwidth_hz(self) -> float:
        if self.q_factor == 0:
            return 0.0
        return self.center_freq_hz / self.q_factor

    def lower_freq_hz(self) -> float:
        bw = self.bandwidth_hz()
        return self.center_freq_hz - (bw / 2)

    def upper_freq_hz(self) -> float:
        bw = self.bandwidth_hz()
        return self.center_freq_hz + (bw / 2)

    def octave_bandwidth(self) -> float:
        if self.q_factor == 0:
            return 0.0
        return math.log2(1 + 1 / (2 * self.q_factor) + math.sqrt(1 + (1 / (2 * self.q_factor)) ** 2))

    def gain_linear(self) -> float:
        return 10 ** (self.gain_db / 20)

    def stats(self) -> Dict:
        return {
            "center_freq_hz": self.center_freq_hz,
            "gain_db": self.gain_db,
            "q_factor": self.q_factor,
            "bandwidth_hz": round(self.bandwidth_hz(), 1),
            "lower_freq_hz": round(self.lower_freq_hz(), 1),
            "upper_freq_hz": round(self.upper_freq_hz(), 1),
            "octave_bandwidth": round(self.octave_bandwidth(), 3),
            "gain_linear": round(self.gain_linear(), 3),
        }

def run():
    eq = EQCalculator(center_freq_hz=1000, gain_db=-3, q_factor=1.4)
    print(eq.stats())

if __name__ == "__main__":
    run()
