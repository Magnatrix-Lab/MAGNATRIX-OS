"""Multimodal Fusion - Cross-modal fusion for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math

class FusionType(Enum):
    EARLY = auto(); LATE = auto(); INTERMEDIATE = auto()

@dataclass
class MultimodalFusion:
    fusion_type: FusionType = FusionType.LATE
    modalities: Dict[str, List[float]] = field(default_factory=dict)

    def add_modality(self, name: str, features: List[float]) -> None:
        self.modalities[name] = features

    def fuse(self) -> List[float]:
        if self.fusion_type == FusionType.EARLY:
            return [sum(vals)/len(vals) for vals in zip(*self.modalities.values())]
        elif self.fusion_type == FusionType.LATE:
            return [sum(v for vals in self.modalities.values() for v in vals) / len(self.modalities)]
        return [sum(v for vals in self.modalities.values() for v in vals)]

    def stats(self) -> dict:
        return {"type": self.fusion_type.name, "modalities": list(self.modalities.keys())}

def run():
    mf = MultimodalFusion(FusionType.EARLY)
    mf.add_modality("text", [0.1, 0.2, 0.3])
    mf.add_modality("image", [0.4, 0.5, 0.6])
    print("Fused:", [round(v, 4) for v in mf.fuse()])
    print("Stats:", mf.stats())

if __name__ == "__main__": run()
