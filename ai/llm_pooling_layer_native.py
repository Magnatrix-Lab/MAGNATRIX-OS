"""Pooling Layer - Max and average pooling for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum, auto

class PoolType(Enum):
    MAX = auto()
    AVG = auto()
    MIN = auto()

@dataclass
class PoolingLayer:
    pool_size: int = 2
    stride: int = 2
    pool_type: PoolType = PoolType.MAX

    def pool(self, feature_map: List[List[float]]) -> List[List[float]]:
        h, w = len(feature_map), len(feature_map[0])
        out_h = (h - self.pool_size) // self.stride + 1
        out_w = (w - self.pool_size) // self.stride + 1
        output = [[0.0]*out_w for _ in range(out_h)]
        for i in range(out_h):
            for j in range(out_w):
                si, sj = i * self.stride, j * self.stride
                window = [feature_map[si+ki][sj+kj] for ki in range(self.pool_size) for kj in range(self.pool_size) if si+ki < h and sj+kj < w]
                if self.pool_type == PoolType.MAX: output[i][j] = max(window)
                elif self.pool_type == PoolType.MIN: output[i][j] = min(window)
                else: output[i][j] = sum(window) / len(window)
        return output

    def stats(self) -> dict:
        return {"pool_type": self.pool_type.name, "size": self.pool_size, "stride": self.stride}

def run():
    for pt in [PoolType.MAX, PoolType.AVG]:
        pool = PoolingLayer(2, 2, pt)
        fm = [[1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0], [9.0, 10.0, 11.0, 12.0], [13.0, 14.0, 15.0, 16.0]]
        out = pool.pool(fm)
        print(f"{pt.name} pool: {out}")
    print("Stats:", pool.stats())

if __name__ == "__main__":
    run()
