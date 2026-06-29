"""Layer Fuser — Conv+BN, Linear+ReLU fusion simulation."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class FusedLayer:
    name: str = ""
    op_type: str = ""  # conv_bn | linear_relu | etc
    input_ops: list[str] = None
    params: dict = None

    def __post_init__(self):
        if self.input_ops is None:
            self.input_ops = []
        if self.params is None:
            self.params = {}

class QuantizationLayerFuser:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._fused: list[FusedLayer] = []
        self._fusion_rules = ["conv_bn", "linear_relu", "conv_bn_relu"]
        self._persist_path = self.root / "layer_fuser.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._fused = [FusedLayer(**f) for f in data.get("fused", [])]
            self._fusion_rules = data.get("rules", self._fusion_rules)

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "fused": [f.__dict__ for f in self._fused],
            "rules": self._fusion_rules
        }, indent=2))

    def fuse_conv_bn(self, conv_name: str, bn_name: str, weights: list[float], bn_mean: list[float], bn_var: list[float], bn_gamma: list[float], bn_beta: list[float], eps: float = 1e-5) -> FusedLayer:
        # Fused weight = gamma / sqrt(var + eps) * weight
        # Fused bias = beta - gamma * mean / sqrt(var + eps)
        fused_w = [w * g / ((v + eps) ** 0.5) for w, g, v in zip(weights, bn_gamma, bn_var)]
        fused_b = [b - g * m / ((v + eps) ** 0.5) for b, g, m, v in zip(bn_beta, bn_gamma, bn_mean, bn_var)]
        fused = FusedLayer(
            name=f"{conv_name}_{bn_name}_fused",
            op_type="conv_bn",
            input_ops=[conv_name, bn_name],
            params={"weights": fused_w, "bias": fused_b}
        )
        self._fused.append(fused)
        self._save()
        return fused

    def fuse_linear_relu(self, linear_name: str, weights: list[float], bias: list[float]) -> FusedLayer:
        fused = FusedLayer(
            name=f"{linear_name}_relu_fused",
            op_type="linear_relu",
            input_ops=[linear_name],
            params={"weights": weights, "bias": bias, "activation": "relu"}
        )
        self._fused.append(fused)
        self._save()
        return fused

    def list_fused(self) -> list[FusedLayer]:
        return self._fused

    def to_dict(self) -> dict:
        return {"fused_count": len(self._fused), "rules": self._fusion_rules}

    def get_stats(self) -> dict:
        return {"fused": len(self._fused), "by_type": {t: sum(1 for f in self._fused if f.op_type == t) for t in set(f.op_type for f in self._fused)}}

__all__ = ["QuantizationLayerFuser", "FusedLayer"]
