"""Neural Network Pruning — magnitude & structured pruning, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum, auto
import math

class PruneType(Enum):
    MAGNITUDE = auto()
    STRUCTURED = auto()

@dataclass
class PrunedLayer:
    name: str
    original_weights: List[float]
    mask: List[int]
    pruned_weights: List[float] = field(default_factory=list)
    sparsity: float = 0.0

    def __post_init__(self):
        self.pruned_weights = [w * m for w, m in zip(self.original_weights, self.mask)]
        self.sparsity = 1.0 - sum(self.mask) / len(self.mask)

class ModelPruner:
    def __init__(self, prune_type: PruneType = PruneType.MAGNITUDE, target_sparsity: float = 0.5):
        self.prune_type = prune_type
        self.target_sparsity = target_sparsity
        self.layers: Dict[str, PrunedLayer] = {}

    def _magnitude_mask(self, weights: List[float]) -> List[int]:
        threshold = sorted(abs(w) for w in weights)[int(len(weights) * self.target_sparsity)]
        return [1 if abs(w) >= threshold else 0 for w in weights]

    def _structured_mask(self, weights: List[float], block_size: int = 4) -> List[int]:
        blocks = [weights[i:i+block_size] for i in range(0, len(weights), block_size)]
        norms = [sum(w*w for w in b) for b in blocks]
        threshold = sorted(norms)[int(len(norms) * self.target_sparsity)]
        keep = [1 if n >= threshold else 0 for n in norms]
        mask = []
        for k, b in zip(keep, blocks):
            mask.extend([k] * len(b))
        return mask[:len(weights)]

    def prune(self, name: str, weights: List[float]) -> PrunedLayer:
        if self.prune_type == PruneType.MAGNITUDE:
            mask = self._magnitude_mask(weights)
        else:
            mask = self._structured_mask(weights)
        layer = PrunedLayer(name, weights, mask)
        self.layers[name] = layer
        return layer

    def stats(self) -> Dict:
        total_params = sum(len(l.original_weights) for l in self.layers.values())
        total_zero = sum(sum(1 for m in l.mask if m == 0) for l in self.layers.values())
        return {"layers": len(self.layers), "total_params": total_params, "total_zeros": total_zero, "overall_sparsity": total_zero / total_params if total_params else 0}

def run():
    pruner = ModelPruner(PruneType.MAGNITUDE, target_sparsity=0.5)
    weights = [0.1, -0.5, 0.8, -0.2, 0.05, 0.9, -0.3, 0.4, 0.01, -0.6]
    layer = pruner.prune("layer1", weights)
    print("Sparsity:", layer.sparsity, "Mask:", layer.mask)
    print(pruner.stats())

if __name__ == "__main__":
    run()
