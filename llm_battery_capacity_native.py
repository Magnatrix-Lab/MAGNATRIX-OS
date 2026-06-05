"""Battery Capacity Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class BatteryCapacity:
    nominal_capacity_ah: float
    voltage_v: float
    discharge_rate_c: float = 1.0
    temperature_c: float = 25.0
    cycle_count: int = 0

    def energy_wh(self) -> float:
        return round(self.nominal_capacity_ah * self.voltage_v, 2)

    def energy_kwh(self) -> float:
        return round(self.energy_wh() / 1000, 4)

    def actual_capacity_ah(self) -> float:
        rate_factor = max(0.5, 1 - (self.discharge_rate_c - 1) * 0.1)
        temp_factor = max(0.7, 1 - abs(self.temperature_c - 25) / 50.0)
        cycle_factor = max(0.6, 1 - self.cycle_count / 2000.0)
        return round(self.nominal_capacity_ah * rate_factor * temp_factor * cycle_factor, 2)

    def actual_energy_wh(self) -> float:
        return round(self.actual_capacity_ah() * self.voltage_v, 2)

    def discharge_current_a(self) -> float:
        return round(self.nominal_capacity_ah * self.discharge_rate_c, 2)

    def discharge_time_hours(self) -> float:
        if self.discharge_rate_c <= 0:
            return 0.0
        return round(1.0 / self.discharge_rate_c, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "energy_wh": self.energy_wh(),
            "actual_capacity_ah": self.actual_capacity_ah(),
            "actual_energy_wh": self.actual_energy_wh(),
        }

    def run(self):
        print("=" * 60)
        print("BATTERY CAPACITY CALCULATOR")
        print("=" * 60)
        bat = BatteryCapacity(
            nominal_capacity_ah=100, voltage_v=3.7,
            discharge_rate_c=2.0, temperature_c=35, cycle_count=500
        )
        print(f"Nominal: {bat.nominal_capacity_ah} Ah @ {bat.voltage_v} V")
        print(f"Energy: {bat.energy_wh():.2f} Wh ({bat.energy_kwh():.4f} kWh)")
        print(f"Actual capacity: {bat.actual_capacity_ah():.2f} Ah")
        print(f"Actual energy: {bat.actual_energy_wh():.2f} Wh")
        print(f"Discharge current: {bat.discharge_current_a():.2f} A")
        print(f"Discharge time: {bat.discharge_time_hours():.2f} h")
        print(f"Stats: {bat.stats()}")

if __name__ == "__main__":
    BatteryCapacity(0, 0).run()
