"""Synthesis Engine — sine, square, sawtooth, triangle, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

class WaveType(Enum):
    SINE = auto()
    SQUARE = auto()
    SAWTOOTH = auto()
    TRIANGLE = auto()

class SynthEngine:
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.phase = 0.0

    def generate(self, wave_type: WaveType, frequency: float, duration: float, amplitude: float = 1.0) -> List[float]:
        num_samples = int(self.sample_rate * duration)
        samples = []
        for i in range(num_samples):
            t = i / self.sample_rate
            if wave_type == WaveType.SINE:
                val = math.sin(2 * math.pi * frequency * t)
            elif wave_type == WaveType.SQUARE:
                val = 1.0 if math.sin(2 * math.pi * frequency * t) >= 0 else -1.0
            elif wave_type == WaveType.SAWTOOTH:
                val = 2.0 * (frequency * t - math.floor(frequency * t + 0.5))
            elif wave_type == WaveType.TRIANGLE:
                val = 2.0 * abs(2.0 * (frequency * t - math.floor(frequency * t + 0.5))) - 1.0
            else:
                val = 0.0
            samples.append(val * amplitude)
        return samples

    def mix(self, waves: List[List[float]]) -> List[float]:
        if not waves:
            return []
        length = min(len(w) for w in waves)
        return [sum(w[i] for w in waves) / len(waves) for i in range(length)]

    def adsr_envelope(self, samples: List[float], attack: float, decay: float, sustain: float, release: float, duration: float) -> List[float]:
        a_samples = int(self.sample_rate * attack)
        d_samples = int(self.sample_rate * decay)
        r_samples = int(self.sample_rate * release)
        result = []
        for i in range(len(samples)):
            if i < a_samples:
                env = i / a_samples
            elif i < a_samples + d_samples:
                env = 1.0 - (1.0 - sustain) * (i - a_samples) / d_samples
            elif i < len(samples) - r_samples:
                env = sustain
            else:
                env = sustain * (len(samples) - i) / r_samples
            result.append(samples[i] * max(0, env))
        return result

    def stats(self) -> Dict:
        return {"sample_rate": self.sample_rate, "waves": ["sine", "square", "sawtooth", "triangle"]}

def run():
    synth = SynthEngine(44100)
    sine = synth.generate(WaveType.SINE, 440, 0.1, 0.5)
    square = synth.generate(WaveType.SQUARE, 440, 0.1, 0.3)
    mixed = synth.mix([sine, square])
    env = synth.adsr_envelope(sine, 0.01, 0.02, 0.7, 0.05, 0.1)
    print("Sine length:", len(sine), "Mixed length:", len(mixed))
    print(synth.stats())

if __name__ == "__main__":
    run()
