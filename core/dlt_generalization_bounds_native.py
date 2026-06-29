"""DLT Generalization Bounds - Rademacher complexity, VC dimension, generalization."""
from __future__ import annotations
import json, math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class GeneralizationBound:
    bound_id: str
    bound_type: str
    sample_size: int
    complexity_measure: float
    generalization_gap: float
    confidence: float = 0.95

    def to_dict(self) -> Dict:
        return {"bound_id": self.bound_id, "bound_type": self.bound_type,
                "sample_size": self.sample_size, "complexity_measure": round(self.complexity_measure,4),
                "generalization_gap": round(self.generalization_gap,6), "confidence": self.confidence}

class DLTGeneralizationBounds:
    """Generalization bounds: Rademacher complexity, VC dimension, margin bounds."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "dlt_generalization"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.bounds: List[GeneralizationBound] = []
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for b in data.get("bounds",[]): self.bounds.append(GeneralizationBound(**b))
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"bounds": [b.to_dict() for b in self.bounds]}, indent=2))

    def rademacher_bound(self, depth: int, width: int, sample_size: int, lipschitz: float = 1.0) -> GeneralizationBound:
        """Rademacher complexity bound for ReLU networks."""
        complexity = lipschitz * math.sqrt(depth) * width / math.sqrt(sample_size)
        gap = 2 * complexity + 3 * math.sqrt(math.log(2/0.05) / (2 * sample_size))
        bound = GeneralizationBound(
            bound_id=f"rad_d{depth}_w{width}_n{sample_size}",
            bound_type="rademacher", sample_size=sample_size,
            complexity_measure=round(complexity,4), generalization_gap=round(gap,6))
        self.bounds.append(bound)
        self._save_state()
        return bound

    def vc_bound(self, num_parameters: int, sample_size: int) -> GeneralizationBound:
        """VC dimension bound."""
        vc_dim = num_parameters
        gap = math.sqrt(2 * vc_dim * math.log(math.e * sample_size / vc_dim) / sample_size) if vc_dim < sample_size else 1.0
        bound = GeneralizationBound(
            bound_id=f"vc_p{num_parameters}_n{sample_size}",
            bound_type="vc_dimension", sample_size=sample_size,
            complexity_measure=vc_dim, generalization_gap=round(gap,6))
        self.bounds.append(bound)
        self._save_state()
        return bound

    def margin_bound(self, margin: float, rho: float, sample_size: int) -> GeneralizationBound:
        """Margin-based generalization bound."""
        gap = rho / (margin * math.sqrt(sample_size))
        bound = GeneralizationBound(
            bound_id=f"margin_{margin}_{sample_size}",
            bound_type="margin", sample_size=sample_size,
            complexity_measure=round(rho,4), generalization_gap=round(gap,6))
        self.bounds.append(bound)
        self._save_state()
        return bound

    def get_stats(self) -> Dict:
        if not self.bounds: return {"bounds_total": 0}
        avg_gap = sum(b.generalization_gap for b in self.bounds) / len(self.bounds)
        return {"bounds_total": len(self.bounds), "avg_gap": round(avg_gap,6)}

    def to_dict(self) -> Dict:
        return {"bounds": [b.to_dict() for b in self.bounds], "stats": self.get_stats()}

__all__ = ["DLTGeneralizationBounds", "GeneralizationBound"]
