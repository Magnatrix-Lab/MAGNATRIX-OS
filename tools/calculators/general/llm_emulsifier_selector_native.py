"""Emulsifier Selector — HLB, oil type, stability, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class EmulsifierSelector:
    oil_phase_pct: float = 20.0
    water_phase_pct: float = 80.0
    oil_type: str = "mineral"

    def required_hlb(self) -> float:
        oil_hlb = {"mineral": 10, "vegetable": 7, "silicone": 5, "ester": 9}
        return oil_hlb.get(self.oil_type, 8)

    def emulsifier_pct(self) -> float:
        return self.oil_phase_pct * 0.05

    def stability_score(self, hlb_match: float) -> float:
        return 1 - abs(hlb_match - self.required_hlb()) / 10

    def phase_inversion_temp(self) -> float:
        return 70 + self.oil_phase_pct * 0.5

    def stats(self, hlb_match: float = 8) -> Dict:
        return {"required_hlb": self.required_hlb(), "emulsifier_pct": self.emulsifier_pct(), "stability": round(self.stability_score(hlb_match), 2)}

def run():
    es = EmulsifierSelector(oil_phase_pct=30, oil_type="vegetable")
    print(es.stats(7))
    print("PIT:", es.phase_inversion_temp())

if __name__ == "__main__":
    run()
