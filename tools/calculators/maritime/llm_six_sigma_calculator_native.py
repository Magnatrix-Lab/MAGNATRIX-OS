"""Native stdlib module: Six Sigma Calculator
Calculates sigma level, DPMO, and process capability indices.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class SixSigmaCalculator:
    process_name: str
    defects: int
    opportunities: int
    units: int

    def dpmo(self) -> float:
        if self.units == 0 or self.opportunities == 0:
            return 0.0
        return (self.defects / (self.units * self.opportunities)) * 1_000_000

    def sigma_level(self) -> float:
        dpmo = self.dpmo()
        if dpmo <= 0:
            return 6.0
        if dpmo >= 1_000_000:
            return 0.0
        try:
            return 0.8406 + math.sqrt(29.37 - 2.221 * math.log(dpmo))
        except ValueError:
            return 0.0

    def yield_pct(self) -> float:
        if self.units == 0:
            return 0.0
        return ((self.units - self.defects) / self.units) * 100

    def stats(self) -> Dict[str, float]:
        return {
            "process": self.process_name,
            "dpmo": round(self.dpmo(), 1),
            "sigma_level": round(self.sigma_level(), 2),
            "yield_pct": round(self.yield_pct(), 2),
            "defects": self.defects,
        }

def run():
    ssc = SixSigmaCalculator(process_name="Soldering", defects=12, opportunities=3, units=5000)
    print(ssc.stats())

if __name__ == "__main__":
    run()
