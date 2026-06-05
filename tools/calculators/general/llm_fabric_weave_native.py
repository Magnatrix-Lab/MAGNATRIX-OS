"""Fabric Weave Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class FabricWeave:
    warp_count: int
    weft_count: int
    warp_yarn_tex: float
    weft_yarn_tex: float
    fabric_width_cm: float
    weave_type: str = "plain"

    def warp_yarns_per_cm(self) -> float:
        return round(self.warp_count / self.fabric_width_cm, 1)

    def total_ends(self) -> int:
        return int(self.warp_count)

    def picks_per_cm(self) -> float:
        return round(self.weft_count / self.fabric_width_cm, 1)

    def warp_weight_per_meter_g(self) -> float:
        length_m = 1.0
        crimp = {"plain": 1.05, "twill": 1.08, "satin": 1.12, "basket": 1.04}
        factor = crimp.get(self.weave_type, 1.05)
        weight = self.warp_count * self.warp_yarn_tex * length_m * factor / 1000.0
        return round(weight, 2)

    def weft_weight_per_meter_g(self) -> float:
        length_m = 1.0
        weight = self.weft_count * self.weft_yarn_tex * length_m * self.fabric_width_cm / 100.0 / 1000.0
        return round(weight, 2)

    def fabric_weight_gsm(self) -> float:
        warp = self.warp_weight_per_meter_g()
        weft = self.weft_weight_per_meter_g()
        width_m = self.fabric_width_cm / 100.0
        return round((warp + weft) / width_m, 1)

    def stats(self) -> Dict[str, float]:
        return {
            "warp_weight_per_m": self.warp_weight_per_meter_g(),
            "weft_weight_per_m": self.weft_weight_per_meter_g(),
            "fabric_weight_gsm": self.fabric_weight_gsm(),
        }

    def run(self):
        print("=" * 60)
        print("FABRIC WEAVE CALCULATOR")
        print("=" * 60)
        weave = FabricWeave(
            warp_count=3000, weft_count=2500, warp_yarn_tex=20, weft_yarn_tex=25,
            fabric_width_cm=150, weave_type="twill"
        )
        print(f"Weave: {weave.weave_type}")
        print(f"Warp ends: {weave.total_ends()}")
        print(f"Warp yarns/cm: {weave.warp_yarns_per_cm():.1f}")
        print(f"Picks/cm: {weave.picks_per_cm():.1f}")
        print(f"Warp weight/m: {weave.warp_weight_per_meter_g():.2f} g")
        print(f"Weft weight/m: {weave.weft_weight_per_meter_g():.2f} g")
        print(f"Fabric weight: {weave.fabric_weight_gsm():.1f} gsm")
        print(f"Stats: {weave.stats()}")

if __name__ == "__main__":
    FabricWeave(0, 0, 0, 0, 0).run()
