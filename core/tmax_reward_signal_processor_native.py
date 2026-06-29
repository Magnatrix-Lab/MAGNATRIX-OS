"""TMax Reward Signal Processor -- Reward shaping, normalization, feedback aggregation."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class RewardSignal:
    signal_id: str = ""
    trace_id: str = ""
    step_id: str = ""
    raw_reward: float = 0.0
    shaped_reward: float = 0.0
    reward_type: str = ""  # sparse | dense | bonus | penalty
    source: str = ""  # automatic | human | model
    confidence: float = 1.0

class TmaxRewardSignalProcessor:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._signals: list[RewardSignal] = []
        self._shaping_rules: list[dict] = []
        self._persist_path = self.root / "tmax_rewards.json"
        self._load()
        if not self._shaping_rules:
            self._seed_rules()

    def _seed_rules(self) -> None:
        self._shaping_rules = [
            {"name": "efficiency_bonus", "condition": "steps < 5", "bonus": 0.2},
            {"name": "correctness_bonus", "condition": "output_match > 0.9", "bonus": 0.3},
            {"name": "timeout_penalty", "condition": "steps > max_steps", "penalty": -0.5},
            {"name": "error_penalty", "condition": "error in output", "penalty": -0.3},
        ]

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._signals = [RewardSignal(**s) for s in data.get("signals", [])]
            self._shaping_rules = data.get("rules", [])

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "signals": [s.__dict__ for s in self._signals],
            "rules": self._shaping_rules
        }, indent=2))

    def add_signal(self, signal_id: str, trace_id: str, step_id: str, raw_reward: float, reward_type: str = "dense", source: str = "automatic", confidence: float = 1.0) -> RewardSignal:
        shaped = self._shape(raw_reward, reward_type)
        signal = RewardSignal(
            signal_id=signal_id, trace_id=trace_id, step_id=step_id,
            raw_reward=raw_reward, shaped_reward=shaped, reward_type=reward_type,
            source=source, confidence=confidence
        )
        self._signals.append(signal)
        self._save()
        return signal

    def _shape(self, raw: float, reward_type: str) -> float:
        if reward_type == "sparse":
            return raw  # No shaping
        elif reward_type == "dense":
            return raw * 0.5  # Scale down dense rewards
        elif reward_type == "bonus":
            return min(1.0, raw + 0.1)  # Small bonus
        elif reward_type == "penalty":
            return max(-1.0, raw - 0.2)  # Penalty
        return raw

    def normalize(self, signals: list[RewardSignal]) -> list[float]:
        if not signals:
            return []
        values = [s.shaped_reward for s in signals]
        min_v = min(values)
        max_v = max(values)
        if max_v == min_v:
            return [0.5] * len(signals)
        return [(v - min_v) / (max_v - min_v) for v in values]

    def aggregate(self, trace_id: str) -> dict:
        trace_signals = [s for s in self._signals if s.trace_id == trace_id]
        if not trace_signals:
            return {"total": 0, "avg": 0, "count": 0}
        total = sum(s.shaped_reward * s.confidence for s in trace_signals)
        avg = total / len(trace_signals)
        return {"total": round(total, 3), "avg": round(avg, 3), "count": len(trace_signals)}

    def add_rule(self, name: str, condition: str, bonus: float = 0.0, penalty: float = 0.0) -> None:
        self._shaping_rules.append({"name": name, "condition": condition, "bonus": bonus, "penalty": penalty})
        self._save()

    def list_rules(self) -> list[dict]:
        return self._shaping_rules

    def get_by_trace(self, trace_id: str) -> list[RewardSignal]:
        return [s for s in self._signals if s.trace_id == trace_id]

    def to_dict(self) -> dict:
        return {"signal_count": len(self._signals), "rules": len(self._shaping_rules)}

    def get_stats(self) -> dict:
        by_type = {}
        by_source = {}
        for s in self._signals:
            by_type[s.reward_type] = by_type.get(s.reward_type, 0) + 1
            by_source[s.source] = by_source.get(s.source, 0) + 1
        avg_raw = sum(s.raw_reward for s in self._signals) / len(self._signals) if self._signals else 0
        avg_shaped = sum(s.shaped_reward for s in self._signals) / len(self._signals) if self._signals else 0
        return {"signals": len(self._signals), "by_type": by_type, "by_source": by_source, "avg_raw": round(avg_raw, 3), "avg_shaped": round(avg_shaped, 3)}

__all__ = ["TmaxRewardSignalProcessor", "RewardSignal"]
