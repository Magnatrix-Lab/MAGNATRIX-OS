"""Molecular Dynamics — Lennard-Jones, Verlet integration, forces, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class Particle:
    x: float
    y: float
    z: float
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    mass: float = 1.0

@dataclass
class MolecularDynamics:
    particles: List[Particle] = field(default_factory=list)
    dt: float = 0.001
    epsilon: float = 1.0
    sigma: float = 1.0
    box: float = 10.0

    def _lj_force(self, r: float) -> float:
        if r < 0.1:
            r = 0.1
        sr = self.sigma / r
        return 24 * self.epsilon / r * (2 * sr**12 - sr**6)

    def forces(self) -> List[Tuple[float, float, float]]:
        forces = [(0.0, 0.0, 0.0) for _ in self.particles]
        for i in range(len(self.particles)):
            for j in range(i+1, len(self.particles)):
                dx = self.particles[i].x - self.particles[j].x
                dy = self.particles[i].y - self.particles[j].y
                dz = self.particles[i].z - self.particles[j].z
                r = math.sqrt(dx**2 + dy**2 + dz**2)
                if r < self.box / 2:
                    f = self._lj_force(r)
                    fx, fy, fz = f * dx / r, f * dy / r, f * dz / r
                    forces[i] = (forces[i][0] + fx, forces[i][1] + fy, forces[i][2] + fz)
                    forces[j] = (forces[j][0] - fx, forces[j][1] - fy, forces[j][2] - fz)
        return forces

    def verlet_step(self):
        f = self.forces()
        for i, p in enumerate(self.particles):
            ax, ay, az = f[i][0] / p.mass, f[i][1] / p.mass, f[i][2] / p.mass
            p.vx += ax * self.dt
            p.vy += ay * self.dt
            p.vz += az * self.dt
            p.x += p.vx * self.dt
            p.y += p.vy * self.dt
            p.z += p.vz * self.dt

    def kinetic_energy(self) -> float:
        return 0.5 * sum(p.mass * (p.vx**2 + p.vy**2 + p.vz**2) for p in self.particles)

    def temperature(self) -> float:
        n = len(self.particles)
        if n < 2:
            return 0.0
        return 2 * self.kinetic_energy() / (3 * (n - 1))

    def stats(self) -> Dict:
        return {"particles": len(self.particles), "ke": round(self.kinetic_energy(), 4), "T": round(self.temperature(), 4)}

def run():
    md = MolecularDynamics([Particle(0,0,0,0.1,0,0), Particle(1.5,0,0,-0.1,0,0)])
    for _ in range(100):
        md.verlet_step()
    print(md.stats())

if __name__ == "__main__":
    run()
