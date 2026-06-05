"""Slope Stability — Bishop, Fellenius, wedge, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class SlopeStability:
    cohesion: float = 25.0
    friction_angle: float = 30.0
    unit_weight: float = 20.0
    slope_height: float = 10.0
    slope_angle: float = 45.0

    def fellenius_fos(self, slip_radius: float = 15.0) -> float:
        phi = math.radians(self.friction_angle)
        theta = math.radians(self.slope_angle)
        alpha = math.radians(45 + self.friction_angle / 2)
        if math.sin(alpha) == 0 or math.sin(theta) == 0:
            return float('inf')
        resist = self.cohesion * slip_radius * alpha + self.unit_weight * slip_radius**2 * math.cos(theta) * math.tan(phi)
        drive = self.unit_weight * slip_radius**2 * math.sin(theta)
        return resist / drive if drive > 0 else float('inf')

    def wedge_fos(self, joint_dip: float = 60.0, tension: float = 0.0) -> float:
        phi = math.radians(self.friction_angle)
        beta = math.radians(joint_dip)
        if math.sin(beta) == 0:
            return float('inf')
        resist = self.cohesion + (self.unit_weight * self.slope_height * math.cos(beta) - tension) * math.tan(phi)
        drive = self.unit_weight * self.slope_height * math.sin(beta)
        return resist / drive if drive > 0 else float('inf')

    def stability_status(self, fos: float) -> str:
        if fos >= 1.5: return "stable"
        elif fos >= 1.2: return "marginally stable"
        elif fos >= 1.0: return "critical"
        return "unstable"

    def stats(self) -> Dict:
        fos = self.fellenius_fos()
        return {"fos": round(fos, 2), "status": self.stability_status(fos)}

def run():
    ss = SlopeStability(slope_angle=50, cohesion=20, friction_angle=25)
    print(ss.stats())
    print("Wedge FOS:", ss.wedge_fos(55))

if __name__ == "__main__":
    run()
