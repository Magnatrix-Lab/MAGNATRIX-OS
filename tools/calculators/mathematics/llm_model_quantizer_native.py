"""Model Quantization — int8/FP16 weight compression, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum, auto
import math
import struct

class QuantType(Enum):
    INT8 = auto()
    INT4 = auto()
    FP16 = auto()

@dataclass
class QuantizedTensor:
    shape: Tuple[int, ...]
    scale: float
    zero_point: float
    data: List[int]
    qtype: QuantType

    def dequantize(self) -> List[float]:
        return [(x - self.zero_point) * self.scale for x in self.data]

class ModelQuantizer:
    def __init__(self, qtype: QuantType = QuantType.INT8):
        self.qtype = qtype
        self.quantized_layers: Dict[str, QuantizedTensor] = {}

    def _find_range(self, weights: List[float]) -> Tuple[float, float]:
        return min(weights), max(weights)

    def quantize(self, name: str, weights: List[float], shape: Tuple[int, ...]) -> QuantizedTensor:
        wmin, wmax = self._find_range(weights)
        if self.qtype == QuantType.INT8:
            qmax = 127
            qmin = -128
        elif self.qtype == QuantType.INT4:
            qmax = 7
            qmin = -8
        else:
            scale = 1.0
            zp = 0.0
            data = [struct.unpack("<H", struct.pack("<e", w))[0] if w != 0 else 0 for w in weights]
            qt = QuantizedTensor(shape, scale, zp, data, self.qtype)
            self.quantized_layers[name] = qt
            return qt
        scale = (wmax - wmin) / (qmax - qmin) if wmax != wmin else 1.0
        zp = qmin - wmin / scale if scale != 0 else 0
        data = [max(qmin, min(qmax, int(round(w / scale + zp)))) for w in weights]
        qt = QuantizedTensor(shape, scale, zp, data, self.qtype)
        self.quantized_layers[name] = qt
        return qt

    def dequantize_layer(self, name: str) -> List[float]:
        qt = self.quantized_layers.get(name)
        return qt.dequantize() if qt else []

    def compression_ratio(self, name: str, original_floats: int) -> float:
        qt = self.quantized_layers.get(name)
        if not qt:
            return 0.0
        bits = 8 if qt.qtype == QuantType.INT8 else (4 if qt.qtype == QuantType.INT4 else 16)
        return (original_floats * 32) / (len(qt.data) * bits)

    def stats(self) -> Dict:
        return {"layers": len(self.quantized_layers), "qtype": self.qtype.name, "layers_detail": {k: v.shape for k, v in self.quantized_layers.items()}}

def run():
    mq = ModelQuantizer(QuantType.INT8)
    weights = [0.1, -0.5, 0.8, -0.2, 0.05, 0.9, -0.3, 0.4]
    qt = mq.quantize("layer1", weights, (2, 4))
    print("Quantized:", qt.data)
    print("Dequantized:", [round(x, 3) for x in mq.dequantize_layer("layer1")])
    print(mq.stats())

if __name__ == "__main__":
    run()
