"""ADC Reader — analog-to-digital conversion simulation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math
import random

class ADCResolution(Enum):
    BITS_8 = 8
    BITS_10 = 10
    BITS_12 = 12
    BITS_16 = 16

@dataclass
class ADCChannel:
    channel_id: str
    resolution: ADCResolution
    vref: float = 3.3
    samples: List[int] = field(default_factory=list)

    def max_value(self) -> int:
        return 2 ** self.resolution.value - 1

class ADCReader:
    def __init__(self, sample_rate: int = 1000):
        self.sample_rate = sample_rate
        self.channels: Dict[str, ADCChannel] = {}
        self.calibration: Dict[str, Tuple[float, float]] = {}

    def add_channel(self, channel_id: str, resolution: ADCResolution = ADCResolution.BITS_12, vref: float = 3.3):
        self.channels[channel_id] = ADCChannel(channel_id, resolution, vref)

    def read_voltage(self, channel_id: str, voltage: float) -> int:
        ch = self.channels.get(channel_id)
        if not ch:
            return 0
        max_val = ch.max_value()
        digital = int((voltage / ch.vref) * max_val)
        digital = max(0, min(max_val, digital))
        ch.samples.append(digital)
        return digital

    def read_with_noise(self, channel_id: str, voltage: float, noise_std: float = 0.01) -> int:
        noisy = voltage + random.gauss(0, noise_std)
        return self.read_voltage(channel_id, noisy)

    def to_voltage(self, channel_id: str, digital: int) -> float:
        ch = self.channels.get(channel_id)
        if not ch:
            return 0.0
        return (digital / ch.max_value()) * ch.vref

    def average(self, channel_id: str) -> float:
        ch = self.channels.get(channel_id)
        if not ch or not ch.samples:
            return 0.0
        return sum(ch.samples) / len(ch.samples)

    def calibrate(self, channel_id: str, offset: float, gain: float):
        self.calibration[channel_id] = (offset, gain)

    def stats(self) -> Dict:
        return {"channels": len(self.channels), "sample_rate": self.sample_rate, "samples_per_channel": {k: len(v.samples) for k, v in self.channels.items()}}

def run():
    adc = ADCReader()
    adc.add_channel("temp", ADCResolution.BITS_12, 3.3)
    for v in [1.0, 1.5, 2.0, 2.5, 3.0]:
        adc.read_with_noise("temp", v, 0.05)
    print("Average digital:", adc.average("temp"))
    print("Voltage back:", adc.to_voltage("temp", int(adc.average("temp"))))
    print(adc.stats())

if __name__ == "__main__":
    run()
