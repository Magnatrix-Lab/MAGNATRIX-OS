"""Quality Controller — SPC, control charts, Cp/Cpk, defect rate, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class QualityController:
    measurements: List[float] = field(default_factory=list)
    usl: float = 10.0
    lsl: float = 0.0

    def mean(self) -> float:
        return sum(self.measurements) / len(self.measurements) if self.measurements else 0.0

    def stddev(self) -> float:
        if len(self.measurements) < 2:
            return 0.0
        m = self.mean()
        return math.sqrt(sum((x - m)**2 for x in self.measurements) / len(self.measurements))

    def cp(self) -> float:
        s = self.stddev()
        return (self.usl - self.lsl) / (6 * s) if s > 0 else 0.0

    def cpk(self) -> float:
        s = self.stddev()
        if s == 0:
            return 0.0
        m = self.mean()
        cpu = (self.usl - m) / (3 * s)
        cpl = (m - self.lsl) / (3 * s)
        return min(cpu, cpl)

    def control_limits(self) -> Tuple[float, float, float]:
        m = self.mean()
        s = self.stddev()
        return m - 3*s, m, m + 3*s

    def out_of_control(self) -> List[int]:
        lcl, _, ucl = self.control_limits()
        return [i for i, x in enumerate(self.measurements) if x < lcl or x > ucl]

    def defect_rate(self) -> float:
        defects = sum(1 for x in self.measurements if x < self.lsl or x > self.usl)
        return defects / len(self.measurements) if self.measurements else 0.0

    def stats(self) -> Dict:
        return {"mean": round(self.mean(), 3), "cp": round(self.cp(), 3), "cpk": round(self.cpk(), 3), "defects": self.defect_rate()}

def run():
    qc = QualityController([5.1,5.0,5.2,4.9,5.1,5.3,4.8,10.5], usl=6, lsl=4)
    print(qc.stats())
    print("OOC:", qc.out_of_control())

if __name__ == "__main__":
    run()
