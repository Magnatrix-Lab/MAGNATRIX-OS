"""TMax Training Launcher -- Beaker-style config management, experiment launch."""
from dataclasses import dataclass
from pathlib import Path
import json, time

@dataclass
class ExperimentConfig:
    config_id: str = ""
    name: str = ""
    model_name: str = ""
    dataset_path: str = ""
    output_dir: str = ""
    epochs: int = 3
    batch_size: int = 32
    learning_rate: float = 2e-5
    warmup_steps: int = 100
    max_grad_norm: float = 1.0
    seed: int = 42
    mixed_precision: bool = True
    gradient_checkpointing: bool = False
    deepspeed_config: str = ""
    env_vars: dict = None

    def __post_init__(self):
        if self.env_vars is None:
            self.env_vars = {}

class TmaxTrainingLauncher:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._configs: dict[str, ExperimentConfig] = {}
        self._launches: list[dict] = []
        self._persist_path = self.root / "tmax_launcher.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._configs = {k: ExperimentConfig(**v) for k, v in data.get("configs", {}).items()}
            self._launches = data.get("launches", [])

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "configs": {k: v.__dict__ for k, v in self._configs.items()},
            "launches": self._launches
        }, indent=2))

    def create_config(self, config_id: str, name: str, model_name: str, dataset_path: str, output_dir: str) -> ExperimentConfig:
        config = ExperimentConfig(config_id=config_id, name=name, model_name=model_name, dataset_path=dataset_path, output_dir=output_dir)
        self._configs[config_id] = config
        self._save()
        return config

    def set_hyperparams(self, config_id: str, epochs: int = None, batch_size: int = None, lr: float = None, warmup: int = None) -> bool:
        config = self._configs.get(config_id)
        if not config:
            return False
        if epochs is not None:
            config.epochs = epochs
        if batch_size is not None:
            config.batch_size = batch_size
        if lr is not None:
            config.learning_rate = lr
        if warmup is not None:
            config.warmup_steps = warmup
        self._save()
        return True

    def set_env(self, config_id: str, key: str, value: str) -> bool:
        config = self._configs.get(config_id)
        if config:
            config.env_vars[key] = value
            self._save()
            return True
        return False

    def launch(self, config_id: str) -> dict:
        config = self._configs.get(config_id)
        if not config:
            return {"error": "Config not found"}
        launch_record = {
            "launch_id": "launch_" + str(len(self._launches)),
            "config_id": config_id,
            "timestamp": time.time(),
            "status": "started"
        }
        self._launches.append(launch_record)
        self._save()
        return launch_record

    def complete_launch(self, launch_id: str, metrics: dict) -> bool:
        for launch in self._launches:
            if launch.get("launch_id") == launch_id:
                launch["status"] = "completed"
                launch["metrics"] = metrics
                launch["completed_at"] = time.time()
                self._save()
                return True
        return False

    def get_config(self, config_id: str) -> ExperimentConfig | None:
        return self._configs.get(config_id)

    def to_dict(self) -> dict:
        return {"config_count": len(self._configs), "launches": len(self._launches)}

    def get_stats(self) -> dict:
        by_status = {}
        for l in self._launches:
            by_status[l.get("status", "unknown")] = by_status.get(l.get("status", "unknown"), 0) + 1
        return {"configs": len(self._configs), "launches": len(self._launches), "by_status": by_status}

__all__ = ["TmaxTrainingLauncher", "ExperimentConfig"]
