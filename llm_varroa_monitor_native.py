"""Native stdlib module: Varroa Monitor
Tracks varroa mite infestation levels and treatment thresholds.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class VarroaMonitor:
    colony_name: str
    bees_sampled: int
    mites_counted: int
    treatment_threshold_pct: float = 3.0

    def infestation_pct(self) -> float:
        if self.bees_sampled == 0:
            return 0.0
        return (self.mites_counted / self.bees_sampled) * 100

    def mites_per_100_bees(self) -> float:
        if self.bees_sampled == 0:
            return 0.0
        return (self.mites_counted / self.bees_sampled) * 100

    def treatment_needed(self) -> bool:
        return self.infestation_pct() >= self.treatment_threshold_pct

    def severity(self) -> str:
        ip = self.infestation_pct()
        if ip < 1:
            return "low"
        elif ip < 3:
            return "moderate"
        elif ip < 5:
            return "high"
        return "critical"

    def stats(self) -> Dict:
        return {
            "colony": self.colony_name,
            "infestation_pct": round(self.infestation_pct(), 2),
            "mites_per_100": round(self.mites_per_100_bees(), 2),
            "treatment_needed": self.treatment_needed(),
            "severity": self.severity(),
            "threshold": self.treatment_threshold_pct,
        }

def run():
    vm = VarroaMonitor(colony_name="Hive-3", bees_sampled=300, mites_counted=12, treatment_threshold_pct=3)
    print(vm.stats())

if __name__ == "__main__":
    run()
