"""Latent Explorer - Latent space traversal for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple
import random
import math

@dataclass
class LatentExplorer:
    dim: int = 2

    def random_point(self) -> List[float]:
        return [random.gauss(0,1) for _ in range(self.dim)]

    def interpolate(self, a: List[float], b: List[float], steps: int = 5) -> List[List[float]]:
        return [[a[i] + (b[i]-a[i])*t/steps for i in range(self.dim)] for t in range(steps+1)]

    def spherical_interpolate(self, a: List[float], b: List[float], steps: int = 5) -> List[List[float]]:
        dot = sum(x*y for x,y in zip(a,b))
        norm_a = math.sqrt(sum(x*x for x in a))
        norm_b = math.sqrt(sum(x*x for x in b))
        cos_ang = dot/(norm_a*norm_b) if norm_a*norm_b > 0 else 0
        ang = math.acos(max(-1, min(1, cos_ang)))
        return [[(math.sin((1-t/steps)*ang)/math.sin(ang))*a[i] + (math.sin(t/steps*ang)/math.sin(ang))*b[i] for i in range(self.dim)] for t in range(steps+1)] if ang > 1e-6 else self.interpolate(a,b,steps)

    def stats(self) -> dict:
        return {"dim": self.dim}

def run():
    le = LatentExplorer(2)
    a, b = le.random_point(), le.random_point()
    interp = le.interpolate(a, b, 3)
    print("Interp:", [[round(v,4) for v in p] for p in interp])
    print("Stats:", le.stats())

if __name__ == "__main__": run()
