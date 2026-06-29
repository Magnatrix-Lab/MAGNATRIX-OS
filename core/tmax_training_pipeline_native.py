"""TMax Terminal Agent Training Pipeline -- End-to-end training orchestration."""
from dataclasses import dataclass
from pathlib import Path
import json, time

@dataclass
class TrainingRun:
    run_id: str = ""
    model_name: str = ""
    dataset: str = ""
    epochs: int = 0
    batch_size: int = 0
    learning_rate: float = 0.0
    status: str = "pending"  # pending | running | completed | failed
    started_at: float = 0.0
    completed_at: float = 0.0
    metrics: dict = None

    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {}

class TmaxTrainingPipeline:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._runs: dict[str, TrainingRun] = {}
        self._persist_path = self.root / "tmax_training.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._runs = {k: TrainingRun(**v) for k, v in data.get("runs", {}).items()}

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "runs": {k: v.__dict__ for k, v in self._runs.items()}
        }, indent=2))

    def create_run(self, run_id: str, model_name: str, dataset: str, epochs: int = 3, batch_size: int = 32, lr: float = 2e-5) -> TrainingRun:
        run = TrainingRun(
            run_id=run_id, model_name=model_name, dataset=dataset,
            epochs=epochs, batch_size=batch_size, learning_rate=lr,
            started_at=time.time(), status="pending"
        )
        self._runs[run_id] = run
        self._save()
        return run

    def start(self, run_id: str) -> bool:
        run = self._runs.get(run_id)
        if run:
            run.status = "running"
            self._save()
            return True
        return False

    def update_metrics(self, run_id: str, metrics: dict) -> bool:
        run = self._runs.get(run_id)
        if run:
            run.metrics.update(metrics)
            self._save()
            return True
        return False

    def complete(self, run_id: str, final_metrics: dict) -> bool:
        run = self._runs.get(run_id)
        if run:
            run.status = "completed"
            run.completed_at = time.time()
            run.metrics.update(final_metrics)
            self._save()
            return True
        return False

    def fail(self, run_id: str, error: str) -> bool:
        run = self._runs.get(run_id)
        if run:
            run.status = "failed"
            run.metrics["error"] = error
            self._save()
            return True
        return False

    def list_runs(self) -> list[TrainingRun]:
        return list(self._runs.values())

    def get_best(self, metric: str = "accuracy") -> TrainingRun | None:
        completed = [r for r in self._runs.values() if r.status == "completed"]
        if not completed:
            return None
        return max(completed, key=lambda r: r.metrics.get(metric, 0))

    def to_dict(self) -> dict:
        return {"run_count": len(self._runs)}

    def get_stats(self) -> dict:
        by_status = {}
        for r in self._runs.values():
            by_status[r.status] = by_status.get(r.status, 0) + 1
        return {"runs": len(self._runs), "by_status": by_status}

__all__ = ["TmaxTrainingPipeline", "TrainingRun"]
