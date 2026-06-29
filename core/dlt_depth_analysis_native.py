"""DLT Depth Analysis - Benefits of depth in neural networks."""
from __future__ import annotations
import json, math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

@dataclass
class DepthComparison:
    comparison_id: str
    target_function: str
    depth: int
    width: int
    required_width: int
    approximation_quality: float

    def to_dict(self) -> Dict:
        return {"comparison_id": self.comparison_id, "target_function": self.target_function,
                "depth": self.depth, "width": self.width,
                "required_width": self.required_width, "approximation_quality": round(self.approximation_quality,4)}

class DLTDepthAnalysis:
    """Analysis of depth benefits: depth separation, x^2 approximation, Sobolev."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "dlt_depth"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.comparisons: List[DepthComparison] = []
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for c in data.get("comparisons",[]): self.comparisons.append(DepthComparison(**c))
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"comparisons": [c.to_dict() for c in self.comparisons]}, indent=2))

    def _approx_x2(self, depth: int, width: int) -> float:
        """Simulate x^2 approximation quality. Depth helps significantly."""
        if depth < 2: return 0.1
        base = 1.0 / width
        return min(1.0, base * (2 ** depth) / 10)

    def _approximate_sobolev(self, depth: int, width: int, smoothness: float) -> float:
        """Approximation quality for Sobolev ball functions."""
        if depth < 2: return 1.0 / (width ** smoothness)
        return 1.0 / ((width * depth) ** smoothness)

    def compare_depth(self, target: str, depth: int, width: int, smoothness: float = 1.0) -> DepthComparison:
        if target == "x2":
            quality = self._approx_x2(depth, width)
            req_width = max(1, int(width / (2 ** depth)))
        elif target == "sobolev":
            quality = self._approximate_sobolev(depth, width, smoothness)
            req_width = max(1, int(width / depth))
        else:
            quality = 1.0 / (width * depth)
            req_width = width * depth
        comp = DepthComparison(
            comparison_id=f"depth_{target}_{depth}_{width}_{int(time.time())}",
            target_function=target, depth=depth, width=width,
            required_width=req_width, approximation_quality=round(quality,6))
        self.comparisons.append(comp)
        self._save_state()
        return comp

    def depth_separation(self, target: str, max_depth: int = 6, width: int = 100) -> List[DepthComparison]:
        return [self.compare_depth(target, d, width) for d in range(1, max_depth + 1)]

    def get_stats(self) -> Dict:
        if not self.comparisons: return {"comparisons_total": 0}
        avg_qual = sum(c.approximation_quality for c in self.comparisons) / len(self.comparisons)
        return {"comparisons_total": len(self.comparisons), "avg_quality": round(avg_qual,6)}

    def to_dict(self) -> Dict:
        return {"comparisons": [c.to_dict() for c in self.comparisons], "stats": self.get_stats()}

__all__ = ["DLTDepthAnalysis", "DepthComparison"]
