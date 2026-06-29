"""
medical_model_adapter_native.py
MAGNATRIX-OS — Medical Model Adapter

Inspired by Meditron (EPFL): Domain adaptation for medical LLMs with continual pretraining simulation. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class TrainingRun:
    run_id: str
    model_name: str
    base_model: str
    dataset: str
    epochs: int
    batch_size: int
    learning_rate: float
    status: str = "pending"
    loss_history: List[float] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""

    def __post_init__(self):
        if not self.started_at:
            self.started_at = datetime.now().isoformat()


class MedicalModelAdapter:
    """Domain adaptation for medical LLMs with continual pretraining simulation."""

    def __init__(self, adapter_dir: str = "./medical_model_adapter"):
        self.adapter_dir = Path(adapter_dir)
        self.adapter_dir.mkdir(exist_ok=True)
        self.runs: Dict[str, TrainingRun] = {}
        self._load()

    def _load(self) -> None:
        file = self.adapter_dir / "runs.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for rid, rd in data.items():
                        self.runs[rid] = TrainingRun(**rd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.adapter_dir / "runs.json", "w", encoding="utf-8") as f:
            json.dump({rid: asdict(r) for rid, r in self.runs.items()}, f, indent=2)

    def create_run(self, run_id: str, model_name: str, base_model: str, dataset: str,
                   epochs: int = 3, batch_size: int = 32, learning_rate: float = 2e-5) -> TrainingRun:
        run = TrainingRun(
            run_id=run_id, model_name=model_name, base_model=base_model,
            dataset=dataset, epochs=epochs, batch_size=batch_size, learning_rate=learning_rate,
        )
        self.runs[run_id] = run
        self._save()
        return run

    def start_training(self, run_id: str) -> bool:
        run = self.runs.get(run_id)
        if not run:
            return False
        run.status = "training"
        self._save()
        return True

    def log_epoch(self, run_id: str, epoch: int, loss: float) -> bool:
        run = self.runs.get(run_id)
        if not run or run.status != "training":
            return False
        run.loss_history.append(loss)
        if epoch >= run.epochs - 1:
            run.status = "completed"
            run.completed_at = datetime.now().isoformat()
        self._save()
        return True

    def get_run(self, run_id: str) -> Optional[TrainingRun]:
        return self.runs.get(run_id)

    def get_best_run(self) -> Optional[TrainingRun]:
        if not self.runs:
            return None
        return min(self.runs.values(), key=lambda r: min(r.loss_history) if r.loss_history else float('inf'))

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.runs)
        completed = sum(1 for r in self.runs.values() if r.status == "completed")
        training = sum(1 for r in self.runs.values() if r.status == "training")
        return {"runs": total, "completed": completed, "training": training}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["MedicalModelAdapter", "TrainingRun"]