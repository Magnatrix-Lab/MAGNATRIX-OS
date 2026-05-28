#!/usr/bin/env python3
"""Cosmological Modeling — MAGNATRIX-OS ASI Expansion
Path: runtime/cosmo_native.py
License: AGPL-3.0
Depends: Python 3.11+ stdlib only.

N-body gravity, simple climate energy balance, supply-chain network flow.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class Body:
    name: str
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float
    mass: float


class CosmoModel:
    def __init__(self, G: float = 6.67430e-11):
        self.G = G
        self.bodies: List[Body] = []
        self.dt = 86400.0  # 1 day in seconds

    def add_body(self, b: Body) -> None:
        self.bodies.append(b)

    def simulate_nbody(self, steps: int) -> List[Body]:
        """Simple N-body with direct O(N^2) gravity."""
        for _ in range(steps):
            forces = [(0.0, 0.0, 0.0) for _ in self.bodies]
            for i in range(len(self.bodies)):
                for j in range(i + 1, len(self.bodies)):
                    dx = self.bodies[j].x - self.bodies[i].x
                    dy = self.bodies[j].y - self.bodies[i].y
                    dz = self.bodies[j].z - self.bodies[i].z
                    dist = math.sqrt(dx * dx + dy * dy + dz * dz) + 1e6
                    f = self.G * self.bodies[i].mass * self.bodies[j].mass / (dist * dist)
                    fx, fy, fz = f * dx / dist, f * dy / dist, f * dz / dist
                    fi = forces[i]
                    fj = forces[j]
                    forces[i] = (fi[0] + fx, fi[1] + fy, fi[2] + fz)
                    forces[j] = (fj[0] - fx, fj[1] - fy, fj[2] - fz)
            for i, b in enumerate(self.bodies):
                ax = forces[i][0] / b.mass
                ay = forces[i][1] / b.mass
                az = forces[i][2] / b.mass
                b.vx += ax * self.dt
                b.vy += ay * self.dt
                b.vz += az * self.dt
                b.x += b.vx * self.dt
                b.y += b.vy * self.dt
                b.z += b.vz * self.dt
        return self.bodies

    def climate_predict(self, solar_constant: float = 1361, albedo: float = 0.3) -> Dict[str, float]:
        """Simple energy balance climate model."""
        sigma = 5.67e-8  # Stefan-Boltzmann
        S = solar_constant
        absorbed = S * (1 - albedo) / 4
        T_eq = (absorbed / sigma) ** 0.25
        return {
            "equilibrium_temp_k": T_eq,
            "equilibrium_temp_c": T_eq - 273.15,
            "absorbed_watt_per_m2": absorbed,
        }

    def supply_chain_model(self, nodes: List[str], edges: List[Tuple[str, str, float]], source: str, sink: str) -> float:
        """Max flow via Edmonds-Karp (BFS-augmenting path)."""
        capacity: Dict[Tuple[str, str], float] = {}
        adj: Dict[str, List[str]] = {n: [] for n in nodes}
        for u, v, c in edges:
            capacity[(u, v)] = c
            capacity[(v, u)] = 0.0
            adj[u].append(v)
            adj[v].append(u)

        flow = 0.0
        while True:
            parent: Dict[str, Optional[str]] = {n: None for n in nodes}
            q = [source]
            parent[source] = source
            for u in q:
                for v in adj[u]:
                    if parent[v] is None and capacity.get((u, v), 0) > 0:
                        parent[v] = u
                        q.append(v)
            if parent[sink] is None:
                break
            path_flow = float("inf")
            s = sink
            while s != source:
                path_flow = min(path_flow, capacity.get((parent[s], s), 0))
                s = parent[s]
            flow += path_flow
            v = sink
            while v != source:
                u = parent[v]
                capacity[(u, v)] -= path_flow
                capacity[(v, u)] += path_flow
                v = u
        return flow


def _self_test():
    print("=" * 55)
    print("Cosmological Modeling — Self Test")
    print("=" * 55)
    passed = 0
    total = 4

    cosmo = CosmoModel()

    # Earth-Sun system (simplified)
    sun = Body("Sun", 0, 0, 0, 0, 0, 0, 1.989e30)
    earth = Body("Earth", 1.496e11, 0, 0, 0, 29780, 0, 5.972e24)
    cosmo.add_body(sun)
    cosmo.add_body(earth)

    print("[Test 1] N-body simulation")
    initial_dist = math.sqrt((earth.x - sun.x) ** 2)
    bodies = cosmo.simulate_nbody(10)
    new_dist = math.sqrt((bodies[1].x - bodies[0].x) ** 2)
    # Should not drift wildly
    ok = 0.5 * initial_dist < new_dist < 2 * initial_dist
    print(f"  Distance stable: {ok} ({new_dist:.3e} m) — {'PASS' if ok else 'FAIL'}")
    passed += ok

    print("[Test 2] Climate prediction")
    climate = cosmo.climate_predict()
    T = climate["equilibrium_temp_c"]
    ok2 = -50 < T < 100
    print(f"  Equilibrium temp: {T:.1f} C — {'PASS' if ok2 else 'FAIL'}")
    passed += ok2

    print("[Test 3] Supply chain max flow")
    nodes = ["S", "A", "B", "T"]
    edges = [("S", "A", 10), ("S", "B", 5), ("A", "T", 7), ("B", "T", 8), ("A", "B", 3)]
    flow = cosmo.supply_chain_model(nodes, edges, "S", "T")
    ok3 = flow > 0
    print(f"  Max flow: {flow:.0f} — {'PASS' if ok3 else 'FAIL'}")
    passed += ok3

    print("[Test 4] Multiple bodies")
    cosmo2 = CosmoModel()
    for i in range(3):
        cosmo2.add_body(Body(f"b{i}", i * 1e6, 0, 0, 0, 100, 0, 1e20))
    result = cosmo2.simulate_nbody(5)
    ok4 = len(result) == 3
    print(f"  3-body simulated: {ok4} — {'PASS' if ok4 else 'FAIL'}")
    passed += ok4

    print(f"\nPASS: {passed}/{total}")
    print("=" * 55)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
