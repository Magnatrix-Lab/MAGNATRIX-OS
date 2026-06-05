"""Bonbon Mold — shell thickness, filling ratio, demolding, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class BonbonMold:
    mold_volume_ml: float = 10.0
    shell_thickness_mm: float = 2.0
    mold_count: int = 24

    def shell_volume(self) -> float:
        return self.mold_volume_ml * 0.3 * (self.shell_thickness_mm / 2)

    def filling_volume(self) -> float:
        return self.mold_volume_ml - self.shell_volume()

    def chocolate_needed_g(self, density: float = 1.3) -> float:
        return self.shell_volume() * density * self.mold_count

    def filling_needed_g(self, density: float = 1.0) -> float:
        return self.filling_volume() * density * self.mold_count

    def total_batch_g(self) -> float:
        return self.chocolate_needed_g() + self.filling_needed_g()

    def demold_temp(self) -> float:
        return 18

    def stats(self) -> Dict:
        return {"shell": round(self.shell_volume(), 2), "filling": round(self.filling_volume(), 2), "total": round(self.total_batch_g(), 1), "pieces": self.mold_count}

def run():
    bm = BonbonMold(mold_volume_ml=15, shell_thickness_mm=2.5, mold_count=36)
    print(bm.stats())

if __name__ == "__main__":
    run()
