"""Native stdlib module: Proofing Calculator
Calculates proof, ABV, temperature corrections, and blending.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class ProofingCalculator:
    abv_pct: float
    temperature_c: float = 20.0
    volume_l: float = 1.0

    def proof(self) -> float:
        return self.abv_pct * 2

    def abv_at_20c(self) -> float:
        correction = (self.temperature_c - 20) * 0.03
        return self.abv_pct - correction

    def proof_at_20c(self) -> float:
        return self.abv_at_20c() * 2

    def alcohol_volume_l(self) -> float:
        return self.volume_l * (self.abv_pct / 100)

    def water_volume_l(self) -> float:
        return self.volume_l - self.alcohol_volume_l()

    def blend_to_target(self, target_abv_pct: float, other_abv_pct: float, other_volume_l: float) -> float:
        total_alcohol = self.alcohol_volume_l() + other_volume_l * (other_abv_pct / 100)
        total_volume = self.volume_l + other_volume_l
        if total_volume == 0:
            return 0
        return (total_alcohol / total_volume) * 100

    def hydrometer_reading_expected(self) -> float:
        return 100 - self.abv_at_20c()

    def classification(self) -> str:
        proof = self.proof()
        if proof < 40:
            return "low_proof"
        elif proof < 80:
            return "standard_proof"
        elif proof < 100:
            return "over_proof"
        elif proof < 150:
            return "high_proof"
        return "neutral_spirit"

    def stats(self, target_abv_pct: Optional[float] = None, other_abv_pct: Optional[float] = None, other_volume_l: Optional[float] = None) -> Dict:
        result = {
            "abv_pct": self.abv_pct,
            "temperature_c": self.temperature_c,
            "proof": self.proof(),
            "abv_at_20c": round(self.abv_at_20c(), 2),
            "proof_at_20c": round(self.proof_at_20c(), 2),
            "alcohol_volume_l": round(self.alcohol_volume_l(), 3),
            "water_volume_l": round(self.water_volume_l(), 3),
            "classification": self.classification(),
        }
        if target_abv_pct is not None and other_abv_pct is not None and other_volume_l is not None:
            result["blend_result_abv"] = round(self.blend_to_target(target_abv_pct, other_abv_pct, other_volume_l), 2)
        return result

def run():
    pc = ProofingCalculator(abv_pct=45, temperature_c=25, volume_l=2)
    print(pc.stats(target_abv_pct=40, other_abv_pct=60, other_volume_l=1))

if __name__ == "__main__":
    run()
