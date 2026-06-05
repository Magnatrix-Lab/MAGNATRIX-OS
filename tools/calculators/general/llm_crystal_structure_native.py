"""Crystal Structure — lattice, Miller indices, unit cell, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class Atom:
    element: str
    x: float
    y: float
    z: float

@dataclass
class CrystalStructure:
    a: float = 1.0
    b: float = 1.0
    c: float = 1.0
    alpha: float = 90.0
    beta: float = 90.0
    gamma: float = 90.0
    atoms: List[Atom] = field(default_factory=list)

    def volume(self) -> float:
        ar = math.radians(self.alpha)
        br = math.radians(self.beta)
        gr = math.radians(self.gamma)
        return self.a * self.b * self.c * math.sqrt(1 - math.cos(ar)**2 - math.cos(br)**2 - math.cos(gr)**2 + 2*math.cos(ar)*math.cos(br)*math.cos(gr))

    def lattice_spacing(self, h: int, k: int, l: int) -> float:
        """d-spacing for cubic system."""
        if self.alpha == self.beta == self.gamma == 90.0 and self.a == self.b == self.c:
            return self.a / math.sqrt(h*h + k*k + l*l)
        return 0.0

    def miller_planes(self, indices: List[Tuple[int, int, int]]) -> Dict[str, float]:
        return {f"({h}{k}{l})": self.lattice_spacing(h, k, l) for h, k, l in indices}

    def density(self, atomic_mass: float, avogadro: float = 6.022e23) -> float:
        V = self.volume() * 1e-30
        if V <= 0:
            return 0.0
        return len(self.atoms) * atomic_mass / (avogadro * V)

    def stats(self) -> Dict:
        return {"atoms": len(self.atoms), "volume": round(self.volume(), 4), "system": "cubic" if self.a==self.b==self.c and self.alpha==self.beta==self.gamma==90 else "other"}

def run():
    cs = CrystalStructure(a=3.61, atoms=[Atom("Cu",0,0,0),Atom("Cu",0.5,0.5,0),Atom("Cu",0.5,0,0.5),Atom("Cu",0,0.5,0.5)])
    print("Volume:", cs.volume())
    print("d(111):", cs.lattice_spacing(1,1,1))
    print(cs.stats())

if __name__ == "__main__":
    run()
