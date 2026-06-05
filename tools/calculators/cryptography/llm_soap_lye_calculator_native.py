"""Native stdlib module: Soap Lye Calculator
Calculates lye (NaOH/KOH) amounts, water ratios, and superfat for soap making.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class SoapLyeCalculator:
    oil_weights_g: Dict[str, float]
    lye_type: str = "NaOH"  # NaOH or KOH
    superfat_pct: float = 5.0
    water_ratio: float = 0.33  # water as % of oil weight

    _SAP_VALUES = {
        "olive": 0.135, "coconut": 0.190, "palm": 0.141, "shea": 0.128,
        "cocoa": 0.137, "castor": 0.128, "avocado": 0.134, "sweet_almond": 0.137,
        "sunflower": 0.135, "grapeseed": 0.132, "lard": 0.138, "tallow": 0.140,
    }

    _KOH_FACTOR = 1.403

    def total_oil_weight_g(self) -> float:
        return sum(self.oil_weights_g.values())

    def lye_needed_g(self) -> float:
        total = 0.0
        for oil, weight in self.oil_weights_g.items():
            sap = self._SAP_VALUES.get(oil, 0.135)
            total += weight * sap
        if self.lye_type == "KOH":
            total *= self._KOH_FACTOR
        return total * (1 - self.superfat_pct / 100)

    def water_needed_g(self) -> float:
        return self.total_oil_weight_g() * self.water_ratio

    def total_batch_weight_g(self) -> float:
        return self.total_oil_weight_g() + self.lye_needed_g() + self.water_needed_g()

    def superfat_amount_g(self) -> float:
        return sum(self.oil_weights_g.values()) * (self.superfat_pct / 100) * 0.135

    def safety_margin(self) -> str:
        if self.superfat_pct < 3:
            return "lye_heavy_risk"
        elif self.superfat_pct > 10:
            return "soft_soap_risk"
        return "safe"

    def stats(self) -> Dict:
        return {
            "total_oil_weight_g": round(self.total_oil_weight_g(), 1),
            "lye_type": self.lye_type,
            "lye_needed_g": round(self.lye_needed_g(), 2),
            "water_needed_g": round(self.water_needed_g(), 1),
            "total_batch_weight_g": round(self.total_batch_weight_g(), 1),
            "superfat_pct": self.superfat_pct,
            "safety_margin": self.safety_margin(),
        }

def run():
    slc = SoapLyeCalculator(
        oil_weights_g={"olive": 500, "coconut": 300, "palm": 200},
        lye_type="NaOH", superfat_pct=5, water_ratio=0.33,
    )
    print(slc.stats())

if __name__ == "__main__":
    run()
