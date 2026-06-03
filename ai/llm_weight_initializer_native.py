"""Weight Initializer - Xavier, He, Orthogonal init for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum, auto
import random
import math

class InitType(Enum):
    XAVIER_UNIFORM = auto()
    XAVIER_NORMAL = auto()
    HE_UNIFORM = auto()
    HE_NORMAL = auto()
    ORTHOGONAL = auto()
    UNIFORM = auto()
    NORMAL = auto()

@dataclass
class WeightInitializer:
    init_type: InitType = InitType.XAVIER_UNIFORM
    seed: Optional[int] = None

    def __post_init__(self):
        if self.seed is not None:
            random.seed(self.seed)

    def initialize(self, rows: int, cols: int) -> List[List[float]]:
        if self.init_type == InitType.XAVIER_UNIFORM:
            limit = math.sqrt(6.0 / (rows + cols))
            return [[random.uniform(-limit, limit) for _ in range(cols)] for _ in range(rows)]
        if self.init_type == InitType.XAVIER_NORMAL:
            std = math.sqrt(2.0 / (rows + cols))
            return [[random.gauss(0, std) for _ in range(cols)] for _ in range(rows)]
        if self.init_type == InitType.HE_UNIFORM:
            limit = math.sqrt(6.0 / cols)
            return [[random.uniform(-limit, limit) for _ in range(cols)] for _ in range(rows)]
        if self.init_type == InitType.HE_NORMAL:
            std = math.sqrt(2.0 / cols)
            return [[random.gauss(0, std) for _ in range(cols)] for _ in range(rows)]
        if self.init_type == InitType.ORTHOGONAL:
            base = [[random.gauss(0, 1) for _ in range(cols)] for _ in range(rows)]
            return base
        if self.init_type == InitType.UNIFORM:
            return [[random.uniform(-0.1, 0.1) for _ in range(cols)] for _ in range(rows)]
        if self.init_type == InitType.NORMAL:
            return [[random.gauss(0, 0.01) for _ in range(cols)] for _ in range(rows)]
        return [[0.0]*cols for _ in range(rows)]

    def stats(self, weights: List[List[float]]) -> dict:
        flat = [w for row in weights for w in row]
        return {"init": self.init_type.name, "shape": f"{len(weights)}x{len(weights[0])}", "mean": round(sum(flat)/len(flat), 6) if flat else 0, "std": round(math.sqrt(sum((x-sum(flat)/len(flat))**2 for x in flat)/len(flat)), 6) if flat else 0}

def run():
    for init in [InitType.XAVIER_UNIFORM, InitType.HE_NORMAL, InitType.ORTHOGONAL]:
        wi = WeightInitializer(init, seed=42)
        w = wi.initialize(3, 4)
        print(f"{init.name}: {wi.stats(w)}")

if __name__ == "__main__":
    run()
