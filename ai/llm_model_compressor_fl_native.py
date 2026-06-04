"""Model Compressor FL - Compression for FL communication for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math

class CompressMethod(Enum):
    TOPK = auto(); RANDOMK = auto(); SIGN = auto()

@dataclass
class ModelCompressorFL:
    method: CompressMethod = CompressMethod.TOPK
    k: int = 10

    def compress(self, grad: List[float]) -> List[float]:
        if self.method == CompressMethod.TOPK:
            indices = sorted(range(len(grad)), key=lambda i: abs(grad[i]), reverse=True)[:self.k]
            result = [0.0] * len(grad)
            for i in indices: result[i] = grad[i]
            return result
        elif self.method == CompressMethod.RANDOMK:
            indices = random.sample(range(len(grad)), min(self.k, len(grad)))
            result = [0.0] * len(grad)
            for i in indices: result[i] = grad[i]
            return result
        elif self.method == CompressMethod.SIGN:
            return [1.0 if g > 0 else -1.0 if g < 0 else 0.0 for g in grad]
        return grad

    def compression_ratio(self, grad: List[float]) -> float:
        compressed = self.compress(grad)
        nonzero = sum(1 for g in compressed if g != 0)
        return nonzero / len(grad)

    def stats(self, grad: List[float]) -> dict:
        return {"method": self.method.name, "k": self.k, "compression_ratio": round(self.compression_ratio(grad), 4)}

def run():
    mc = ModelCompressorFL(CompressMethod.TOPK, 3)
    grad = [0.1, 0.5, -0.3, 0.8, -0.2]
    compressed = mc.compress(grad)
    print("Compressed:", compressed)
    print("Stats:", mc.stats(grad))

if __name__ == "__main__": run()
