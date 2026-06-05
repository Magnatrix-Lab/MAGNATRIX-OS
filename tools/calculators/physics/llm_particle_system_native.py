"""Particle System — emitter, forces, lifecycle, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import random
import math

@dataclass
class Particle:
    position: Tuple[float, float]
    velocity: Tuple[float, float]
    lifetime: float
    max_lifetime: float
    size: float
    color: Tuple[int, int, int]
    active: bool = True

class ParticleSystem:
    def __init__(self, max_particles: int = 1000):
        self.max_particles = max_particles
        self.particles: List[Particle] = []
        self.emitters: List[Dict] = []
        self.gravity = (0.0, -9.8)
        self.wind = (0.0, 0.0)

    def add_emitter(self, x: float, y: float, rate: int = 10, spread: float = 1.0):
        self.emitters.append({"x": x, "y": y, "rate": rate, "spread": spread})

    def _spawn(self, emitter: Dict):
        for _ in range(emitter["rate"]):
            if len(self.particles) >= self.max_particles:
                break
            vx = random.uniform(-emitter["spread"], emitter["spread"])
            vy = random.uniform(1, 5)
            p = Particle(
                (emitter["x"], emitter["y"]),
                (vx, vy),
                random.uniform(1, 3),
                random.uniform(1, 3),
                random.uniform(1, 5),
                (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
            )
            self.particles.append(p)

    def update(self, dt: float):
        for emitter in self.emitters:
            self._spawn(emitter)
        for p in self.particles:
            if not p.active:
                continue
            p.lifetime -= dt
            if p.lifetime <= 0:
                p.active = False
                continue
            vx = p.velocity[0] + self.wind[0] * dt
            vy = p.velocity[1] + self.gravity[1] * dt
            p.velocity = (vx, vy)
            px = p.position[0] + vx * dt
            py = p.position[1] + vy * dt
            p.position = (px, py)
            p.size = max(0, p.size - dt * 0.5)
        self.particles = [p for p in self.particles if p.active]

    def get_active(self) -> List[Particle]:
        return [p for p in self.particles if p.active]

    def stats(self) -> Dict:
        active = len(self.get_active())
        return {"particles": len(self.particles), "active": active, "emitters": len(self.emitters), "max": self.max_particles}

def run():
    ps = ParticleSystem(100)
    ps.add_emitter(0, 0, 5, 2.0)
    for _ in range(10):
        ps.update(0.1)
    print(ps.stats())

if __name__ == "__main__":
    run()
