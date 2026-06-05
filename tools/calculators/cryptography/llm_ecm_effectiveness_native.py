"""Native stdlib module: ECM Effectiveness Calculator
Calculates electronic countermeasure effectiveness and jamming ratios.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class ECMEffectivenessCalculator:
    jammer_power_w: float
    jammer_gain_db: float
    target_radar_gain_db: float
    target_radar_power_w: float
    distance_to_target_km: float
    frequency_ghz: float

    def jamming_to_signal_ratio(self) -> float:
        g_j = 10 ** (self.jammer_gain_db / 10)
        g_t = 10 ** (self.target_radar_gain_db / 10)
        r_j = self.distance_to_target_km * 1000
        if r_j == 0 or g_t == 0:
            return 0.0
        return (self.jammer_power_w * g_j * 4 * math.pi * (r_j ** 2)) / (self.target_radar_power_w * g_t * (0.1 ** 2))

    def js_db(self) -> float:
        j_s = self.jamming_to_signal_ratio()
        if j_s <= 0:
            return -999
        return 10 * math.log10(j_s)

    def effective_range_reduction_factor(self) -> float:
        js = self.jamming_to_signal_ratio()
        if js == 0:
            return 1.0
        return 1 / (js ** 0.25)

    def burnthrough_range_km(self) -> float:
        if self.jamming_to_signal_ratio() == 0:
            return 0.0
        return self.distance_to_target_km / (self.jamming_to_signal_ratio() ** 0.25)

    def effectiveness_pct(self) -> float:
        js = self.js_db()
        if js < 0:
            return 0.0
        elif js < 10:
            return js * 5
        return min(100, 50 + (js - 10) * 2)

    def stats(self) -> Dict:
        return {
            "jammer_power_w": self.jammer_power_w,
            "target_radar_power_w": self.target_radar_power_w,
            "distance_km": self.distance_to_target_km,
            "js_ratio_db": round(self.js_db(), 2),
            "effective_range_reduction": round(self.effective_range_reduction_factor(), 3),
            "burnthrough_range_km": round(self.burnthrough_range_km(), 1),
            "effectiveness_pct": round(self.effectiveness_pct(), 1),
        }

def run():
    ecm = ECMEffectivenessCalculator(jammer_power_w=1000, jammer_gain_db=15, target_radar_gain_db=30, target_radar_power_w=5000, distance_to_target_km=50, frequency_ghz=10)
    print(ecm.stats())

if __name__ == "__main__":
    run()
