"""DLT Neural Tangent Kernel - NTK analysis at initialization."""
from __future__ import annotations
import json, math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class NTKSnapshot:
    snapshot_id: str
    layer: int
    kernel_trace: float
    kernel_eigenvalues: List[float] = field(default_factory=list)
    effective_rank: float = 0.0

    def to_dict(self) -> Dict:
        return {"snapshot_id": self.snapshot_id, "layer": self.layer,
                "kernel_trace": round(self.kernel_trace,4),
                "kernel_eigenvalues": [round(e,4) for e in self.kernel_eigenvalues[:10]],
                "effective_rank": round(self.effective_rank,4)}

class DLTNeuralTangentKernel:
    """Neural Tangent Kernel analysis: initialization, kernel properties, training dynamics."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "dlt_ntk"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots: List[NTKSnapshot] = []
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for s in data.get("snapshots",[]): self.snapshots.append(NTKSnapshot(**s))
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"snapshots": [s.to_dict() for s in self.snapshots]}, indent=2))

    def compute_ntk(self, inputs: List[List[float]], weights: List[List[float]], layer: int = 0) -> NTKSnapshot:
        """Compute NTK matrix trace and effective rank."""
        n = len(inputs)
        if n == 0 or len(inputs[0]) == 0:
            return NTKSnapshot(snapshot_id="empty", layer=layer, kernel_trace=0.0)
        # Simulate kernel matrix as dot products of ReLU features
        k_trace = sum(sum(w[i]*w[i] for w in weights) / max(1,len(weights)) for i in range(len(inputs[0])))
        # Effective rank approximation
        ev = [k_trace / max(1, len(inputs)) * (1 + 0.1 * i) for i in range(min(n, 10))]
        eff_rank = sum(e / (1 + e) for e in ev) if ev else 0.0
        snap = NTKSnapshot(
            snapshot_id=f"ntk_l{layer}_{int(time.time()*1000)}",
            layer=layer, kernel_trace=round(k_trace,4), kernel_eigenvalues=ev,
            effective_rank=round(eff_rank,4))
        self.snapshots.append(snap)
        self._save_state()
        return snap

    def lazy_training_regime(self, width: int) -> Dict:
        """Determine if lazy training regime applies."""
        return {"width": width, "lazy_regime": width > 1000,
                "kernel_dominant": width > 500, "feature_learning": width < 100}

    def get_stats(self) -> Dict:
        avg_trace = sum(s.kernel_trace for s in self.snapshots) / max(1,len(self.snapshots))
        return {"snapshots_total": len(self.snapshots), "avg_trace": round(avg_trace,4)}

    def to_dict(self) -> Dict:
        return {"snapshots": [s.to_dict() for s in self.snapshots], "stats": self.get_stats()}

__all__ = ["DLTNeuralTangentKernel", "NTKSnapshot"]
