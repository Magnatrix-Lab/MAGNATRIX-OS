"""Model Quantizer - Weight quantization for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List
from enum import Enum, auto

class QuantType(Enum):
    INT8 = auto(); INT4 = auto(); BINARY = auto()

@dataclass
class ModelQuantizer:
    quant_type: QuantType = QuantType.INT8

    def quantize(self, weights: List[float]) -> List[int]:
        if self.quant_type == QuantType.INT8:
            return [int(max(-128, min(127, w * 127))) for w in weights]
        if self.quant_type == QuantType.INT4:
            return [int(max(-8, min(7, w * 7))) for w in weights]
        if self.quant_type == QuantType.BINARY:
            return [1 if w > 0 else -1 for w in weights]
        return [int(w) for w in weights]

    def dequantize(self, quantized: List[int]) -> List[float]:
        if self.quant_type == QuantType.INT8:
            return [q / 127.0 for q in quantized]
        if self.quant_type == QuantType.INT4:
            return [q / 7.0 for q in quantized]
        if self.quant_type == QuantType.BINARY:
            return [float(q) for q in quantized]
        return [float(q) for q in quantized]

    def stats(self, weights: List[float]) -> dict:
        q = self.quantize(weights)
        return {"type": self.quant_type.name, "original_bits": 32, "quantized_bits": 8 if self.quant_type==QuantType.INT8 else 4 if self.quant_type==QuantType.INT4 else 1}

def run():
    mq = ModelQuantizer(QuantType.INT8)
    w = [0.5, -0.3, 0.8, -0.1]
    q = mq.quantize(w)
    print("Quantized:", q)
    print("Dequantized:", [round(v,4) for v in mq.dequantize(q)])
    print("Stats:", mq.stats(w))

if __name__ == "__main__": run()
