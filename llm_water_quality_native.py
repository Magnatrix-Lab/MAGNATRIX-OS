"""Native stdlib module: Water Quality Monitor
Tracks water quality parameters and calculates WQI for aquaculture.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class WaterParameter:
    name: str
    value: float
    unit: str
    ideal_min: float
    ideal_max: float
    weight: float = 1.0

@dataclass
class WaterQualityMonitor:
    system_name: str
    parameters: List[WaterParameter] = field(default_factory=list)

    def _parameter_score(self, param: WaterParameter) -> float:
        if param.value < param.ideal_min or param.value > param.ideal_max:
            return 0.0
        range_mid = (param.ideal_min + param.ideal_max) / 2
        range_total = param.ideal_max - param.ideal_min
        if range_total == 0:
            return 100.0
        deviation = abs(param.value - range_mid) / (range_total / 2)
        return max(0, 100 - (deviation * 100))

    def wqi(self) -> float:
        if not self.parameters:
            return 0.0
        total_weight = sum(p.weight for p in self.parameters)
        if total_weight == 0:
            return 0.0
        weighted_sum = sum(self._parameter_score(p) * p.weight for p in self.parameters)
        return weighted_sum / total_weight

    def out_of_range(self) -> List[str]:
        return [p.name for p in self.parameters if p.value < p.ideal_min or p.value > p.ideal_max]

    def stats(self) -> Dict:
        return {
            "system": self.system_name,
            "wqi": round(self.wqi(), 1),
            "parameters_count": len(self.parameters),
            "out_of_range": self.out_of_range(),
        }

def run():
    wqm = WaterQualityMonitor(
        system_name="Pond A",
        parameters=[
            WaterParameter("temperature", 26, "C", 22, 28, 1.0),
            WaterParameter("ph", 7.2, "", 6.5, 8.5, 1.0),
            WaterParameter("ammonia", 0.3, "mg/L", 0, 0.5, 2.0),
            WaterParameter("nitrite", 0.1, "mg/L", 0, 0.2, 2.0),
            WaterParameter("dissolved_oxygen", 5.5, "mg/L", 5, 8, 2.0),
        ]
    )
    print(wqm.stats())

if __name__ == "__main__":
    run()
