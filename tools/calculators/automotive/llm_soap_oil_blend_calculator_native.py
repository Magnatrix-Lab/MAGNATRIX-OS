"""Native stdlib module: Soap Oil Blend Calculator
Analyzes oil properties, hardness, cleansing, and conditioning values.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class SoapOilBlendCalculator:
    oil_weights_g: Dict[str, float]

    _OIL_PROPERTIES = {
        "olive": {"hardness": 17, "cleansing": 0, "conditioning": 82, "bubbly": 0, "creamy": 67},
        "coconut": {"hardness": 79, "cleansing": 67, "conditioning": 10, "bubbly": 67, "creamy": 12},
        "palm": {"hardness": 50, "cleansing": 0, "conditioning": 49, "bubbly": 0, "creamy": 49},
        "shea": {"hardness": 45, "cleansing": 0, "conditioning": 58, "bubbly": 0, "creamy": 45},
        "cocoa": {"hardness": 61, "cleansing": 0, "conditioning": 54, "bubbly": 0, "creamy": 61},
        "castor": {"hardness": 15, "cleansing": 0, "conditioning": 92, "bubbly": 0, "creamy": 79},
        "sweet_almond": {"hardness": 7, "cleansing": 0, "conditioning": 72, "bubbly": 0, "creamy": 17},
        "sunflower": {"hardness": 11, "cleansing": 0, "conditioning": 69, "bubbly": 0, "creamy": 17},
    }

    def total_weight(self) -> float:
        return sum(self.oil_weights_g.values())

    def oil_pcts(self) -> Dict[str, float]:
        total = self.total_weight()
        if total == 0:
            return {}
        return {oil: (weight / total) * 100 for oil, weight in self.oil_weights_g.items()}

    def _weighted_property(self, prop: str) -> float:
        total = self.total_weight()
        if total == 0:
            return 0
        value = 0
        for oil, weight in self.oil_weights_g.items():
            props = self._OIL_PROPERTIES.get(oil, {})
            value += (weight / total) * props.get(prop, 0)
        return value

    def hardness(self) -> float:
        return self._weighted_property("hardness")

    def cleansing(self) -> float:
        return self._weighted_property("cleansing")

    def conditioning(self) -> float:
        return self._weighted_property("conditioning")

    def bubbly(self) -> float:
        return self._weighted_property("bubbly")

    def creamy(self) -> float:
        return self._weighted_property("creamy")

    def iodine_value(self) -> float:
        return self.conditioning() * 0.8

    def stats(self) -> Dict:
        return {
            "oil_pcts": {k: round(v, 1) for k, v in self.oil_pcts().items()},
            "hardness": round(self.hardness(), 1),
            "cleansing": round(self.cleansing(), 1),
            "conditioning": round(self.conditioning(), 1),
            "bubbly": round(self.bubbly(), 1),
            "creamy": round(self.creamy(), 1),
            "iodine_estimate": round(self.iodine_value(), 1),
        }

def run():
    sobc = SoapOilBlendCalculator(
        oil_weights_g={"olive": 400, "coconut": 250, "palm": 200, "shea": 100, "castor": 50}
    )
    print(sobc.stats())

if __name__ == "__main__":
    run()
