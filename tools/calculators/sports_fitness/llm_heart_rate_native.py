"""Native stdlib module: Heart Rate Calculator
Calculates heart rate zones, max HR, and training intensity.
"""
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class HeartRateCalculator:
    age: int
    resting_hr: int

    def max_hr(self) -> int:
        return 220 - self.age

    def hrr(self) -> int:
        return self.max_hr() - self.resting_hr

    def zone_1(self) -> tuple:
        return (self.resting_hr + int(self.hrr() * 0.50), self.resting_hr + int(self.hrr() * 0.60))

    def zone_2(self) -> tuple:
        return (self.resting_hr + int(self.hrr() * 0.60), self.resting_hr + int(self.hrr() * 0.70))

    def zone_3(self) -> tuple:
        return (self.resting_hr + int(self.hrr() * 0.70), self.resting_hr + int(self.hrr() * 0.80))

    def zone_4(self) -> tuple:
        return (self.resting_hr + int(self.hrr() * 0.80), self.resting_hr + int(self.hrr() * 0.90))

    def zone_5(self) -> tuple:
        return (self.resting_hr + int(self.hrr() * 0.90), self.max_hr())

    def target_hr(self, intensity_pct: float) -> int:
        return self.resting_hr + int(self.hrr() * intensity_pct)

    def all_zones(self) -> Dict:
        return {
            "zone_1_recovery": self.zone_1(),
            "zone_2_aerobic": self.zone_2(),
            "zone_3_tempo": self.zone_3(),
            "zone_4_threshold": self.zone_4(),
            "zone_5_anaerobic": self.zone_5(),
        }

    def stats(self) -> Dict:
        return {
            "age": self.age,
            "max_hr": self.max_hr(),
            "resting_hr": self.resting_hr,
            "hrr": self.hrr(),
            "zones": self.all_zones(),
        }

def run():
    hr = HeartRateCalculator(age=30, resting_hr=55)
    print(hr.stats())

if __name__ == "__main__":
    run()
