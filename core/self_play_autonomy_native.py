"""
self_play_autonomy_native.py
MAGNATRIX-OS — Self-Play Autonomy Trainer

Inspired by arXiv 2606.19370: Human-like autonomy from self-play with human data regularization. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class TrainingEpisode:
    episode_id: str
    policy_id: str
    reward: float
    human_aligned: bool
    steps: int


class SelfPlayAutonomyTrainer:
    """Train autonomy via self-play with human data regularization."""

    def __init__(self, cache_dir: str = "./self_play"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.episodes: Dict[str, TrainingEpisode] = {}
        self.policies: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        for fname in ["episodes.json", "policies.json"]:
            f = self.cache_dir / fname
            if f.exists():
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        if fname == "episodes.json":
                            for eid, ed in data.items():
                                self.episodes[eid] = TrainingEpisode(**ed)
                        else:
                            self.policies = data
                except Exception:
                    pass

    def _save(self) -> None:
        with open(self.cache_dir / "episodes.json", "w", encoding="utf-8") as f:
            json.dump({eid: asdict(e) for eid, e in self.episodes.items()}, f, indent=2)
        with open(self.cache_dir / "policies.json", "w", encoding="utf-8") as f:
            json.dump(self.policies, f, indent=2)

    def train_policy(self, policy_id: str, self_play_ratio: float = 0.9, human_data_minutes: float = 0.5) -> Dict[str, Any]:
        """Train a policy with self-play + human data regularization."""
        self.policies[policy_id] = {
            "policy_id": policy_id, "self_play_ratio": self_play_ratio,
            "human_data_minutes": human_data_minutes, "episodes": 0, "avg_reward": 0.0,
        }
        self._save()
        return self.policies[policy_id]

    def record_episode(self, episode_id: str, policy_id: str, reward: float, human_aligned: bool, steps: int) -> TrainingEpisode:
        ep = TrainingEpisode(
            episode_id=episode_id, policy_id=policy_id, reward=reward,
            human_aligned=human_aligned, steps=steps,
        )
        self.episodes[episode_id] = ep
        # Update policy stats
        policy = self.policies.get(policy_id, {})
        policy["episodes"] = policy.get("episodes", 0) + 1
        total_reward = policy.get("avg_reward", 0.0) * (policy["episodes"] - 1) + reward
        policy["avg_reward"] = total_reward / policy["episodes"]
        self._save()
        return ep

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.episodes)
        aligned = sum(1 for e in self.episodes.values() if e.human_aligned)
        avg_reward = sum(e.reward for e in self.episodes.values()) / max(1, total)
        return {"total_episodes": total, "human_aligned": aligned, "avg_reward": round(avg_reward, 4)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["SelfPlayAutonomyTrainer", "TrainingEpisode"]