"""Robot Controller — PID, state machine, trajectory tracking, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto

class RobotState(Enum):
    IDLE = auto(); MOVING = auto(); STOPPED = auto(); ERROR = auto()

@dataclass
class PIDController:
    Kp: float = 1.0
    Ki: float = 0.0
    Kd: float = 0.0
    integral: float = 0.0
    prev_error: float = 0.0

    def compute(self, setpoint: float, measurement: float, dt: float) -> float:
        error = setpoint - measurement
        self.integral += error * dt
        derivative = (error - self.prev_error) / dt if dt > 0 else 0
        self.prev_error = error
        return self.Kp * error + self.Ki * self.integral + self.Kd * derivative

@dataclass
class RobotController:
    state: RobotState = RobotState.IDLE
    pid: PIDController = field(default_factory=lambda: PIDController(2.0, 0.1, 0.5))
    position: float = 0.0
    target: float = 0.0
    history: List[float] = field(default_factory=list)

    def set_target(self, target: float):
        self.target = target
        self.state = RobotState.MOVING

    def update(self, dt: float = 0.1):
        if self.state != RobotState.MOVING:
            return
        cmd = self.pid.compute(self.target, self.position, dt)
        self.position += cmd * dt
        self.history.append(self.position)
        if abs(self.target - self.position) < 0.01:
            self.state = RobotState.STOPPED

    def stats(self) -> Dict:
        return {"state": self.state.name, "position": round(self.position, 4), "target": self.target, "steps": len(self.history)}

def run():
    rc = RobotController()
    rc.set_target(5.0)
    for _ in range(50):
        rc.update(0.1)
    print(rc.stats())

if __name__ == "__main__":
    run()
