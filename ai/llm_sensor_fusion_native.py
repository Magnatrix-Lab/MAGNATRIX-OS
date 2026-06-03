"""Sensor Fusion - Multi-sensor data fusion for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import math

@dataclass
class SensorFusion:
    sensors: Dict[str, Dict] = field(default_factory=dict)

    def add_sensor(self, name: str, weight: float, bias: float = 0.0) -> None:
        self.sensors[name] = {"weight": weight, "bias": bias, "readings": []}

    def add_reading(self, name: str, value: float) -> None:
        if name in self.sensors:
            self.sensors[name]["readings"].append(value)

    def fuse(self) -> Tuple[float, float]:
        total_weight = sum(s["weight"] for s in self.sensors.values())
        weighted_sum = sum(s["weight"] * (sum(s["readings"])/len(s["readings"]) if s["readings"] else 0) for s in self.sensors.values())
        mean = weighted_sum / total_weight if total_weight > 0 else 0
        variance = sum(s["weight"] * (sum((r-mean)**2 for r in s["readings"])/len(s["readings"]) if s["readings"] else 0) for s in self.sensors.values()) / total_weight if total_weight > 0 else 0
        return round(mean, 4), round(math.sqrt(variance), 4)

    def stats(self) -> dict:
        return {"sensors": len(self.sensors), "weights": {k:v["weight"] for k,v in self.sensors.items()}}

def run():
    sf = SensorFusion()
    sf.add_sensor("cam", 0.6); sf.add_sensor("lidar", 0.4)
    sf.add_reading("cam", 10.0); sf.add_reading("cam", 10.2)
    sf.add_reading("lidar", 9.8); sf.add_reading("lidar", 10.1)
    print("Fused:", sf.fuse())
    print("Stats:", sf.stats())

if __name__ == "__main__": run()
