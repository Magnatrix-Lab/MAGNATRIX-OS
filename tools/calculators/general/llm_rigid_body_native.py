"""Rigid Body Physics — position, velocity, rotation, forces, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

@dataclass
class RigidBody:
    position: Tuple[float, float]
    velocity: Tuple[float, float] = (0.0, 0.0)
    angle: float = 0.0
    angular_velocity: float = 0.0
    mass: float = 1.0
    moment_of_inertia: float = 1.0
    forces: List[Tuple[float, float]] = field(default_factory=list)
    torques: List[float] = field(default_factory=list)

class RigidBodyEngine:
    def __init__(self, gravity: Tuple[float, float] = (0, -9.8), dt: float = 0.016):
        self.gravity = gravity
        self.dt = dt
        self.bodies: List[RigidBody] = []

    def add_body(self, body: RigidBody):
        self.bodies.append(body)

    def apply_force(self, body_idx: int, force: Tuple[float, float], point: Optional[Tuple[float, float]] = None):
        body = self.bodies[body_idx]
        body.forces.append(force)
        if point:
            rx = point[0] - body.position[0]
            ry = point[1] - body.position[1]
            torque = rx * force[1] - ry * force[0]
            body.torques.append(torque)

    def step(self):
        for body in self.bodies:
            total_force = (self.gravity[0] * body.mass, self.gravity[1] * body.mass)
            for f in body.forces:
                total_force = (total_force[0] + f[0], total_force[1] + f[1])
            ax = total_force[0] / body.mass
            ay = total_force[1] / body.mass
            vx = body.velocity[0] + ax * self.dt
            vy = body.velocity[1] + ay * self.dt
            px = body.position[0] + vx * self.dt
            py = body.position[1] + vy * self.dt
            total_torque = sum(body.torques)
            angular_acc = total_torque / body.moment_of_inertia
            av = body.angular_velocity + angular_acc * self.dt
            angle = body.angle + av * self.dt
            body.velocity = (vx, vy)
            body.position = (px, py)
            body.angular_velocity = av
            body.angle = angle
            body.forces = []
            body.torques = []

    def stats(self) -> Dict:
        return {"bodies": len(self.bodies), "dt": self.dt, "gravity": self.gravity}

def run():
    engine = RigidBodyEngine((0, -9.8), 0.016)
    body = RigidBody((0, 10), (0, 0), 0, 0, 2.0, 1.0)
    engine.add_body(body)
    engine.apply_force(0, (5, 0))
    for _ in range(60):
        engine.step()
    print(engine.bodies[0].position, engine.bodies[0].velocity)
    print(engine.stats())

if __name__ == "__main__":
    run()
