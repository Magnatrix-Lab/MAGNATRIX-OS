"""Paper Spec Calculator -- gsm, bulk, caliper, yield, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class PaperSpec:
    gsm: float = 80.0
    sheet_size_mm: Tuple[float, float] = (210, 297)
    ream_count: int = 500

    def sheet_weight_g(self) -> float:
        return self.gsm * self.sheet_size_mm[0] * self.sheet_size_mm[1] / 1000000

    def ream_weight_kg(self) -> float:
        return self.sheet_weight_g() * self.ream_count / 1000

    def yield_per_ton(self) -> int:
        return int(1000000 / self.sheet_weight_g())

    def caliper_mm(self, bulk: float = 1.2) -> float:
        return self.gsm / 1000 * bulk

    def opacity_pct(self, thickness_factor: float = 1.0) -> float:
        return min(100, self.gsm * 0.8 * thickness_factor + 40)

    def folding_endurance(self) -> int:
        return int(self.gsm * 2.5)

    def stats(self) -> Dict:
        return {"sheet_weight_g": round(self.sheet_weight_g(), 3), "ream_kg": round(self.ream_weight_kg(), 2), "yield_per_ton": self.yield_per_ton(), "caliper_mm": round(self.caliper_mm(), 3)}

def run():
    ps = PaperSpec(gsm=100, sheet_size_mm=(210, 297))
    print(ps.stats())

if __name__ == "__main__":
    run()
