"""Pasteurization Units Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class PasteurizationUnits:
    temperature_c: float
    time_seconds: float
    target_z_value_c: float = 10.0
    reference_temp_c: float = 60.0
    target_pu: float = 50.0

    def pasteurization_units(self) -> float:
        if self.temperature_c <= self.reference_temp_c:
            return 0.0
        return round(self.time_seconds * math.exp((self.temperature_c - self.reference_temp_c) / self.target_z_value_c), 2)

    def is_adequately_pasteurized(self) -> bool:
        return self.pasteurization_units() >= self.target_pu

    def required_time_at_temp(self) -> float:
        if self.temperature_c <= self.reference_temp_c:
            return 0.0
        return round(self.target_pu / math.exp((self.temperature_c - self.reference_temp_c) / self.target_z_value_c), 1)

    def lethal_rate(self) -> float:
        if self.temperature_c <= self.reference_temp_c:
            return 0.0
        return round(math.exp((self.temperature_c - self.reference_temp_c) / self.target_z_value_c), 4)

    def f0_value(self) -> float:
        z = 10.0
        ref = 121.1
        if self.temperature_c <= ref:
            return 0.0
        return round(self.time_seconds * math.exp((self.temperature_c - ref) / z), 2)

    def decimal_reduction_time(self) -> float:
        d_ref = 10.0
        return round(d_ref / self.lethal_rate(), 2)

    def stats(self) -> Dict[str, float]:
        return {
            "pasteurization_units": self.pasteurization_units(),
            "lethal_rate": self.lethal_rate(),
            "required_time_s": self.required_time_at_temp(),
        }

    def run(self):
        print("=" * 60)
        print("PASTEURIZATION UNITS CALCULATOR")
        print("=" * 60)
        pu = PasteurizationUnits(
            temperature_c=72, time_seconds=15, target_z_value_c=10, target_pu=50
        )
        print(f"Temperature: {pu.temperature_c} C")
        print(f"Time: {pu.time_seconds} s")
        print(f"PU: {pu.pasteurization_units():.2f}")
        print(f"Adequate: {pu.is_adequately_pasteurized()}")
        print(f"Required time: {pu.required_time_at_temp():.1f} s")
        print(f"Lethal rate: {pu.lethal_rate():.4f}")
        print(f"F0 value: {pu.f0_value():.2f}")
        print(f"Decimal reduction: {pu.decimal_reduction_time():.2f} s")
        print(f"Stats: {pu.stats()}")

if __name__ == "__main__":
    PasteurizationUnits(0, 0).run()
