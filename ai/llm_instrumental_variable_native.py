"""Instrumental Variable - IV estimation for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple
import math

@dataclass
class InstrumentalVariable:
    z: List[float] = field(default_factory=list)
    x: List[float] = field(default_factory=list)
    y: List[float] = field(default_factory=list)

    def _cov(self, a: List[float], b: List[float]) -> float:
        n = len(a); ma = sum(a)/n; mb = sum(b)/n
        return sum((a[i]-ma)*(b[i]-mb) for i in range(n))/(n-1) if n > 1 else 0

    def _var(self, a: List[float]) -> float:
        n = len(a); m = sum(a)/n
        return sum((x-m)**2 for x in a)/(n-1) if n > 1 else 0

    def estimate(self) -> float:
        return self._cov(self.z, self.y) / self._cov(self.z, self.x) if self._cov(self.z, self.x) != 0 else 0

    def stats(self) -> dict:
        return {"n": len(self.z), "beta_iv": round(self.estimate(), 4)}

def run():
    iv = InstrumentalVariable()
    iv.z = [1,0,1,0,1,0,1,0,1,0]
    iv.x = [2,1,3,1,2,0,3,1,2,1]
    iv.y = [5,2,6,1,5,1,7,2,6,2]
    print("Beta IV:", round(iv.estimate(), 4))
    print("Stats:", iv.stats())

if __name__ == "__main__": run()
