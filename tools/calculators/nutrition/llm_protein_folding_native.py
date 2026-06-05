"""Protein Folding — HP model, contact map, energy minimization, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
import math, random

@dataclass
class ProteinFolder:
    sequence: str = ""
    """H = hydrophobic, P = polar"""
    lattice: Dict[Tuple[int, int], int] = field(default_factory=dict)
    conformation: List[Tuple[int, int]] = field(default_factory=list)

    def place_linear(self):
        self.conformation = [(i, 0) for i in range(len(self.sequence))]
        self.lattice = {self.conformation[i]: i for i in range(len(self.sequence))}

    def energy(self) -> int:
        e = 0
        for i in range(len(self.conformation)):
            if self.sequence[i] != 'H':
                continue
            x, y = self.conformation[i]
            for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                if (x+dx, y+dy) in self.lattice:
                    j = self.lattice[(x+dx, y+dy)]
                    if abs(j - i) > 1 and self.sequence[j] == 'H':
                        e -= 1
        return e // 2

    def random_fold(self, iterations: int = 1000) -> Tuple[int, List[Tuple[int, int]]]:
        self.place_linear()
        best_e = self.energy()
        best_conf = list(self.conformation)
        for _ in range(iterations):
            i = random.randint(1, len(self.conformation)-1)
            x, y = self.conformation[i-1]
            dirs = [(1,0),(-1,0),(0,1),(0,-1)]
            random.shuffle(dirs)
            for dx, dy in dirs:
                new_pos = (x+dx, y+dy)
                if new_pos not in self.lattice or self.lattice.get(new_pos) == i:
                    old = self.conformation[i]
                    self.conformation[i] = new_pos
                    self.lattice[new_pos] = i
                    if old != new_pos:
                        del self.lattice[old]
                    e = self.energy()
                    if e < best_e:
                        best_e = e; best_conf = list(self.conformation)
                    break
        return best_e, best_conf

    def stats(self) -> Dict:
        return {"length": len(self.sequence), "energy": self.energy(), "contacts": -self.energy()}

def run():
    pf = ProteinFolder("HPHPHPHPHPHPH")
    e, conf = pf.random_fold(500)
    print("Energy:", e, "Conf:", conf[:5])
    print(pf.stats())

if __name__ == "__main__":
    run()
