"""Native stdlib module: Sensor Fusion Calculator
Fuses sensor readings with complementary and Kalman-style filtering.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class SensorReading:
    sensor_name: str
    value: float
    variance: float

@dataclass
class SensorFusionCalculator:
    readings: List[SensorReading] = field(default_factory=list)
    prior_estimate: float = 0.0
    prior_variance: float = 1.0

    def weighted_average(self) -> float:
        if not self.readings:
            return self.prior_estimate
        total_weight = 0.0
        weighted_sum = 0.0
        for r in self.readings:
            weight = 1 / max(r.variance, 0.0001)
            total_weight += weight
            weighted_sum += r.value * weight
        return weighted_sum / total_weight

    def fused_variance(self) -> float:
        if not self.readings:
            return self.prior_variance
        total_weight = sum(1 / max(r.variance, 0.0001) for r in self.readings)
        return 1 / total_weight

    def sensor_count(self) -> int:
        return len(self.readings)

    def variance_reduction_pct(self) -> float:
        if self.prior_variance == 0:
            return 0.0
        return ((self.prior_variance - self.fused_variance()) / self.prior_variance) * 100

    def stats(self) -> Dict:
        return {
            "sensors": self.sensor_count(),
            "fused_value": round(self.weighted_average(), 4),
            "fused_variance": round(self.fused_variance(), 6),
            "variance_reduction_pct": round(self.variance_reduction_pct(), 2),
            "prior_estimate": self.prior_estimate,
        }

def run():
    sf = SensorFusionCalculator(
        readings=[
            SensorReading("lidar", 10.2, 0.1),
            SensorReading("ultrasonic", 10.5, 0.3),
            SensorReading("camera", 9.9, 0.2),
        ],
        prior_estimate=10.0,
        prior_variance=0.5
    )
    print(sf.stats())

if __name__ == "__main__":
    run()
