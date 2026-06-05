"""Native stdlib module: Kiln Firing Calculator
Calculates firing schedules, cone temperatures, and heat work.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class KilnFiringCalculator:
    target_temp_c: float
    hold_time_min: float = 0.0
    ramp_rate_c_per_hour: float = 100.0
    kiln_efficiency_pct: float = 75.0
    chamber_volume_l: float = 100.0

    _CONE_TEMPS = {
        "022": 600, "021": 614, "020": 626, "019": 666, "018": 717,
        "017": 747, "016": 772, "015": 791, "014": 815, "013": 837,
        "012": 856, "011": 871, "010": 887, "09": 900, "08": 923,
        "07": 984, "06": 999, "05": 1046, "04": 1063, "03": 1101,
        "02": 1120, "01": 1137, "1": 1159, "2": 1162, "3": 1165,
        "4": 1186, "5": 1196, "6": 1222, "7": 1240, "8": 1263,
        "9": 1280, "10": 1305, "11": 1315, "12": 1326, "13": 1346,
    }

    def cone_from_temp(self) -> Optional[str]:
        for cone, temp in sorted(self._CONE_TEMPS.items(), key=lambda x: x[1]):
            if temp >= self.target_temp_c:
                return cone
        return None

    def firing_time_hours(self) -> float:
        return self.target_temp_c / self.ramp_rate_c_per_hour + self.hold_time_min / 60

    def heat_work_estimate(self) -> float:
        return self.target_temp_c * (self.firing_time_hours()) ** 0.5

    def energy_consumption_kwh(self) -> float:
        rough_kw = self.chamber_volume_l * 0.05
        return rough_kw * self.firing_time_hours() / (self.kiln_efficiency_pct / 100)

    def cooling_time_hours(self, safe_to_open_c: float = 80.0) -> float:
        return (self.target_temp_c - safe_to_open_c) / 200

    def stats(self) -> Dict:
        return {
            "target_temp_c": self.target_temp_c,
            "cone_approx": self.cone_from_temp(),
            "firing_time_hours": round(self.firing_time_hours(), 1),
            "heat_work": round(self.heat_work_estimate(), 0),
            "energy_consumption_kwh": round(self.energy_consumption_kwh(), 1),
            "cooling_time_hours": round(self.cooling_time_hours(), 1),
        }

def run():
    kfc = KilnFiringCalculator(target_temp_c=1222, hold_time_min=15, ramp_rate_c_per_hour=150)
    print(kfc.stats())

if __name__ == "__main__":
    run()
