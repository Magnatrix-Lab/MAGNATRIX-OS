"""DLT Gradient Flow - Gradient flow dynamics and implicit regularization."""
from __future__ import annotations
import json, math, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class FlowTrajectory:
    trajectory_id: str
    initial_loss: float
    final_loss: float
    time_span: float
    implicit_rank: int
    weight_norm: float
    margin: float

    def to_dict(self) -> Dict:
        return {"trajectory_id": self.trajectory_id, "initial_loss": round(self.initial_loss,6),
                "final_loss": round(self.final_loss,6), "time_span": round(self.time_span,4),
                "implicit_rank": self.implicit_rank, "weight_norm": round(self.weight_norm,4),
                "margin": round(self.margin,6)}

class DLTGradientFlow:
    """Gradient flow dynamics: implicit regularization, margin maximization, rank minimization."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "dlt_flow"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.trajectories: List[FlowTrajectory] = []
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for t in data.get("trajectories",[]): self.trajectories.append(FlowTrajectory(**t))
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"trajectories": [t.to_dict() for t in self.trajectories]}, indent=2))

    def simulate_flow(self, initial_loss: float, time_span: float, separable: bool = True) -> FlowTrajectory:
        """Simulate gradient flow trajectory for separable data."""
        if separable:
            final_loss = initial_loss * math.exp(-time_span)
            margin = min(1.0, time_span * 0.1)
            weight_norm = math.sqrt(time_span)
            rank = max(1, int(time_span / 10))
        else:
            final_loss = initial_loss / (1 + time_span)
            margin = 0.0
            weight_norm = time_span
            rank = 5
        traj = FlowTrajectory(
            trajectory_id=f"flow_{int(time.time()*1000)}",
            initial_loss=initial_loss, final_loss=round(final_loss,6),
            time_span=round(time_span,4), implicit_rank=rank,
            weight_norm=round(weight_norm,4), margin=round(margin,6))
        self.trajectories.append(traj)
        self._save_state()
        return traj

    def implicit_regularization(self, trajectory_id: str) -> Dict:
        traj = next((t for t in self.trajectories if t.trajectory_id == trajectory_id), None)
        if not traj: return {}
        return {"trajectory_id": trajectory_id, "weight_norm_growth": round(traj.weight_norm,4),
                "margin_evolution": round(traj.margin,6), "implicit_rank": traj.implicit_rank,
                "loss_decay": round(traj.initial_loss - traj.final_loss,6)}

    def get_stats(self) -> Dict:
        if not self.trajectories: return {"trajectories_total": 0}
        avg_margin = sum(t.margin for t in self.trajectories) / len(self.trajectories)
        return {"trajectories_total": len(self.trajectories), "avg_margin": round(avg_margin,6)}

    def to_dict(self) -> Dict:
        return {"trajectories": [t.to_dict() for t in self.trajectories], "stats": self.get_stats()}

__all__ = ["DLTGradientFlow", "FlowTrajectory"]
