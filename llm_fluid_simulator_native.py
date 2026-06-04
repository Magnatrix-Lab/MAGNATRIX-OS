"""Fluid Simulator — 2D grid, Navier-Stokes simplified, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto

class FluidSimulator:
    def __init__(self, width: int = 32, height: int = 32, dt: float = 0.1, diffusion: float = 0.0, viscosity: float = 0.0):
        self.width = width
        self.height = height
        self.dt = dt
        self.diffusion = diffusion
        self.viscosity = viscosity
        self.size = width * height
        self.density = [0.0] * self.size
        self.density_prev = [0.0] * self.size
        self.vx = [0.0] * self.size
        self.vy = [0.0] * self.size
        self.vx_prev = [0.0] * self.size
        self.vy_prev = [0.0] * self.size

    def _idx(self, x: int, y: int) -> int:
        x = max(0, min(self.width - 1, x))
        y = max(0, min(self.height - 1, y))
        return x + y * self.width

    def add_density(self, x: int, y: int, amount: float):
        self.density[self._idx(x, y)] += amount

    def add_velocity(self, x: int, y: int, vx: float, vy: float):
        idx = self._idx(x, y)
        self.vx[idx] += vx
        self.vy[idx] += vy

    def _diffuse(self, b: int, x: List[float], x0: List[float], diff: float):
        a = self.dt * diff * (self.width - 2) * (self.height - 2)
        for _ in range(4):
            for i in range(1, self.width - 1):
                for j in range(1, self.height - 1):
                    idx = self._idx(i, j)
                    x[idx] = (x0[idx] + a * (x[self._idx(i+1, j)] + x[self._idx(i-1, j)] + x[self._idx(i, j+1)] + x[self._idx(i, j-1)])) / (1 + 4 * a)

    def _advect(self, b: int, d: List[float], d0: List[float], vx: List[float], vy: List[float]):
        dt0 = self.dt * (self.width - 2)
        for i in range(1, self.width - 1):
            for j in range(1, self.height - 1):
                x = i - dt0 * vx[self._idx(i, j)]
                y = j - dt0 * vy[self._idx(i, j)]
                x = max(0.5, min(self.width - 1.5, x))
                y = max(0.5, min(self.height - 1.5, y))
                i0, i1 = int(x), int(x) + 1
                j0, j1 = int(y), int(y) + 1
                s1, s0 = x - i0, 1 - s1
                t1, t0 = y - j0, 1 - t1
                d[self._idx(i, j)] = (s0 * (t0 * d0[self._idx(i0, j0)] + t1 * d0[self._idx(i0, j1)]) + s1 * (t0 * d0[self._idx(i1, j0)] + t1 * d0[self._idx(i1, j1)]))

    def step(self):
        self.vx_prev, self.vx = self.vx, self.vx_prev
        self._diffuse(1, self.vx, self.vx_prev, self.viscosity)
        self.vy_prev, self.vy = self.vy, self.vy_prev
        self._diffuse(2, self.vy, self.vy_prev, self.viscosity)
        self._project(self.vx, self.vy, self.vx_prev, self.vy_prev)
        self.vx_prev, self.vx = self.vx, self.vx_prev
        self.vy_prev, self.vy = self.vy, self.vy_prev
        self._advect(1, self.vx, self.vx_prev, self.vx_prev, self.vy_prev)
        self._advect(2, self.vy, self.vy_prev, self.vx_prev, self.vy_prev)
        self._project(self.vx, self.vy, self.vx_prev, self.vy_prev)
        self.density_prev, self.density = self.density, self.density_prev
        self._diffuse(0, self.density, self.density_prev, self.diffusion)
        self.density_prev, self.density = self.density, self.density_prev
        self._advect(0, self.density, self.density_prev, self.vx, self.vy)

    def _project(self, vx: List[float], vy: List[float], p: List[float], div: List[float]):
        for i in range(1, self.width - 1):
            for j in range(1, self.height - 1):
                div[self._idx(i, j)] = -0.5 * (vx[self._idx(i+1, j)] - vx[self._idx(i-1, j)] + vy[self._idx(i, j+1)] - vy[self._idx(i, j-1)]) / self.width
                p[self._idx(i, j)] = 0
        for _ in range(4):
            for i in range(1, self.width - 1):
                for j in range(1, self.height - 1):
                    p[self._idx(i, j)] = (div[self._idx(i, j)] + p[self._idx(i+1, j)] + p[self._idx(i-1, j)] + p[self._idx(i, j+1)] + p[self._idx(i, j-1)]) / 4
        for i in range(1, self.width - 1):
            for j in range(1, self.height - 1):
                vx[self._idx(i, j)] -= 0.5 * (p[self._idx(i+1, j)] - p[self._idx(i-1, j)]) * self.width
                vy[self._idx(i, j)] -= 0.5 * (p[self._idx(i, j+1)] - p[self._idx(i, j-1)]) * self.width

    def get_density(self, x: int, y: int) -> float:
        return self.density[self._idx(x, y)]

    def stats(self) -> Dict:
        total_d = sum(self.density)
        return {"width": self.width, "height": self.height, "total_density": total_d}

def run():
    fluid = FluidSimulator(16, 16, 0.1, 0.0001, 0.0)
    fluid.add_density(8, 8, 100)
    fluid.add_velocity(8, 8, 10, 5)
    for _ in range(5):
        fluid.step()
    print(fluid.stats())

if __name__ == "__main__":
    run()
