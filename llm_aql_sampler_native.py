"""Native stdlib module: AQL Sampler
Determines acceptance sampling plans by AQL level, lot size, and inspection level.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class AQLSampler:
    lot_size: int
    aql_pct: float
    inspection_level: str = "II"
    single_double: str = "single"

    def _sample_size_code(self) -> str:
        if self.lot_size <= 8:
            return "A"
        elif self.lot_size <= 15:
            return "B"
        elif self.lot_size <= 25:
            return "C"
        elif self.lot_size <= 50:
            return "D"
        elif self.lot_size <= 90:
            return "E"
        elif self.lot_size <= 150:
            return "F"
        elif self.lot_size <= 280:
            return "G"
        elif self.lot_size <= 500:
            return "H"
        elif self.lot_size <= 1200:
            return "J"
        elif self.lot_size <= 3200:
            return "K"
        elif self.lot_size <= 10000:
            return "L"
        elif self.lot_size <= 35000:
            return "M"
        elif self.lot_size <= 150000:
            return "N"
        elif self.lot_size <= 500000:
            return "P"
        return "Q"

    def sample_size(self) -> int:
        code = self._sample_size_code()
        sizes = {"A": 2, "B": 3, "C": 5, "D": 8, "E": 13, "F": 20, "G": 32, "H": 50, "J": 80, "K": 125, "L": 200, "M": 315, "N": 500, "P": 800, "Q": 1250}
        return sizes.get(code, 1250)

    def acceptance_number(self) -> int:
        if self.aql_pct <= 0.65:
            return 0
        elif self.aql_pct <= 1.0:
            return 1
        elif self.aql_pct <= 1.5:
            return 2
        elif self.aql_pct <= 2.5:
            return 3
        elif self.aql_pct <= 4.0:
            return 5
        return 7

    def rejection_number(self) -> int:
        return self.acceptance_number() + 1

    def stats(self) -> Dict:
        return {
            "lot_size": self.lot_size,
            "sample_size": self.sample_size(),
            "acceptance_number": self.acceptance_number(),
            "rejection_number": self.rejection_number(),
            "aql_pct": self.aql_pct,
        }

def run():
    aql = AQLSampler(lot_size=5000, aql_pct=1.5, inspection_level="II")
    print(aql.stats())

if __name__ == "__main__":
    run()
