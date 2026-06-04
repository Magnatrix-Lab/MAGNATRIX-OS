"""ADC Converter - Analog to digital for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class ADCConverter:
    bits: int = 12
    vref: float = 3.3

    def convert(self, analog_voltage: float) -> int:
        levels = 2**self.bits
        return int((analog_voltage / self.vref) * (levels - 1))

    def to_voltage(self, digital_value: int) -> float:
        levels = 2**self.bits
        return (digital_value / (levels - 1)) * self.vref

    def sample(self, analog_values: List[float]) -> List[int]:
        return [self.convert(v) for v in analog_values]

    def stats(self) -> dict:
        return {"bits": self.bits, "resolution": self.vref / (2**self.bits), "levels": 2**self.bits}

def run():
    adc = ADCConverter(10, 5.0)
    print("Convert 2.5V:", adc.convert(2.5))
    print("To voltage 512:", adc.to_voltage(512))
    print("Stats:", adc.stats())

if __name__ == "__main__": run()
