"""Weld Cost Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class WeldCost:
    weld_length_m: float
    weld_throat_mm: float
    process_type: str = "mig"
    labor_rate_per_h: float = 25.0

    def weld_volume_mm3(self) -> float:
        if self.weld_throat_mm <= 0:
            return 0.0
        area = self.weld_throat_mm ** 2 / 2.0
        return round(area * self.weld_length_m * 1000, 1)

    def weld_weight_kg(self, density_g_cm3: float = 7.8) -> float:
        return round(self.weld_volume_mm3() * density_g_cm3 / 1e6, 3)

    def electrode_weight_kg(self) -> float:
        efficiencies = {"mig": 0.95, "tig": 0.85, "flux_core": 0.90, "stick": 0.60, "submerged": 0.98}
        eff = efficiencies.get(self.process_type, 0.9)
        return round(self.weld_weight_kg() / eff, 3)

    def deposition_rate_kg_per_h(self) -> float:
        rates = {"mig": 3.0, "tig": 1.0, "flux_core": 4.0, "stick": 2.0, "submerged": 8.0}
        return rates.get(self.process_type, 3.0)

    def welding_time_h(self) -> float:
        rate = self.deposition_rate_kg_per_h()
        if rate <= 0:
            return 0.0
        return round(self.weld_weight_kg() / rate, 2)

    def labor_cost(self) -> float:
        return round(self.welding_time_h() * self.labor_rate_per_h, 2)

    def material_cost(self, electrode_price_per_kg: float = 3.0) -> float:
        return round(self.electrode_weight_kg() * electrode_price_per_kg, 2)

    def power_cost(self, power_kw: float = 5.0, energy_price_per_kwh: float = 0.15) -> float:
        return round(self.welding_time_h() * power_kw * energy_price_per_kwh, 2)

    def total_cost(self, electrode_price_per_kg: float = 3.0) -> float:
        return round(self.labor_cost() + self.material_cost(electrode_price_per_kg) + self.power_cost(), 2)

    def cost_per_meter(self, electrode_price_per_kg: float = 3.0) -> float:
        if self.weld_length_m <= 0:
            return 0.0
        return round(self.total_cost(electrode_price_per_kg) / self.weld_length_m, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "welding_time_h": self.welding_time_h(),
            "labor_cost": self.labor_cost(),
            "total_cost": self.total_cost(),
        }

    def run(self):
        print("=" * 60)
        print("WELD COST CALCULATOR")
        print("=" * 60)
        wc = WeldCost(
            weld_length_m=10, weld_throat_mm=5, process_type="mig", labor_rate_per_h=30
        )
        print(f"Weld: {wc.weld_length_m} m @ {wc.weld_throat_mm} mm throat")
        print(f"Volume: {wc.weld_volume_mm3():.1f} mm3")
        print(f"Weight: {wc.weld_weight_kg():.3f} kg")
        print(f"Electrode: {wc.electrode_weight_kg():.3f} kg")
        print(f"Time: {wc.welding_time_h():.2f} h")
        print(f"Labor: ${wc.labor_cost():.2f}")
        print(f"Material: ${wc.material_cost():.2f}")
        print(f"Total: ${wc.total_cost():.2f}")
        print(f"Cost/m: ${wc.cost_per_meter():.2f}")
        print(f"Stats: {wc.stats()}")

if __name__ == "__main__":
    WeldCost(0, 0).run()
