"""Native stdlib module: Injection Molding Calculator
Calculates injection molding parameters, cycle times, and shot weights.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class InjectionMoldingCalculator:
    part_weight_g: float
    part_volume_cm3: float
    material_density_g_cm3: float
    runner_weight_g: float
    cavity_count: int
    injection_time_s: float
    cooling_time_s: float
    mold_open_time_s: float

    def shot_weight_g(self) -> float:
        return (self.part_weight_g + self.runner_weight_g) * self.cavity_count

    def shot_volume_cm3(self) -> float:
        if self.material_density_g_cm3 == 0:
            return 0.0
        return self.shot_weight_g() / self.material_density_g_cm3

    def cycle_time_s(self) -> float:
        return self.injection_time_s + self.cooling_time_s + self.mold_open_time_s

    def cycle_time_min(self) -> float:
        return self.cycle_time_s() / 60

    def parts_per_hour(self) -> float:
        if self.cycle_time_s() == 0:
            return 0.0
        return (3600 / self.cycle_time_s()) * self.cavity_count

    def material_utilization_pct(self) -> float:
        if self.shot_weight_g() == 0:
            return 0.0
        return (self.part_weight_g * self.cavity_count / self.shot_weight_g()) * 100

    def clamp_force_ton(self, projected_area_cm2: float, injection_pressure_mpa: float = 100) -> float:
        force_n = projected_area_cm2 * 1e-4 * injection_pressure_mpa * 1e6
        return force_n / 9806.65

    def stats(self, projected_area_cm2: float = 0) -> Dict:
        return {
            "shot_weight_g": round(self.shot_weight_g(), 1),
            "shot_volume_cm3": round(self.shot_volume_cm3(), 1),
            "cycle_time_s": round(self.cycle_time_s(), 1),
            "parts_per_hour": round(self.parts_per_hour(), 1),
            "material_utilization_pct": round(self.material_utilization_pct(), 1),
            "clamp_force_ton": round(self.clamp_force_ton(projected_area_cm2), 1) if projected_area_cm2 else None,
        }

def run():
    imc = InjectionMoldingCalculator(part_weight_g=50, part_volume_cm3=55, material_density_g_cm3=1.05, runner_weight_g=15, cavity_count=4, injection_time_s=3, cooling_time_s=15, mold_open_time_s=5)
    print(imc.stats(projected_area_cm2=200))

if __name__ == "__main__":
    run()
