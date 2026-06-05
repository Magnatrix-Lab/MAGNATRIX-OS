"""Native stdlib module: Soap Curing Calculator
Calculates cure time, weight loss, and pH development during curing.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class SoapCuringCalculator:
    initial_weight_g: float
    initial_water_pct: float = 12.0
    cure_time_days: int = 28
    ambient_humidity_pct: float = 50.0
    soap_hardness_score: float = 35.0

    def water_loss_g(self) -> float:
        base_loss = self.initial_weight_g * (self.initial_water_pct / 100) * 0.6
        humidity_factor = 1 - (self.ambient_humidity_pct / 100) * 0.5
        return base_loss * humidity_factor

    def cured_weight_g(self) -> float:
        return self.initial_weight_g - self.water_loss_g()

    def weight_loss_pct(self) -> float:
        if self.initial_weight_g == 0:
            return 0
        return (self.water_loss_g() / self.initial_weight_g) * 100

    def recommended_cure_days(self) -> int:
        if self.soap_hardness_score < 30:
            return 42
        elif self.soap_hardness_score < 45:
            return 35
        return 28

    def estimated_ph(self) -> float:
        base_ph = 10.0
        cure_reduction = min(2.0, self.cure_time_days * 0.04)
        return base_ph - cure_reduction

    def readiness_score(self) -> float:
        if self.cure_time_days < self.recommended_cure_days():
            return (self.cure_time_days / self.recommended_cure_days()) * 100
        return 100

    def storage_conditions(self) -> str:
        if self.ambient_humidity_pct > 70:
            return "risk_of_dos"
        elif self.ambient_humidity_pct < 30:
            return "fast_cure_risk_cracking"
        return "ideal"

    def stats(self) -> Dict:
        return {
            "initial_weight_g": self.initial_weight_g,
            "cured_weight_g": round(self.cured_weight_g(), 1),
            "weight_loss_g": round(self.water_loss_g(), 1),
            "weight_loss_pct": round(self.weight_loss_pct(), 1),
            "recommended_cure_days": self.recommended_cure_days(),
            "estimated_ph": round(self.estimated_ph(), 1),
            "readiness_score": round(self.readiness_score(), 1),
            "storage_conditions": self.storage_conditions(),
        }

def run():
    scc = SoapCuringCalculator(initial_weight_g=150, initial_water_pct=12, cure_time_days=21, ambient_humidity_pct=55, soap_hardness_score=38)
    print(scc.stats())

if __name__ == "__main__":
    run()
