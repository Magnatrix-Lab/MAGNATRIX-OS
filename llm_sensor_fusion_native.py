"""Sensor Fusion — Kalman filter, complementary filter, sensor merging, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class KalmanFilter1D:
    x: float = 0.0
    P: float = 1.0
    Q: float = 0.01
    R: float = 0.1

    def predict(self, u: float = 0.0):
        self.x += u
        self.P += self.Q

    def update(self, z: float):
        K = self.P / (self.P + self.R)
        self.x += K * (z - self.x)
        self.P = (1 - K) * self.P

@dataclass
class SensorFusion:
    sensors: Dict[str, List[float]] = field(default_factory=dict)
    weights: Dict[str, float] = field(default_factory=dict)
    kf: KalmanFilter1D = field(default_factory=KalmanFilter1D)

    def weighted_average(self, readings: Dict[str, float]) -> float:
        total_w = sum(self.weights.get(s, 1.0) for s in readings)
        if total_w == 0:
            return sum(readings.values()) / len(readings)
        return sum(readings[s] * self.weights.get(s, 1.0) for s in readings) / total_w

    def complementary_filter(self, accel_angle: float, gyro_rate: float, dt: float, alpha: float = 0.98) -> float:
        return alpha * (self.kf.x + gyro_rate * dt) + (1 - alpha) * accel_angle

    def kalman_fuse(self, measurements: List[float]):
        for z in measurements:
            self.kf.predict()
            self.kf.update(z)
        return self.kf.x

    def stats(self) -> Dict:
        return {"sensors": len(self.sensors), "kf_estimate": round(self.kf.x, 4)}

def run():
    sf = SensorFusion(weights={"gps": 0.3, "imu": 0.7})
    print("Weighted:", sf.weighted_average({"gps": 10.1, "imu": 10.3}))
    print("Kalman:", sf.kalman_fuse([10.0, 10.2, 10.1, 10.3]))
    print(sf.stats())

if __name__ == "__main__":
    run()
