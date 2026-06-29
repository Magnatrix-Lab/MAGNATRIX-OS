"""DLT Optimization Theory - Gradient descent, convexity, smoothness, convergence."""
from __future__ import annotations
import json, math, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class OptimizationTrace:
    trace_id: str
    optimizer: str
    learning_rate: float
    iterations: int
    final_loss: float
    convergence_rate: float
    smoothness: float = 0.0
    strong_convexity: float = 0.0

    def to_dict(self) -> Dict:
        return {"trace_id": self.trace_id, "optimizer": self.optimizer,
                "learning_rate": self.learning_rate, "iterations": self.iterations,
                "final_loss": round(self.final_loss,6), "convergence_rate": round(self.convergence_rate,6),
                "smoothness": round(self.smoothness,4), "strong_convexity": round(self.strong_convexity,4)}

class DLTOptimizationTheory:
    """Optimization theory: gradient descent, smoothness, strong convexity, rates."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "dlt_opt"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.traces: List[OptimizationTrace] = []
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for t in data.get("traces",[]): self.traces.append(OptimizationTrace(**t))
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"traces": [t.to_dict() for t in self.traces]}, indent=2))

    def gradient_descent_rate(self, smoothness: float, strong_convexity: float, lr: float, iterations: int) -> float:
        """Compute convergence rate for gradient descent on smooth convex objective."""
        if smoothness <= 0: return 0.0
        if strong_convexity > 0:
            kappa = smoothness / strong_convexity
            rate = (1 - 1.0 / kappa) ** iterations
        else:
            rate = smoothness / (2 * iterations)
        return round(rate, 6)

    def simulate_gd(self, initial_loss: float, lr: float, iterations: int, smoothness: float, strong_convexity: float = 0.0) -> OptimizationTrace:
        rate = self.gradient_descent_rate(smoothness, strong_convexity, lr, iterations)
        final_loss = initial_loss * rate
        trace = OptimizationTrace(
            trace_id=f"gd_{lr}_{iterations}_{int(time.time())}",
            optimizer="gradient_descent", learning_rate=lr, iterations=iterations,
            final_loss=round(final_loss,6), convergence_rate=round(rate,6),
            smoothness=round(smoothness,4), strong_convexity=round(strong_convexity,4))
        self.traces.append(trace)
        self._save_state()
        return trace

    def polyak_step_size(self, gradient_norm: float, loss: float) -> float:
        """Compute Polyak step size."""
        if gradient_norm <= 0: return 0.01
        return loss / (gradient_norm ** 2)

    def get_stats(self) -> Dict:
        if not self.traces: return {"traces_total": 0}
        avg_loss = sum(t.final_loss for t in self.traces) / len(self.traces)
        return {"traces_total": len(self.traces), "avg_final_loss": round(avg_loss,6)}

    def to_dict(self) -> Dict:
        return {"traces": [t.to_dict() for t in self.traces], "stats": self.get_stats()}

__all__ = ["DLTOptimizationTheory", "OptimizationTrace"]
