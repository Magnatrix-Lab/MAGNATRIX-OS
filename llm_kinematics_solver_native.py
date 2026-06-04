"""Kinematics Solver — forward, inverse, DH parameters, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

@dataclass
class Joint:
    joint_type: str  # revolute or prismatic
    theta: float = 0.0
    d: float = 0.0
    a: float = 0.0
    alpha: float = 0.0

class KinematicsSolver:
    def __init__(self):
        self.joints: List[Joint] = []

    def add_joint(self, joint: Joint):
        self.joints.append(joint)

    def _dh_matrix(self, theta: float, d: float, a: float, alpha: float) -> List[List[float]]:
        ct, st = math.cos(theta), math.sin(theta)
        ca, sa = math.cos(alpha), math.sin(alpha)
        return [
            [ct, -st * ca, st * sa, a * ct],
            [st, ct * ca, -ct * sa, a * st],
            [0, sa, ca, d],
            [0, 0, 0, 1],
        ]

    def _mat_mult(self, a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
        result = [[0.0]*4 for _ in range(4)]
        for i in range(4):
            for j in range(4):
                for k in range(4):
                    result[i][j] += a[i][k] * b[k][j]
        return result

    def forward_kinematics(self, joint_angles: List[float]) -> List[List[float]]:
        T = [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
        for i, joint in enumerate(self.joints):
            if joint.joint_type == "revolute":
                theta = joint_angles[i] if i < len(joint_angles) else joint.theta
            else:
                theta = joint.theta
            m = self._dh_matrix(theta, joint.d, joint.a, joint.alpha)
            T = self._mat_mult(T, m)
        return T

    def get_position(self, T: List[List[float]]) -> Tuple[float, float, float]:
        return (T[0][3], T[1][3], T[2][3])

    def inverse_kinematics_2d(self, target_x: float, target_y: float, l1: float, l2: float) -> Optional[Tuple[float, float]]:
        d = math.sqrt(target_x**2 + target_y**2)
        if d > l1 + l2 or d < abs(l1 - l2):
            return None
        cos_q2 = (d**2 - l1**2 - l2**2) / (2 * l1 * l2)
        q2 = math.acos(max(-1, min(1, cos_q2)))
        q1 = math.atan2(target_y, target_x) - math.atan2(l2 * math.sin(q2), l1 + l2 * math.cos(q2))
        return (q1, q2)

    def stats(self) -> Dict:
        return {"joints": len(self.joints)}

def run():
    solver = KinematicsSolver()
    solver.add_joint(Joint("revolute", 0, 0, 1, 0))
    solver.add_joint(Joint("revolute", 0, 0, 1, 0))
    T = solver.forward_kinematics([0, math.pi/2])
    print("Position:", solver.get_position(T))
    print("IK:", solver.inverse_kinematics_2d(1.5, 0.5, 1, 1))
    print(solver.stats())

if __name__ == "__main__":
    run()
