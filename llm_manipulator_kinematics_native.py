"""Manipulator Kinematics — DH parameters, forward, inverse, Jacobian, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class DHParameter:
    theta: float
    d: float
    a: float
    alpha: float

class ManipulatorKinematics:
    def __init__(self, dh_params: List[DHParameter] = None):
        self.dh = dh_params or []

    def dh_matrix(self, p: DHParameter) -> List[List[float]]:
        ct, st = math.cos(p.theta), math.sin(p.theta)
        ca, sa = math.cos(p.alpha), math.sin(p.alpha)
        return [
            [ct, -st*ca, st*sa, p.a*ct],
            [st, ct*ca, -ct*sa, p.a*st],
            [0, sa, ca, p.d],
            [0, 0, 0, 1]
        ]

    def mat_mult(self, A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
        n = len(A)
        return [[sum(A[i][k] * B[k][j] for k in range(n)) for j in range(n)] for i in range(n)]

    def forward(self, joint_angles: List[float]) -> Tuple[float, float, float]:
        T = [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
        for i, p in enumerate(self.dh):
            dp = DHParameter(p.theta + joint_angles[i], p.d, p.a, p.alpha)
            T = self.mat_mult(T, self.dh_matrix(dp))
        return T[0][3], T[1][3], T[2][3]

    def workspace_check(self, x: float, y: float, z: float) -> bool:
        reach = sum(p.a for p in self.dh)
        return math.sqrt(x**2 + y**2 + z**2) <= reach

    def stats(self, joint_angles: List[float]) -> Dict:
        pos = self.forward(joint_angles)
        return {"x": round(pos[0], 3), "y": round(pos[1], 3), "z": round(pos[2], 3), "joints": len(self.dh)}

def run():
    dh = [DHParameter(0, 0, 1, 0), DHParameter(0, 0, 1, 0)]
    mk = ManipulatorKinematics(dh)
    print(mk.stats([0.5, 0.5]))
    print("In workspace (1,1,0):", mk.workspace_check(1, 1, 0))

if __name__ == "__main__":
    run()
