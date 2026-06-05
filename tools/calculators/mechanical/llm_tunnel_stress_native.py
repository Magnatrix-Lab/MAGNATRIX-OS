"""Tunnel Stress — rock mass, support, convergence, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class TunnelStress:
    overburden: float = 100.0
    tunnel_width: float = 5.0
    tunnel_height: float = 4.0
    rock_density: float = 2700.0
    poisson: float = 0.25

    def vertical_stress(self) -> float:
        return self.overburden * self.rock_density * 9.81 / 1000

    def horizontal_stress(self, k: float = 1.0) -> float:
        return k * self.vertical_stress()

    def roof_stress(self) -> float:
        return self.vertical_stress() * (1 - self.tunnel_width / (2 * self.overburden)) if self.overburden > 0 else 0.0

    def wall_stress(self) -> float:
        return 2 * self.horizontal_stress() * (1 - self.tunnel_height / (2 * self.overburden)) if self.overburden > 0 else 0.0

    def support_pressure(self, q: float = 1.0) -> float:
        return q * self.vertical_stress() * self.tunnel_width / (2 * self.overburden) if self.overburden > 0 else 0.0

    def convergence(self, deform_modulus: float = 5000.0) -> float:
        if deform_modulus <= 0:
            return 0.0
        return self.vertical_stress() * self.tunnel_width / (2 * deform_modulus)

    def stats(self) -> Dict:
        return {"vertical": round(self.vertical_stress(), 1), "roof": round(self.roof_stress(), 1), "convergence": round(self.convergence(), 3)}

def run():
    ts = TunnelStress(overburden=200, tunnel_width=8, tunnel_height=6)
    print(ts.stats())
    print("Wall stress:", ts.wall_stress())
    print("Support pressure:", ts.support_pressure())

if __name__ == "__main__":
    run()
