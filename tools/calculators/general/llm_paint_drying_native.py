"""Paint Drying Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class PaintDrying:
    paint_thickness_um: float
    drying_type: str = "air"
    temperature_c: float = 25.0
    humidity_percent: float = 50.0
    airflow_ms: float = 0.5

    def drying_time_minutes(self) -> float:
        base_times = {"air": 60, "oven": 20, "uv": 2, "infrared": 10, "forced_air": 30}
        base = base_times.get(self.drying_type, 60)
        temp_factor = max(0.3, math.exp((25 - self.temperature_c) / 15.0))
        humidity_factor = 1 + (self.humidity_percent - 50) / 100.0
        airflow_factor = max(0.5, 1.0 - self.airflow_ms * 0.3)
        thickness_factor = self.paint_thickness_um / 50.0
        return round(base * temp_factor * humidity_factor * airflow_factor * thickness_factor, 1)

    def touch_dry_time(self) -> float:
        return round(self.drying_time_minutes() * 0.3, 1)

    def hard_dry_time(self) -> float:
        return round(self.drying_time_minutes() * 2.5, 1)

    def energy_for_oven_kwh(self, area_sqm: float = 1.0) -> float:
        if self.drying_type not in ["oven", "infrared"]:
            return 0.0
        energy = area_sqm * self.drying_time_minutes() / 60.0 * 2.0
        return round(energy, 3)

    def solvent_evaporation_rate(self) -> float:
        if self.drying_type == "uv":
            return 0.0
        rate = 0.5 * (self.temperature_c / 25.0) * (1 - self.humidity_percent / 200.0)
        return round(rate, 3)

    def stats(self) -> Dict[str, float]:
        return {
            "drying_time_minutes": self.drying_time_minutes(),
            "touch_dry_minutes": self.touch_dry_time(),
            "hard_dry_minutes": self.hard_dry_time(),
        }

    def run(self):
        print("=" * 60)
        print("PAINT DRYING CALCULATOR")
        print("=" * 60)
        dry = PaintDrying(
            paint_thickness_um=80, drying_type="oven",
            temperature_c=60, humidity_percent=40, airflow_ms=1.0
        )
        print(f"Thickness: {dry.paint_thickness_um} um")
        print(f"Drying type: {dry.drying_type}")
        print(f"Drying time: {dry.drying_time_minutes():.1f} min")
        print(f"Touch dry: {dry.touch_dry_time():.1f} min")
        print(f"Hard dry: {dry.hard_dry_time():.1f} min")
        print(f"Energy: {dry.energy_for_oven_kwh(area_sqm=5.0):.3f} kWh")
        print(f"Solvent evaporation: {dry.solvent_evaporation_rate():.3f}")
        print(f"Stats: {dry.stats()}")

if __name__ == "__main__":
    PaintDrying(0).run()
