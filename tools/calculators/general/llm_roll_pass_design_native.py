"""Roll Pass Design Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class RollPassDesign:
    initial_area_mm2: float
    final_area_mm2: float
    roll_diameter_mm: float
    material_yield_strength_mpa: float = 250.0

    def area_reduction_percent(self) -> float:
        if self.initial_area_mm2 <= 0:
            return 0.0
        return round((self.initial_area_mm2 - self.final_area_mm2) / self.initial_area_mm2 * 100, 2)

    def number_of_passes(self, max_reduction_per_pass: float = 25.0) -> int:
        reduction = self.area_reduction_percent()
        if max_reduction_per_pass <= 0:
            return 0
        return max(1, math.ceil(reduction / max_reduction_per_pass))

    def roll_force_kn(self) -> float:
        if self.roll_diameter_mm <= 0:
            return 0.0
        avg_area = (self.initial_area_mm2 + self.final_area_mm2) / 2.0
        contact_length = math.sqrt(self.roll_diameter_mm * (self.initial_area_mm2 - self.final_area_mm2) / self.initial_area_mm2 * 0.5)
        return round(self.material_yield_strength_mpa * avg_area / 1000.0 * contact_length / 100.0, 2)

    def roll_torque_nm(self) -> float:
        force = self.roll_force_kn()
        lever_arm = self.roll_diameter_mm / 2000.0
        return round(force * 1000 * lever_arm * 0.5, 2)

    def roll_power_kw(self, rolling_speed_m_s: float = 1.0) -> float:
        torque = self.roll_torque_nm()
        angular_velocity = rolling_speed_m_s / (self.roll_diameter_mm / 2000.0)
        return round(torque * angular_velocity / 1000, 2)

    def strain_per_pass(self) -> float:
        passes = self.number_of_passes()
        if passes <= 0:
            return 0.0
        total_strain = math.log(self.initial_area_mm2 / self.final_area_mm2) if self.final_area_mm2 > 0 else 0
        return round(total_strain / passes, 4)

    def stats(self) -> Dict[str, float]:
        return {
            "area_reduction_percent": self.area_reduction_percent(),
            "number_of_passes": self.number_of_passes(),
            "roll_force_kn": self.roll_force_kn(),
        }

    def run(self):
        print("=" * 60)
        print("ROLL PASS DESIGN CALCULATOR")
        print("=" * 60)
        rpd = RollPassDesign(
            initial_area_mm2=10000, final_area_mm2=2500,
            roll_diameter_mm=400, material_yield_strength_mpa=300
        )
        print(f"Initial: {rpd.initial_area_mm2} mm2, Final: {rpd.final_area_mm2} mm2")
        print(f"Reduction: {rpd.area_reduction_percent():.2f}%")
        print(f"Passes: {rpd.number_of_passes()}")
        print(f"Roll force: {rpd.roll_force_kn():.2f} kN")
        print(f"Roll torque: {rpd.roll_torque_nm():.2f} Nm")
        print(f"Roll power: {rpd.roll_power_kw():.2f} kW")
        print(f"Strain/pass: {rpd.strain_per_pass():.4f}")
        print(f"Stats: {rpd.stats()}")

if __name__ == "__main__":
    RollPassDesign(0, 0, 0).run()
