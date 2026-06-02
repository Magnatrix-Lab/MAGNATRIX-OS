"""Quantization Engine — Model quantization and dequantization for inference optimization.

Modul ini menyediakan:
- QuantizationConfig untuk quantization configuration
- WeightQuantizer untuk quantize weights to INT8/INT4/FP16
- ActivationQuantizer untuk quantize activations
- QuantizedModel untuk quantized model representation
- QuantizationEngine untuk end-to-end quantization pipeline
"""

from __future__ import annotations

import json
import time
import uuid
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class QuantizationType(Enum):
    FP32 = "fp32"
    FP16 = "fp16"
    BF16 = "bf16"
    INT8 = "int8"
    INT4 = "int4"
    GPTQ = "gptq"
    AWQ = "awq"


@dataclass
class QuantizationConfig:
    """Quantization configuration."""
    quant_type: QuantizationType
    group_size: int = 128
    bits: int = 8
    symmetric: bool = True
    per_channel: bool = True
    calibration_samples: int = 128
    zero_point: bool = True


@dataclass
class QuantizedTensor:
    """Quantized tensor with scale and zero point."""
    quantized_values: List[int]
    scale: float
    zero_point: int
    shape: List[int]
    dtype: str
    original_dtype: str = "fp32"
    compression_ratio: float = 1.0

    def dequantize(self) -> List[float]:
        if self.dtype == "int4":
            return [(v - self.zero_point) * self.scale for v in self.quantized_values]
        elif self.dtype == "int8":
            return [(v - self.zero_point) * self.scale for v in self.quantized_values]
        elif self.dtype == "fp16":
            return [v * self.scale for v in self.quantized_values]
        return [float(v) for v in self.quantized_values]


class WeightQuantizer:
    """Quantize model weights."""

    def __init__(self, config: QuantizationConfig):
        self.config = config

    def quantize(self, weights: List[float]) -> QuantizedTensor:
        if self.config.quant_type == QuantizationType.INT8:
            return self._quantize_int8(weights)
        elif self.config.quant_type == QuantizationType.INT4:
            return self._quantize_int4(weights)
        elif self.config.quant_type == QuantizationType.FP16:
            return self._quantize_fp16(weights)
        return self._quantize_int8(weights)

    def _quantize_int8(self, weights: List[float]) -> QuantizedTensor:
        min_val = min(weights)
        max_val = max(weights)
        if self.config.symmetric:
            abs_max = max(abs(min_val), abs(max_val))
            scale = abs_max / 127.0 if abs_max > 0 else 1.0
            zero_point = 0
            quantized = [max(-128, min(127, int(w / scale))) for w in weights]
        else:
            scale = (max_val - min_val) / 255.0 if max_val != min_val else 1.0
            zero_point = int(-min_val / scale)
            quantized = [max(0, min(255, int(w / scale + zero_point))) for w in weights]
        return QuantizedTensor(
            quantized_values=quantized,
            scale=scale,
            zero_point=zero_point,
            shape=[len(weights)],
            dtype="int8",
            compression_ratio=4.0,  # 32-bit -> 8-bit
        )

    def _quantize_int4(self, weights: List[float]) -> QuantizedTensor:
        min_val = min(weights)
        max_val = max(weights)
        scale = (max_val - min_val) / 15.0 if max_val != min_val else 1.0
        zero_point = int(-min_val / scale)
        quantized = [max(0, min(15, int(w / scale + zero_point))) for w in weights]
        return QuantizedTensor(
            quantized_values=quantized,
            scale=scale,
            zero_point=zero_point,
            shape=[len(weights)],
            dtype="int4",
            compression_ratio=8.0,  # 32-bit -> 4-bit
        )

    def _quantize_fp16(self, weights: List[float]) -> QuantizedTensor:
        # Simulated: just scale and represent as integers
        scale = 1.0
        zero_point = 0
        quantized = [int(w * 1000) for w in weights]  # Simulated
        return QuantizedTensor(
            quantized_values=quantized,
            scale=scale,
            zero_point=zero_point,
            shape=[len(weights)],
            dtype="fp16",
            compression_ratio=2.0,
        )

    def dequantize(self, tensor: QuantizedTensor) -> List[float]:
        return tensor.dequantize()


class ActivationQuantizer:
    """Quantize activations dynamically."""

    def __init__(self, config: QuantizationConfig):
        self.config = config
        self._ranges: Dict[str, Tuple[float, float]] = {}

    def calibrate(self, layer_name: str, activations: List[float]) -> None:
        self._ranges[layer_name] = (min(activations), max(activations))

    def quantize(self, layer_name: str, activations: List[float]) -> QuantizedTensor:
        min_val, max_val = self._ranges.get(layer_name, (min(activations), max(activations)))
        scale = (max_val - min_val) / 255.0 if max_val != min_val else 1.0
        zero_point = int(-min_val / scale)
        quantized = [max(0, min(255, int(a / scale + zero_point))) for a in activations]
        return QuantizedTensor(
            quantized_values=quantized,
            scale=scale,
            zero_point=zero_point,
            shape=[len(activations)],
            dtype="int8",
            compression_ratio=4.0,
        )


class QuantizedModel:
    """Quantized model representation."""

    def __init__(self, model_id: str, name: str):
        self.model_id = model_id
        self.name = name
        self._weights: Dict[str, QuantizedTensor] = {}
        self._config: Optional[QuantizationConfig] = None
        self.quantized_at: Optional[float] = None

    def add_weight(self, name: str, tensor: QuantizedTensor) -> None:
        self._weights[name] = tensor

    def get_weight(self, name: str) -> Optional[QuantizedTensor]:
        return self._weights.get(name)

    def get_size_mb(self) -> float:
        total_bits = 0
        for tensor in self._weights.values():
            bits_per_param = {"int8": 8, "int4": 4, "fp16": 16, "fp32": 32}
            bits = bits_per_param.get(tensor.dtype, 32)
            total_bits += len(tensor.quantized_values) * bits
        return total_bits / (8 * 1024 * 1024)

    def get_compression_ratio(self) -> float:
        original_bits = sum(len(t.quantized_values) * 32 for t in self._weights.values())
        compressed_bits = sum(
            len(t.quantized_values) * {"int8": 8, "int4": 4, "fp16": 16, "fp32": 32}.get(t.dtype, 32)
            for t in self._weights.values()
        )
        return original_bits / max(compressed_bits, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "name": self.name,
            "weights": len(self._weights),
            "size_mb": round(self.get_size_mb(), 2),
            "compression_ratio": round(self.get_compression_ratio(), 2),
            "config": self._config.quant_type.value if self._config else None,
        }


class QuantizationEngine:
    """End-to-end quantization pipeline."""

    def __init__(self):
        self._quantized_models: Dict[str, QuantizedModel] = {}
        self._history: List[Dict[str, Any]] = []

    def quantize_model(self, model_id: str, name: str, weights: Dict[str, List[float]],
                       config: QuantizationConfig) -> QuantizedModel:
        weight_quantizer = WeightQuantizer(config)
        qmodel = QuantizedModel(model_id, name)
        qmodel._config = config
        for weight_name, weight_values in weights.items():
            tensor = weight_quantizer.quantize(weight_values)
            qmodel.add_weight(weight_name, tensor)
        qmodel.quantized_at = time.time()
        self._quantized_models[model_id] = qmodel
        self._history.append({
            "model_id": model_id,
            "config": config.quant_type.value,
            "compression_ratio": qmodel.get_compression_ratio(),
            "timestamp": time.time(),
        })
        return qmodel

    def get_model(self, model_id: str) -> Optional[QuantizedModel]:
        return self._quantized_models.get(model_id)

    def compare(self, model_id: str, weight_name: str) -> Dict[str, Any]:
        qmodel = self._quantized_models.get(model_id)
        if not qmodel:
            return {"error": "Model not found"}
        tensor = qmodel.get_weight(weight_name)
        if not tensor:
            return {"error": "Weight not found"}
        dequantized = tensor.dequantize()
        return {
            "weight_name": weight_name,
            "dtype": tensor.dtype,
            "compression_ratio": tensor.compression_ratio,
            "sample_original": tensor.quantized_values[:5],
            "sample_dequantized": [round(d, 4) for d in dequantized[:5]],
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "quantized_models": len(self._quantized_models),
            "avg_compression": sum(h["compression_ratio"] for h in self._history) / max(len(self._history), 1),
            "history": len(self._history),
        }

    def export(self, model_id: str, path: str) -> None:
        model = self._quantized_models.get(model_id)
        if model:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(model.to_dict(), f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("QUANTIZATION ENGINE DEMO")
    print("=" * 70)

    # Generate simulated weights
    random.seed(42)
    weights = {
        "layer1.weights": [random.gauss(0, 0.5) for _ in range(1000)],
        "layer2.weights": [random.gauss(0, 0.3) for _ in range(2000)],
        "layer3.weights": [random.gauss(0, 0.2) for _ in range(1500)],
    }

    # 1. INT8 quantization
    print("\n[1] INT8 Quantization")
    engine = QuantizationEngine()
    config_int8 = QuantizationConfig(QuantizationType.INT8, symmetric=True)
    qmodel_int8 = engine.quantize_model("model-1", "Test Model", weights, config_int8)
    print(f"  Model: {qmodel_int8.name}")
    print(f"  Size: {qmodel_int8.get_size_mb():.2f} MB")
    print(f"  Compression ratio: {qmodel_int8.get_compression_ratio():.1f}x")
    print(f"  Weights: {len(qmodel_int8._weights)}")

    # 2. INT4 quantization
    print("\n[2] INT4 Quantization")
    config_int4 = QuantizationConfig(QuantizationType.INT4)
    qmodel_int4 = engine.quantize_model("model-2", "Test Model INT4", weights, config_int4)
    print(f"  Size: {qmodel_int4.get_size_mb():.2f} MB")
    print(f"  Compression ratio: {qmodel_int4.get_compression_ratio():.1f}x")

    # 3. FP16 quantization
    print("\n[3] FP16 Quantization")
    config_fp16 = QuantizationConfig(QuantizationType.FP16)
    qmodel_fp16 = engine.quantize_model("model-3", "Test Model FP16", weights, config_fp16)
    print(f"  Size: {qmodel_fp16.get_size_mb():.2f} MB")
    print(f"  Compression ratio: {qmodel_fp16.get_compression_ratio():.1f}x")

    # 4. Compare dequantization
    print("\n[4] Dequantization Comparison")
    for model_id in ["model-1", "model-2"]:
        comp = engine.compare(model_id, "layer1.weights")
        print(f"  {model_id}: {comp['dtype']}")
        print(f"    Original sample: {comp['sample_original'][:5]}")
        print(f"    Dequantized sample: {comp['sample_dequantized'][:5]}")

    # 5. Activation quantization
    print("\n[5] Activation Quantization")
    act_quantizer = ActivationQuantizer(QuantizationConfig(QuantizationType.INT8))
    activations = [random.gauss(0, 1) for _ in range(100)]
    act_quantizer.calibrate("layer1", activations)
    q_act = act_quantizer.quantize("layer1", activations)
    print(f"  Activations: {len(activations)} -> {q_act.dtype}")
    print(f"  Scale: {q_act.scale:.4f}, Zero point: {q_act.zero_point}")
    deq = q_act.dequantize()[:5]
    print(f"  Dequantized sample: {[round(d, 4) for d in deq]}")

    # 6. Stats
    print(f"\n[6] Stats")
    print(f"  {engine.get_stats()}")

    # 7. Export
    print("\n[7] Export")
    engine.export("model-1", "/tmp/quantized_model.json")
    print("  Exported to /tmp/quantized_model.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
