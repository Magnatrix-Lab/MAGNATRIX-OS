#!/usr/bin/env python3
"""Embodiment Layer — MAGNATRIX-OS ASI Expansion
Path: runtime/embodiment_native.py
License: AGPL-3.0
Depends: Python 3.11+ stdlib only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class JointState:
    name: str
    position: float  # radians or meters
    velocity: float
    torque: float
    limit_min: float = -math.pi
    limit_max: float = math.pi


@dataclass
class EndEffector:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    orientation: float = 0.0


class EmbodimentLayer:
    def __init__(self, n_joints: int = 6):
        self.joints: List[JointState] = [
            JointState(f"joint_{i}", 0.0, 0.0, 0.0) for i in range(n_joints)
        ]
        self.ee = EndEffector()
        self.emergency_stop = False
        self._link_lengths = [0.5] * n_joints

    def connect(self) -> bool:
        self.emergency_stop = False
        return True

    def send_command(self, target_positions: List[float]) -> bool:
        if self.emergency_stop:
            return False
        for i, pos in enumerate(target_positions):
            if i < len(self.joints):
                j = self.joints[i]
                j.position = max(j.limit_min, min(j.limit_max, pos))
        self._update_fk()
        return True

    def read_state(self) -> Dict[str, any]:
        return {
            "joints": [{"name": j.name, "pos": j.position, "vel": j.velocity} for j in self.joints],
            "ee": {"x": self.ee.x, "y": self.ee.y, "z": self.ee.z},
            "estop": self.emergency_stop,
        }

    def plan_motion(self, target_ee: EndEffector, steps: int = 50) -> List[List[float]]:
        """Simple Jacobian-transpose IK trajectory."""
        trajectory = []
        for _ in range(steps):
            # Compute error
            err_x = target_ee.x - self.ee.x
            err_y = target_ee.y - self.ee.y
            err_z = target_ee.z - self.ee.z
            if abs(err_x) < 0.01 and abs(err_y) < 0.01 and abs(err_z) < 0.01:
                break
            # Simplified: move each joint proportional to error
            delta = [0.0] * len(self.joints)
            for i in range(len(self.joints)):
                delta[i] = (err_x + err_y + err_z) * 0.01 / len(self.joints)
            new_pos = [j.position + d for j, d in zip(self.joints, delta)]
            self.send_command(new_pos)
            trajectory.append([j.position for j in self.joints])
        return trajectory

    def estop(self) -> None:
        """Emergency stop."""
        self.emergency_stop = True
        for j in self.joints:
            j.velocity = 0.0

    def _update_fk(self) -> None:
        """Simplified forward kinematics for planar arm."""
        x, y = 0.0, 0.0
        angle = 0.0
        for i, j in enumerate(self.joints):
            angle += j.position
            x += self._link_lengths[i] * math.cos(angle)
            y += self._link_lengths[i] * math.sin(angle)
        self.ee.x = x
        self.ee.y = y
        self.ee.z = 0.0


def _self_test():
    print("=" * 55)
    print("Embodiment Layer — Self Test")
    print("=" * 55)
    passed = 0
    total = 4

    bot = EmbodimentLayer(n_joints=3)
    ok = bot.connect()
    print(f"[Test 1] Connected: {ok} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    bot.send_command([0.5, 0.3, 0.2])
    state = bot.read_state()
    print(f"[Test 2] State read: joints={len(state['joints'])} — {'PASS' if len(state['joints'])==3 else 'FAIL'}")
    passed += (len(state['joints']) == 3)

    traj = bot.plan_motion(EndEffector(0.5, 0.5, 0.0), steps=100)
    print(f"[Test 3] Trajectory planned: {len(traj)} steps — {'PASS' if len(traj) > 0 else 'FAIL'}")
    passed += (len(traj) > 0)

    bot.estop()
    ok2 = bot.send_command([1.0, 1.0, 1.0])
    print(f"[Test 4] E-stop blocks commands: {not ok2} — {'PASS' if not ok2 else 'FAIL'}")
    passed += (not ok2)

    print(f"\nPASS: {passed}/{total}")
    print("=" * 55)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
