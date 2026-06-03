"""LLM Architecture Builder — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class LayerSpec(Enum):
    ATTENTION = auto()
    FFN = auto()
    NORM = auto()
    DROPOUT = auto()
    RESIDUAL = auto()

@dataclass
class ArchitectureConfig:
    id: str
    name: str
    layers: List[LayerSpec] = field(default_factory=list)
    hidden_dim: int = 768
    num_heads: int = 12
    num_layers: int = 6
    metadata: Dict[str, Any] = field(default_factory=dict)

class ArchitectureBuilder:
    def __init__(self) -> None:
        self._configs: Dict[str, ArchitectureConfig] = {}

    def add(self, config: ArchitectureConfig) -> None:
        self._configs[config.id] = config

    def build_transformer(self, num_layers: int = 6, hidden_dim: int = 768, num_heads: int = 12) -> ArchitectureConfig:
        layers = []
        for _ in range(num_layers):
            layers.extend([LayerSpec.NORM, LayerSpec.ATTENTION, LayerSpec.RESIDUAL, LayerSpec.NORM, LayerSpec.FFN, LayerSpec.RESIDUAL])
        return ArchitectureConfig(
            id="transformer_" + str(num_layers),
            name="Standard Transformer",
            layers=layers,
            hidden_dim=hidden_dim,
            num_heads=num_heads,
            num_layers=num_layers
        )

    def build_mamba(self, num_layers: int = 6, hidden_dim: int = 768) -> ArchitectureConfig:
        layers = []
        for _ in range(num_layers):
            layers.extend([LayerSpec.NORM, LayerSpec.FFN, LayerSpec.DROPOUT])
        return ArchitectureConfig(
            id="mamba_" + str(num_layers),
            name="Mamba-style",
            layers=layers,
            hidden_dim=hidden_dim,
            num_layers=num_layers
        )

    def get_layer_count(self, config_id: str) -> Dict[str, int]:
        config = self._configs.get(config_id)
        if not config:
            return {}
        counts = {}
        for layer in config.layers:
            counts[layer.name] = counts.get(layer.name, 0) + 1
        return counts

    def get_stats(self) -> Dict[str, Any]:
        return {"configs": len(self._configs), "total_layers": sum(len(c.layers) for c in self._configs.values())}

def run() -> None:
    print("Architecture Builder test")
    e = ArchitectureBuilder()
    t = e.build_transformer(2, 512, 8)
    m = e.build_mamba(2, 512)
    e.add(t)
    e.add(m)
    print("  Transformer layers: " + str(e.get_layer_count(t.id)))
    print("  Mamba layers: " + str(e.get_layer_count(m.id)))
    print("  Stats: " + str(e.get_stats()))
    print("Architecture Builder test complete.")

if __name__ == "__main__":
    run()
