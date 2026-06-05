"""Native stdlib module: Pesticide Calculator
Calculates pesticide application rates, tank mixes, and safety buffers.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class PesticideCalculator:
    pesticide_name: str
    active_ingredient_pct: float
    recommended_rate_l_per_ha: float
    area_ha: float
    water_volume_l_per_ha: float = 200
    buffer_distance_m: float = 10

    def total_pesticide_l(self) -> float:
        return self.recommended_rate_l_per_ha * self.area_ha

    def total_water_l(self) -> float:
        return self.water_volume_l_per_ha * self.area_ha

    def active_ingredient_g_per_ha(self) -> float:
        return self.recommended_rate_l_per_ha * 1000 * (self.active_ingredient_pct / 100)

    def total_active_ingredient_g(self) -> float:
        return self.active_ingredient_g_per_ha() * self.area_ha

    def tank_mix_concentration_pct(self) -> float:
        if self.total_water_l() == 0:
            return 0.0
        return (self.total_pesticide_l() / self.total_water_l()) * 100

    def stats(self) -> Dict:
        return {
            "pesticide": self.pesticide_name,
            "total_pesticide_l": round(self.total_pesticide_l(), 2),
            "total_water_l": round(self.total_water_l(), 1),
            "active_ingredient_g_ha": round(self.active_ingredient_g_per_ha(), 1),
            "total_active_ingredient_g": round(self.total_active_ingredient_g(), 1),
            "tank_mix_concentration_pct": round(self.tank_mix_concentration_pct(), 3),
            "buffer_m": self.buffer_distance_m,
        }

def run():
    pc = PesticideCalculator(pesticide_name="Insecticide-X", active_ingredient_pct=20, recommended_rate_l_per_ha=1.5, area_ha=30, water_volume_l_per_ha=250, buffer_distance_m=15)
    print(pc.stats())

if __name__ == "__main__":
    run()
