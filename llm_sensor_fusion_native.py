"""Sensor Fusion — multi-sensor data combination, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math
import random

class SensorType(Enum):
    ACCELEROMETER = auto()
    GYROSCOPE = auto()
    MAGNETOMETER = auto()
    TEMPERATURE = auto()
    PRESSURE = auto()

@dataclass
class SensorReading:
    sensor_id: str
    sensor_type: SensorType
    values: List[float]
    timestamp: float
    confidence: float = 1.0

class SensorFusion:
    def __init__(self):
        self.sensors: Dict[str, SensorReading] = {}
        self.fused_state: Dict[str, float] = {}
        self.weights: Dict[str, float] = {}

    def add_reading(self, reading: SensorReading):
        self.sensors[reading.sensor_id] = reading
        if reading.sensor_id not in self.weights:
            self.weights[reading.sensor_id] = 1.0

    def set_weight(self, sensor_id: str, weight: float):
        self.weights[sensor_id] = weight

    def fuse_weighted_average(self, key: str) -> Optional[float]:
        total = 0.0
        weight_sum = 0.0
        for sid, reading in self.sensors.items():
            if reading.values and key in self._get_keys(reading):
                idx = self._get_key_index(reading, key)
                if idx < len(reading.values):
                    w = self.weights.get(sid, 1.0) * reading.confidence
                    total += reading.values[idx] * w
                    weight_sum += w
        if weight_sum == 0:
            return None
        return total / weight_sum

    def _get_keys(self, reading: SensorReading) -> List[str]:
        mapping = {
            SensorType.ACCELEROMETER: ["ax", "ay", "az"],
            SensorType.GYROSCOPE: ["gx", "gy", "gz"],
            SensorType.MAGNETOMETER: ["mx", "my", "mz"],
            SensorType.TEMPERATURE: ["temp"],
            SensorType.PRESSURE: ["pressure"],
        }
        return mapping.get(reading.sensor_type, [])

    def _get_key_index(self, reading: SensorReading, key: str) -> int:
        keys = self._get_keys(reading)
        return keys.index(key) if key in keys else -1

    def fuse_kalman_simple(self, key: str, prev_estimate: float, process_noise: float = 0.1, measurement_noise: float = 0.1) -> float:
        fused = self.fuse_weighted_average(key)
        if fused is None:
            return prev_estimate
        estimate = prev_estimate
        error_cov = 1.0
        kalman_gain = error_cov / (error_cov + measurement_noise)
        estimate = estimate + kalman_gain * (fused - estimate)
        error_cov = (1 - kalman_gain) * error_cov + process_noise
        return estimate

    def stats(self) -> Dict:
        return {"sensors": len(self.sensors), "fused_keys": list(self.fused_state.keys()), "weights": self.weights}

def run():
    fusion = SensorFusion()
    fusion.add_reading(SensorReading("acc1", SensorType.ACCELEROMETER, [0.1, 0.2, 9.8], 0.0, 0.95))
    fusion.add_reading(SensorReading("acc2", SensorType.ACCELEROMETER, [0.15, 0.18, 9.7], 0.0, 0.9))
    fusion.add_reading(SensorReading("temp1", SensorType.TEMPERATURE, [25.0], 0.0, 0.99))
    print("Fused az:", fusion.fuse_weighted_average("az"))
    print("Fused temp:", fusion.fuse_weighted_average("temp"))
    print(fusion.stats())

if __name__ == "__main__":
    run()
