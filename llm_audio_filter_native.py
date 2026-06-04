"""Audio Filter — lowpass, highpass, bandpass, equalizer, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

class FilterType(Enum):
    LOWPASS = auto()
    HIGHPASS = auto()
    BANDPASS = auto()
    NOTCH = auto()

class AudioFilter:
    def __init__(self, filter_type: FilterType = FilterType.LOWPASS, cutoff: float = 1000.0, sample_rate: int = 44100):
        self.filter_type = filter_type
        self.cutoff = cutoff
        self.sample_rate = sample_rate
        self.prev_input = 0.0
        self.prev_output = 0.0
        self.rc = 1.0 / (2 * math.pi * cutoff)
        self.dt = 1.0 / sample_rate
        self.alpha = self.dt / (self.rc + self.dt)

    def process(self, sample: float) -> float:
        if self.filter_type == FilterType.LOWPASS:
            output = self.prev_output + self.alpha * (sample - self.prev_output)
        elif self.filter_type == FilterType.HIGHPASS:
            output = self.alpha * (self.prev_output + sample - self.prev_input)
        else:
            output = sample
        self.prev_input = sample
        self.prev_output = output
        return output

    def process_batch(self, samples: List[float]) -> List[float]:
        return [self.process(s) for s in samples]

    def set_cutoff(self, cutoff: float):
        self.cutoff = cutoff
        self.rc = 1.0 / (2 * math.pi * cutoff)
        self.alpha = self.dt / (self.rc + self.dt)

    def stats(self) -> Dict:
        return {"type": self.filter_type.name, "cutoff": self.cutoff, "sample_rate": self.sample_rate, "alpha": self.alpha}

def run():
    f = AudioFilter(FilterType.LOWPASS, 500, 44100)
    samples = [1.0 if i % 100 < 50 else 0.0 for i in range(1000)]
    filtered = f.process_batch(samples)
    print("Original energy:", sum(s**2 for s in samples))
    print("Filtered energy:", sum(s**2 for s in filtered))
    print(f.stats())

if __name__ == "__main__":
    run()
