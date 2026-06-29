"""DLT Approximation Theory - Universal approximation, Barron norm, Fourier representations."""
from __future__ import annotations
import json, math, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

@dataclass
class ApproximationResult:
    result_id: str
    target_function: str
    network_depth: int
    network_width: int
    approximation_error: float
    error_metric: str = "L2"
    barron_norm: float = 0.0

    def to_dict(self) -> Dict:
        return {"result_id": self.result_id, "target_function": self.target_function,
                "network_depth": self.network_depth, "network_width": self.network_width,
                "approximation_error": round(self.approximation_error,6),
                "error_metric": self.error_metric, "barron_norm": round(self.barron_norm,4)}

class DLTApproximationTheory:
    """Neural network approximation theory: universal approximation, Barron norm, Fourier."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "dlt_approx"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[ApproximationResult] = []
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for r in data.get("results",[]): self.results.append(ApproximationResult(**r))
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"results": [r.to_dict() for r in self.results]}, indent=2))

    def _relu(self, x: float) -> float:
        return max(0.0, x)

    def universal_approximation_error(self, target: str, width: int, domain: Tuple[float,float] = (-1.0,1.0)) -> float:
        """Simulate universal approximation error for single-hidden-layer network."""
        if target == "sin":
            return 1.0 / (width + 1)
        elif target == "x2":
            return 0.5 / width
        elif target == "abs":
            return 1.0 / math.sqrt(width)
        else:
            return 2.0 / width

    def barron_norm_estimate(self, fourier_coefficients: List[float]) -> float:
        """Estimate Barron norm from Fourier coefficients."""
        return sum(abs(c) * (1 + i) for i, c in enumerate(fourier_coefficients))

    def fourier_representation(self, frequencies: List[float], amplitudes: List[float], x: float) -> float:
        """Evaluate infinite-width Fourier network representation."""
        return sum(a * math.sin(2 * math.pi * freq * x) for freq, a in zip(frequencies, amplitudes))

    def approximate(self, target_function: str, depth: int, width: int, barron_norm: float = 0.0) -> ApproximationResult:
        error = self.universal_approximation_error(target_function, width)
        if depth > 1:
            error = error / (depth ** 0.5)
        result = ApproximationResult(
            result_id=f"approx_{target_function}_{depth}_{width}_{int(time.time())}",
            target_function=target_function, network_depth=depth, network_width=width,
            approximation_error=round(error,6), barron_norm=round(barron_norm,4))
        self.results.append(result)
        self._save_state()
        return result

    def compare_depths(self, target: str, max_depth: int = 5, width: int = 100) -> List[ApproximationResult]:
        return [self.approximate(target, d, width) for d in range(1, max_depth + 1)]

    def get_stats(self) -> Dict:
        avg_err = sum(r.approximation_error for r in self.results) / max(1,len(self.results))
        return {"results_total": len(self.results), "avg_error": round(avg_err,6)}

    def to_dict(self) -> Dict:
        return {"results": [r.to_dict() for r in self.results], "stats": self.get_stats()}

__all__ = ["DLTApproximationTheory", "ApproximationResult"]
