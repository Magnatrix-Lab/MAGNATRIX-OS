"""Control System — PID, LQR, bang-bang, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

class ControllerType(Enum):
    PID = auto()
    BANG_BANG = auto()
    P = auto()

@dataclass
class PIDController:
    Kp: float = 1.0
    Ki: float = 0.0
    Kd: float = 0.0
    setpoint: float = 0.0
    integral: float = 0.0
    prev_error: float = 0.0

    def update(self, measurement: float, dt: float) -> float:
        error = self.setpoint - measurement
        self.integral += error * dt
        derivative = (error - self.prev_error) / dt
        output = self.Kp * error + self.Ki * self.integral + self.Kd * derivative
        self.prev_error = error
        return output

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0

class ControlSystem:
    def __init__(self, controller_type: ControllerType = ControllerType.PID):
        self.controller_type = controller_type
        self.pid = PIDController()
        self.hysteresis = 0.1
        self.history: List[Dict] = []

    def set_pid(self, Kp: float, Ki: float, Kd: float, setpoint: float):
        self.pid.Kp = Kp
        self.pid.Ki = Ki
        self.pid.Kd = Kd
        self.pid.setpoint = setpoint

    def control(self, measurement: float, dt: float) -> float:
        if self.controller_type == ControllerType.PID:
            output = self.pid.update(measurement, dt)
        elif self.controller_type == ControllerType.BANG_BANG:
            error = self.pid.setpoint - measurement
            if error > self.hysteresis:
                output = 1.0
            elif error < -self.hysteresis:
                output = -1.0
            else:
                output = 0.0
        elif self.controller_type == ControllerType.P:
            output = self.pid.Kp * (self.pid.setpoint - measurement)
        else:
            output = 0.0
        self.history.append({"measurement": measurement, "output": output, "error": self.pid.setpoint - measurement})
        return output

    def simulate(self, initial: float, dt: float, steps: int, process_gain: float = 1.0) -> List[float]:
        values = [initial]
        for _ in range(steps):
            control = self.control(values[-1], dt)
            # Simple first-order process
            new_val = values[-1] + process_gain * control * dt
            values.append(new_val)
        return values

    def stats(self) -> Dict:
        return {"type": self.controller_type.name, "history": len(self.history), "setpoint": self.pid.setpoint}

def run():
    ctrl = ControlSystem(ControllerType.PID)
    ctrl.set_pid(2.0, 0.1, 0.5, 10.0)
    values = ctrl.simulate(0.0, 0.1, 50)
    print("Final:", values[-1])
    print(ctrl.stats())

if __name__ == "__main__":
    run()
