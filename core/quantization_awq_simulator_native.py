"""AWQ Simulator — Activation-aware scaling."""
from dataclasses import dataclass
from pathlib import Path
import json, math

@dataclass
class AWQChannel:
    channel_id: int = 0
    salience_score: float = 0.0
    original_scale: float = 1.0
    optimized_scale: float = 1.0
    protected: bool = False

class QuantizationAWQSimulator:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._channels: list[AWQChannel] = []
        self._config = {"n_bits": 4, "zero_point": True, "q_group_size": 128}
        self._persist_path = self.root / "awq_sim.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._channels = [AWQChannel(**c) for c in data.get("channels", [])]
            self._config = data.get("config", self._config)

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "channels": [c.__dict__ for c in self._channels],
            "config": self._config
        }, indent=2))

    def compute_salience(self, activations: list[float], channel_id: int) -> AWQChannel:
        # Salience = average absolute activation magnitude (simplified)
        salience = sum(abs(a) for a in activations) / len(activations) if activations else 0.0
        channel = AWQChannel(channel_id=channel_id, salience_score=salience)
        self._channels.append(channel)
        self._save()
        return channel

    def apply_scaling(self, channel_id: int, scale_factor: float) -> None:
        for c in self._channels:
            if c.channel_id == channel_id:
                c.optimized_scale = c.original_scale * scale_factor
                c.protected = c.salience_score > 0.5  # Protect high-salience channels
                self._save()
                return

    def protect_salient(self, threshold: float = 0.5) -> list[int]:
        protected = []
        for c in self._channels:
            if c.salience_score > threshold:
                c.protected = True
                protected.append(c.channel_id)
        self._save()
        return protected

    def to_dict(self) -> dict:
        return {"config": self._config, "channel_count": len(self._channels), "protected": sum(1 for c in self._channels if c.protected)}

    def get_stats(self) -> dict:
        return {"channels": len(self._channels), "protected": sum(1 for c in self._channels if c.protected), "avg_salience": sum(c.salience_score for c in self._channels) / len(self._channels) if self._channels else 0.0}

__all__ = ["QuantizationAWQSimulator", "AWQChannel"]
