"""Oil Viscosity Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class OilViscosity:
    viscosity_40c_cst: float
    viscosity_100c_cst: float
    temperature_c: float = 40.0

    def viscosity_index(self) -> float:
        if self.viscosity_100c_cst <= 0 or self.viscosity_40c_cst <= 0:
            return 0.0
        l = self.viscosity_40c_cst
        h = self.viscosity_100c_cst
        if h < 2.0:
            return 0.0
        vi = ((l - h) / (l - (h ** 1.5))) * 100
        return round(max(min(vi, 150), 0), 1)

    def viscosity_at_temp(self, target_temp_c: float) -> float:
        if self.viscosity_40c_cst <= 0 or self.viscosity_100c_cst <= 0:
            return 0.0
        b = math.log(self.viscosity_40c_cst / self.viscosity_100c_cst) / math.log((100 + 273.15) / (40 + 273.15))
        a = self.viscosity_40c_cst / ((40 + 273.15) ** b)
        visc = a * ((target_temp_c + 273.15) ** b)
        return round(visc, 2)

    def sae_grade(self) -> str:
        if self.viscosity_100c_cst < 5.6:
            return "0W-XX"
        elif self.viscosity_100c_cst < 9.3:
            return "5W-30"
        elif self.viscosity_100c_cst < 12.5:
            return "10W-30"
        elif self.viscosity_100c_cst < 16.3:
            return "15W-40"
        else:
            return "20W-50"

    def kinematic_to_dynamic_cp(self, density_kg_m3: float = 850.0) -> float:
        return round(self.viscosity_40c_cst * density_kg_m3 / 1000.0, 2)

    def pour_point_estimate_c(self) -> float:
        return round(-40 + (self.viscosity_40c_cst - 20) * 0.5, 1)

    def stats(self) -> Dict[str, float]:
        return {
            "viscosity_index": self.viscosity_index(),
            "viscosity_at_temp": self.viscosity_at_temp(self.temperature_c),
            "dynamic_viscosity_cp": self.kinematic_to_dynamic_cp(),
        }

    def run(self):
        print("=" * 60)
        print("OIL VISCOSITY CALCULATOR")
        print("=" * 60)
        oil = OilViscosity(viscosity_40c_cst=45, viscosity_100c_cst=7.5, temperature_c=60)
        print(f"40C: {oil.viscosity_40c_cst} cSt, 100C: {oil.viscosity_100c_cst} cSt")
        print(f"Viscosity index: {oil.viscosity_index():.1f}")
        print(f"Viscosity at {oil.temperature_c}C: {oil.viscosity_at_temp(oil.temperature_c):.2f} cSt")
        print(f"SAE grade: {oil.sae_grade()}")
        print(f"Dynamic viscosity: {oil.kinematic_to_dynamic_cp():.2f} cP")
        print(f"Pour point estimate: {oil.pour_point_estimate_c():.1f} C")
        print(f"Stats: {oil.stats()}")

if __name__ == "__main__":
    OilViscosity(0, 0).run()
