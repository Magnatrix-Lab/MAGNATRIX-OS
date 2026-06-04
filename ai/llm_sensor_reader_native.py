"""Sensor Reader - Sensor data acquisition for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum, auto
import random
import time

class SensorType(Enum):
    TEMPERATURE = auto(); HUMIDITY = auto(); PRESSURE = auto(); LIGHT = auto()

@dataclass
class SensorReader:
    sensors: Dict[str, Dict] = field(default_factory=dict)

    def register(self, sensor_id: str, sensor_type: SensorType, unit: str = "") -> None:
        self.sensors[sensor_id] = {"type": sensor_type, "unit": unit, "readings": []}

    def read(self, sensor_id: str) -> Optional[float]:
        if sensor_id not in self.sensors: return None
        value = random.uniform(20.0, 30.0) if self.sensors[sensor_id]["type"] == SensorType.TEMPERATURE else random.uniform(0, 100)
        self.sensors[sensor_id]["readings"].append({"value": value, "timestamp": time.time()})
        return value

    def average(self, sensor_id: str) -> float:
        readings = self.sensors.get(sensor_id, {}).get("readings", [])
        return sum(r["value"] for r in readings) / len(readings) if readings else 0.0

    def stats(self) -> dict:
        return {"sensors": len(self.sensors), "readings": sum(len(s["readings"]) for s in self.sensors.values())}

def run():
    sr = SensorReader()
    sr.register("temp1", SensorType.TEMPERATURE, "C")
    for _ in range(5): sr.read("temp1")
    print("Average:", round(sr.average("temp1"), 2))
    print("Stats:", sr.stats())

if __name__ == "__main__": run()
