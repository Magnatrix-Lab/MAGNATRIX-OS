"""Native stdlib module: SPC Chart
Calculates control limits and process capability for statistical process control.
"""
from dataclasses import dataclass, field
from typing import List, Dict
import math

@dataclass
class SPCChart:
    process_name: str
    measurements: List[float] = field(default_factory=list)
    usl: float = 0.0
    lsl: float = 0.0

    def mean(self) -> float:
        if not self.measurements:
            return 0.0
        return sum(self.measurements) / len(self.measurements)

    def std_dev(self) -> float:
        if len(self.measurements) < 2:
            return 0.0
        m = self.mean()
        variance = sum((x - m) ** 2 for x in self.measurements) / (len(self.measurements) - 1)
        return math.sqrt(variance)

    def ucl(self) -> float:
        return self.mean() + 3 * self.std_dev()

    def lcl(self) -> float:
        return self.mean() - 3 * self.std_dev()

    def cp(self) -> float:
        if self.usl <= self.lsl:
            return 0.0
        return (self.usl - self.lsl) / (6 * self.std_dev())

    def cpk(self) -> float:
        if self.std_dev() == 0:
            return 0.0
        cpu = (self.usl - self.mean()) / (3 * self.std_dev())
        cpl = (self.mean() - self.lsl) / (3 * self.std_dev())
        return min(cpu, cpl)

    def out_of_control(self) -> List[float]:
        ucl = self.ucl()
        lcl = self.lcl()
        return [x for x in self.measurements if x > ucl or x < lcl]

    def stats(self) -> Dict:
        return {
            "process": self.process_name,
            "mean": round(self.mean(), 3),
            "std_dev": round(self.std_dev(), 3),
            "ucl": round(self.ucl(), 3),
            "lcl": round(self.lcl(), 3),
            "cp": round(self.cp(), 2),
            "cpk": round(self.cpk(), 2),
            "out_of_control_count": len(self.out_of_control()),
        }

def run():
    spc = SPCChart(
        process_name="Bore Diameter",
        measurements=[10.02, 10.01, 9.99, 10.00, 10.03, 9.98, 10.01, 10.00, 10.02, 9.99, 10.05, 9.97],
        usl=10.05,
        lsl=9.95
    )
    print(spc.stats())

if __name__ == "__main__":
    run()
