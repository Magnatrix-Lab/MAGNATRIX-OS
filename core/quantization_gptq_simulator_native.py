"""GPTQ Simulator — Weight grouping, inverse Hessian."""
from dataclasses import dataclass
from pathlib import Path
import json, math, random

@dataclass
class GPTQGroup:
    group_id: int = 0
    weights: list[float] = None
    quant_weights: list[int] = None
    scale: float = 1.0
    zero_point: float = 0.0

    def __post_init__(self):
        if self.weights is None:
            self.weights = []
        if self.quant_weights is None:
            self.quant_weights = []

class QuantizationGPTQSimulator:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._groups: list[GPTQGroup] = []
        self._config = {"bits": 4, "group_size": 128, "damp": 0.01}
        self._persist_path = self.root / "gptq_sim.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._groups = [GPTQGroup(**g) for g in data.get("groups", [])]
            self._config = data.get("config", self._config)

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "groups": [g.__dict__ for g in self._groups],
            "config": self._config
        }, indent=2))

    def quantize_group(self, weights: list[float], group_id: int = 0) -> GPTQGroup:
        bits = self._config["bits"]
        group_size = self._config["group_size"]
        # Simulate inverse Hessian approximation (simplified)
        h_inv = [1.0 / (abs(w) + self._config["damp"]) for w in weights[:group_size]]
        scale = (max(weights) - min(weights)) / (2**bits - 1) if max(weights) != min(weights) else 1.0
        zp = min(weights)
        quant = [int(round((w - zp) / scale)) if scale > 0 else 0 for w in weights[:group_size]]
        group = GPTQGroup(group_id=group_id, weights=weights[:group_size], quant_weights=quant, scale=scale, zero_point=zp)
        self._groups.append(group)
        self._save()
        return group

    def dequantize(self, group: GPTQGroup) -> list[float]:
        return [q * group.scale + group.zero_point for q in group.quant_weights]

    def set_config(self, bits: int, group_size: int, damp: float) -> None:
        self._config = {"bits": bits, "group_size": group_size, "damp": damp}
        self._save()

    def to_dict(self) -> dict:
        return {"config": self._config, "group_count": len(self._groups)}

    def get_stats(self) -> dict:
        return {"groups": len(self._groups), "bits": self._config["bits"], "group_size": self._config["group_size"]}

__all__ = ["QuantizationGPTQSimulator", "GPTQGroup"]
