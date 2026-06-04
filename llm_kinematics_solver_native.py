"""Kinematics Solver — forward/inverse kinematics, Jacobian, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class Link:
    length: float
    angle: float

@dataclass
class KinematicsSolver:
    links: List[Link] = field(default_factory=list)

    def forward(self) -> Tuple[float, float]:
        x, y = 0.0, 0.0
        total_angle = 0.0
        for link in self.links:
            total_angle += math.radians(link.angle)
            x += link.length * math.cos(total_angle)
            y += link.length * math.sin(total_angle)
        return round(x, 4), round(y, 4)

    def inverse_2link(self, target_x: float, target_y: float, l1: float, l2: float) -> Optional[Tuple[float, float]]:
        d = math.sqrt(target_x**2 + target_y**2)
        if d > l1 + l2 or d < abs(l1 - l2):
            return None
        cos_q2 = (d**2 - l1**2 - l2**2) / (2 * l1 * l2)
        q2 = math.degrees(math.acos(max(-1, min(1, cos_q2))))
        q1 = math.degrees(math.atan2(target_y, target_x) - math.atan2(l2 * math.sin(math.radians(q2)), l1 + l2 * math.cos(math.radians(q2))))
        return round(q1, 2), round(q2, 2)

    def jacobian(self, delta: float = 0.01) -> List[List[float]]:
        n = len(self.links)
        J = [[0.0]*n for _ in range(2)]
        pos0 = self.forward()
        for i in range(n):
            self.links[i].angle += delta
            pos1 = self.forward()
            self.links[i].angle -= delta
            J[0][i] = (pos1[0] - pos0[0]) / delta
            J[1][i] = (pos1[1] - pos0[1]) / delta
        return J

    def stats(self) -> Dict:
        return {"links": len(self.links), "end_effector": self.forward()}

def run():
    solver = KinematicsSolver([Link(2, 45), Link(2, 45)])
    print("Forward:", solver.forward())
    print("Inverse:", solver.inverse_2link(2, 2, 2, 2))
    print(solver.stats())

if __name__ == "__main__":
    run()
