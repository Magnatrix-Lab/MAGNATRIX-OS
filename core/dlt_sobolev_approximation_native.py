"""DLT Sobolev Approximation - Sobolev space approximation rates for neural networks."""
from __future__ import annotations
import json, math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class SobolevApproximation:
    approx_id: str
    function_class: str
    smoothness: float
    dimension: int
    depth: int
    width: int
    approximation_rate: float
    lower_bound: float

    def to_dict(self) -> Dict:
        return {"approx_id": self.approx_id, "function_class": self.function_class,
                "smoothness": self.smoothness, "dimension": self.dimension,
                "depth": self.depth, "width": self.width,
                "approximation_rate": round(self.approximation_rate,6),
                "lower_bound": round(self.lower_bound,6)}

class DLTSobolevApproximation:
    """Sobolev space approximation: rates, curse of dimensionality, depth benefits."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "dlt_sobolev"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.approximations: List[SobolevApproximation] = []
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for a in data.get("approximations",[]): self.approximations.append(SobolevApproximation(**a))
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"approximations": [a.to_dict() for a in self.approximations]}, indent=2))

    def approximation_rate(self, smoothness: float, dimension: int, depth: int, width: int) -> Tuple[float,float]:
        """Compute upper and lower bounds for Sobolev approximation."""
        # Upper bound: rate ~ N^(-smoothness/d) for shallow, better for deep
        n = width * depth
        upper = n ** (-smoothness / max(1, dimension))
        if depth >= 2:
            upper = upper * (depth ** 0.5)
        # Lower bound from min-max theory
        lower = n ** (-smoothness / max(1, dimension))
        return round(upper,6), round(lower,6)

    def compute(self, function_class: str, smoothness: float, dimension: int, depth: int, width: int) -> SobolevApproximation:
        upper, lower = self.approximation_rate(smoothness, dimension, depth, width)
        approx = SobolevApproximation(
            approx_id=f"sob_{function_class}_s{smoothness}_d{dimension}_{depth}_{width}",
            function_class=function_class, smoothness=smoothness, dimension=dimension,
            depth=depth, width=width, approximation_rate=upper, lower_bound=lower)
        self.approximations.append(approx)
        self._save_state()
        return approx

    def curse_of_dimensionality(self, smoothness: float, dimension: int) -> Dict:
        """Measure curse of dimensionality for given smoothness."""
        required = math.exp(dimension / smoothness) if smoothness > 0 else float("inf")
        return {"smoothness": smoothness, "dimension": dimension,
                "exponential_growth": required > 1000,
                "required_parameters_estimate": round(required,1)}

    def get_stats(self) -> Dict:
        if not self.approximations: return {"approximations_total": 0}
        avg_rate = sum(a.approximation_rate for a in self.approximations) / len(self.approximations)
        return {"approximations_total": len(self.approximations), "avg_rate": round(avg_rate,6)}

    def to_dict(self) -> Dict:
        return {"approximations": [a.to_dict() for a in self.approximations], "stats": self.get_stats()}

__all__ = ["DLTSobolevApproximation", "SobolevApproximation"]
