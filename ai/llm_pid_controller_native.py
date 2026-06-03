"""PID Controller - Proportional-integral-derivative for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List

@dataclass
class PIDController:
    kp: float = 1.0; ki: float = 0.1; kd: float = 0.01
    setpoint: float = 0.0
    integral: float = 0.0; prev_error: float = 0.0
    history: List[float] = field(default_factory=list)

    def update(self, measurement: float, dt: float = 1.0) -> float:
        error = self.setpoint - measurement
        self.integral += error * dt
        derivative = (error - self.prev_error) / dt
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        self.prev_error = error
        self.history.append(output)
        return output

    def stats(self) -> dict:
        return {"kp": self.kp, "ki": self.ki, "kd": self.kd, "history_len": len(self.history)}

def run():
    pid = PIDController(1.0, 0.1, 0.05)
    pid.setpoint = 10.0
    measurement = 0.0
    for _ in range(10):
        u = pid.update(measurement)
        measurement += u * 0.1
    print("Final measurement:", round(measurement, 4))
    print("Stats:", pid.stats())

if __name__ == "__main__": run()
