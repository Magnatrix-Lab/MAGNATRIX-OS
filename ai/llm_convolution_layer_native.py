"""Convolution Layer - 2D conv for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum, auto
import random
import math

class PaddingType(Enum):
    SAME = auto()
    VALID = auto()

@dataclass
class ConvolutionLayer:
    kernel_size: int = 3
    input_channels: int = 1
    output_channels: int = 1
    stride: int = 1
    padding: PaddingType = PaddingType.VALID
    kernels: List[List[List[float]]] = field(default_factory=list)

    def __post_init__(self):
        if not self.kernels:
            scale = math.sqrt(1.0 / (self.input_channels * self.kernel_size * self.kernel_size))
            self.kernels = [[[random.gauss(0, scale) for _ in range(self.kernel_size)] for _ in range(self.kernel_size)] for _ in range(self.output_channels)]

    def convolve(self, image: List[List[float]]) -> List[List[float]]:
        h, w = len(image), len(image[0])
        out_h = (h - self.kernel_size) // self.stride + 1
        out_w = (w - self.kernel_size) // self.stride + 1
        output = [[0.0]*out_w for _ in range(out_h)]
        for i in range(out_h):
            for j in range(out_w):
                si, sj = i * self.stride, j * self.stride
                val = sum(image[si+ki][sj+kj] * self.kernels[0][ki][kj] for ki in range(self.kernel_size) for kj in range(self.kernel_size))
                output[i][j] = val
        return output

    def stats(self) -> dict:
        return {"kernel": self.kernel_size, "in_ch": self.input_channels, "out_ch": self.output_channels, "stride": self.stride, "kernels": len(self.kernels)}

def run():
    conv = ConvolutionLayer(3, 1, 1, 1)
    img = [[float(i+j) for j in range(6)] for i in range(6)]
    out = conv.convolve(img)
    print("Output shape:", len(out), "x", len(out[0]))
    print("Stats:", conv.stats())

if __name__ == "__main__":
    run()
