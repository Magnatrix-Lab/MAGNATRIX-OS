"""Native stdlib module: Extruder Calculator
Calculates extruder throughput, screw speed, and melt temperature for plastics.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class ScrewType(Enum):
    SINGLE = "single"
    TWIN = "twin"
    BARRIER = "barrier"

@dataclass
class ExtruderCalculator:
    screw_diameter_mm: float
    screw_speed_rpm: float
    screw_type: ScrewType
    material_density_g_cm3: float
    melt_temperature_c: float
    die_pressure_mpa: float

    def throughput_kg_hr(self) -> float:
        base = math.pi * (self.screw_diameter_mm / 1000 / 2) ** 2 * (self.screw_speed_rpm / 60) * 1000
        factor = 1.0 if self.screw_type == ScrewType.SINGLE else 1.5 if self.screw_type == ScrewType.TWIN else 1.2
        return base * factor * self.material_density_g_cm3 * 3600

    def shear_rate_s(self) -> float:
        if self.screw_diameter_mm == 0:
            return 0.0
        return math.pi * self.screw_diameter_mm * self.screw_speed_rpm / (60 * 1)

    def specific_energy_kwh_kg(self) -> float:
        if self.throughput_kg_hr() == 0:
            return 0.0
        motor_power_kw = 50 * (self.screw_diameter_mm / 100) ** 2
        return motor_power_kw / self.throughput_kg_hr()

    def residence_time_s(self, barrel_length_m: float = 4) -> float:
        if self.screw_speed_rpm == 0:
            return 0.0
        return (barrel_length_m * 60) / (self.screw_speed_rpm * 0.5)

    def melt_viscosity_pa_s(self) -> float:
        return 1000 * math.exp(-0.01 * (self.melt_temperature_c - 200))

    def stats(self, barrel_length_m: float = 4) -> Dict:
        return {
            "screw_type": self.screw_type.value,
            "throughput_kg_hr": round(self.throughput_kg_hr(), 1),
            "shear_rate_s": round(self.shear_rate_s(), 1),
            "specific_energy_kwh_kg": round(self.specific_energy_kwh_kg(), 3),
            "residence_time_s": round(self.residence_time_s(barrel_length_m), 1),
            "melt_viscosity_pa_s": round(self.melt_viscosity_pa_s(), 1),
        }

def run():
    import math
    ec = ExtruderCalculator(screw_diameter_mm=65, screw_speed_rpm=80, screw_type=ScrewType.SINGLE, material_density_g_cm3=0.95, melt_temperature_c=220, die_pressure_mpa=15)
    print(ec.stats())

if __name__ == "__main__":
    run()
