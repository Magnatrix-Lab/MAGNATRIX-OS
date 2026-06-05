"""Native stdlib module: Robot Kinematics Calculator
Calculates forward and inverse kinematics for simple 2-DOF robotic arms.
"""
from dataclasses import dataclass
from typing import Dict, Tuple
import math

@dataclass
class RobotKinematics:
    link1_length: float
    link2_length: float
    theta1_deg: float
    theta2_deg: float

    def forward_kinematics(self) -> Tuple[float, float]:
        t1 = math.radians(self.theta1_deg)
        t2 = math.radians(self.theta2_deg)
        x = self.link1_length * math.cos(t1) + self.link2_length * math.cos(t1 + t2)
        y = self.link1_length * math.sin(t1) + self.link2_length * math.sin(t1 + t2)
        return (round(x, 4), round(y, 4))

    def workspace_radius(self) -> float:
        return self.link1_length + self.link2_length

    def reach_min(self) -> float:
        return abs(self.link1_length - self.link2_length)

    def end_effector_angle(self) -> float:
        return self.theta1_deg + self.theta2_deg

    def inverse_kinematics(self, target_x: float, target_y: float) -> Dict:
        r = math.sqrt(target_x**2 + target_y**2)
        if r > self.workspace_radius() or r < self.reach_min():
            return {"error": "Target out of reach"}
        cos_t2 = (r**2 - self.link1_length**2 - self.link2_length**2) / (2 * self.link1_length * self.link2_length)
        if abs(cos_t2) > 1:
            return {"error": "No solution"}
        t2 = math.acos(cos_t2)
        t1 = math.atan2(target_y, target_x) - math.atan2(self.link2_length * math.sin(t2), self.link1_length + self.link2_length * math.cos(t2))
        return {
            "theta1_deg": round(math.degrees(t1), 2),
            "theta2_deg": round(math.degrees(t2), 2),
        }

    def stats(self) -> Dict:
        fk = self.forward_kinematics()
        return {
            "link1": self.link1_length,
            "link2": self.link2_length,
            "theta1": self.theta1_deg,
            "theta2": self.theta2_deg,
            "end_effector_x": fk[0],
            "end_effector_y": fk[1],
            "workspace_radius": self.workspace_radius(),
            "reach_min": self.reach_min(),
        }

def run():
    rk = RobotKinematics(link1_length=1.0, link2_length=0.8, theta1_deg=45, theta2_deg=30)
    print(rk.stats())
    print(rk.inverse_kinematics(1.2, 0.8))

if __name__ == "__main__":
    run()
