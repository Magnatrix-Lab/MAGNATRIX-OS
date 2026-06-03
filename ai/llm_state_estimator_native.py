"""State Estimator - Kalman filter for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple

@dataclass
class StateEstimator:
    x: float = 0.0; p: float = 1.0
    q: float = 0.01; r: float = 0.1

    def predict(self, u: float = 0.0) -> Tuple[float, float]:
        self.x += u
        self.p += self.q
        return self.x, self.p

    def update(self, z: float) -> Tuple[float, float]:
        k = self.p / (self.p + self.r)
        self.x += k * (z - self.x)
        self.p = (1 - k) * self.p
        return self.x, self.p

    def stats(self) -> dict:
        return {"estimate": round(self.x, 4), "uncertainty": round(self.p, 4)}

def run():
    se = StateEstimator()
    measurements = [1.0, 1.1, 0.9, 1.2, 1.0]
    for z in measurements:
        se.predict(0.1)
        se.update(z)
    print("Stats:", se.stats())

if __name__ == "__main__": run()
