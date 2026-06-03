"""Filter Designer - FIR/IIR filters for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
from enum import Enum, auto
import math

class FilterType(Enum):
    LOWPASS = auto(); HIGHPASS = auto(); MOVING_AVG = auto()

@dataclass
class FilterDesigner:
    filter_type: FilterType = FilterType.LOWPASS
    cutoff: float = 0.5; order: int = 3
    coefficients: List[float] = field(default_factory=list)

    def __post_init__(self):
        if self.filter_type == FilterType.MOVING_AVG:
            self.coefficients = [1.0/self.order]*self.order
        elif self.filter_type == FilterType.LOWPASS:
            self.coefficients = [math.sin(self.cutoff*math.pi*(i-self.order//2))/(math.pi*(i-self.order//2)) if i!=self.order//2 else self.cutoff for i in range(self.order)]

    def apply(self, signal: List[float]) -> List[float]:
        n = len(self.coefficients)
        return [sum(signal[max(0,i-j)]*self.coefficients[j] for j in range(n) if i-j >= 0) for i in range(len(signal))]

    def stats(self) -> dict:
        return {"type": self.filter_type.name, "order": self.order, "coeffs": [round(c,4) for c in self.coefficients]}

def run():
    fd = FilterDesigner(FilterType.MOVING_AVG, order=3)
    signal = [1.0, 2.0, 3.0, 4.0, 5.0, 4.0, 3.0]
    print("Filtered:", [round(v,4) for v in fd.apply(signal)])
    print("Stats:", fd.stats())

if __name__ == "__main__": run()
