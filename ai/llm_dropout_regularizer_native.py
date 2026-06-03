"""Dropout Regularizer - Dropout for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum, auto
import random

class DropoutMode(Enum):
    STANDARD = auto()
    INVERTED = auto()

@dataclass
class DropoutRegularizer:
    rate: float = 0.5
    mode: DropoutMode = DropoutMode.STANDARD
    seed: Optional[int] = None

    def __post_init__(self):
        if self.seed is not None:
            random.seed(self.seed)

    def apply(self, inputs: List[float], training: bool = True) -> List[float]:
        if not training or self.rate <= 0:
            return inputs
        mask = [1.0 if random.random() > self.rate else 0.0 for _ in inputs]
        if self.mode == DropoutMode.INVERTED:
            scale = 1.0 / (1.0 - self.rate)
            return [inputs[i] * mask[i] * scale for i in range(len(inputs))]
        return [inputs[i] * mask[i] for i in range(len(inputs))]

    def apply_batch(self, batch: List[List[float]], training: bool = True) -> List[List[float]]:
        return [self.apply(row, training) for row in batch]

    def stats(self, inputs: List[float]) -> dict:
        out = self.apply(inputs)
        active = sum(1 for v in out if v != 0)
        return {"rate": self.rate, "mode": self.mode.name, "active_units": active, "total_units": len(inputs)}

def run():
    d = DropoutRegularizer(0.3, DropoutMode.INVERTED, seed=42)
    inputs = [1.0, 2.0, 3.0, 4.0, 5.0]
    for _ in range(3):
        out = d.apply(inputs)
        print(f"Dropout out: {[round(v, 4) for v in out]}")
    print("Stats:", d.stats(inputs))

if __name__ == "__main__":
    run()
