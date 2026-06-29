
"""
adaptive_harness_native.py
MAGNATRIX-OS — Adaptive Auto-Harness

Inspired by A-Evolve Adaptive Auto-Harness (arXiv 2606.01770):
Sustained self-improvement for agentic system deployment on
open-ended, shifting task streams.

Pure Python standard library.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto


class TaskType(Enum):
    FIXED = auto()
    OPEN_ENDED = auto()
    SHIFTING = auto()
    ADAPTIVE = auto()


@dataclass
class TaskStream:
    name: str
    tasks: List[Dict] = field(default_factory=list)
    task_type: TaskType = TaskType.FIXED
    shift_interval: int = 10
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HarnessUpdate:
    update_id: str
    timestamp: str
    trigger_reason: str
    changes: List[str] = field(default_factory=list)
    performance_delta: float = 0.0
    harness_benefit: float = 0.0


class AdaptiveHarness:
    """Adaptive auto-harness for open-ended task streams."""

    def __init__(self, output_dir: str = "./harness"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.harnesses: Dict[str, Dict] = {}
        self.update_history: List[HarnessUpdate] = []
        self.task_streams: Dict[str, TaskStream] = {}
        self.performance_window: Dict[str, List[float]] = {}
        self._adaptation_rules: List[Callable] = []

    def register_task_stream(self, stream: TaskStream) -> None:
        self.task_streams[stream.name] = stream
        self.performance_window[stream.name] = []

    def deploy_harness(self, stream_name: str, harness_config: Dict) -> None:
        self.harnesses[stream_name] = {
            "config": harness_config,
            "deployed_at": datetime.now().isoformat(),
            "updates": 0,
        }

    def evaluate(self, stream_name: str, agent_result: Dict) -> float:
        """Evaluate agent performance on a task stream."""
        score = agent_result.get("score", 0.0)
        self.performance_window[stream_name].append(score)
        # Keep only last 20 scores
        if len(self.performance_window[stream_name]) > 20:
            self.performance_window[stream_name] = self.performance_window[stream_name][-20:]
        return score

    def check_adaptation_needed(self, stream_name: str) -> bool:
        """Detect if harness needs updating due to performance drift."""
        scores = self.performance_window.get(stream_name, [])
        if len(scores) < 5:
            return False
        recent = scores[-5:]
        older = scores[-10:-5] if len(scores) >= 10 else scores[:5]
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)
        # Declining performance or high variance
        declining = recent_avg < older_avg * 0.95
        high_variance = max(recent) - min(recent) > 0.3
        return declining or high_variance

    def adapt_harness(self, stream_name: str) -> HarnessUpdate:
        """Generate harness update for a shifting task stream."""
        harness = self.harnesses.get(stream_name, {})
        old_config = harness.get("config", {})
        # Generate adaptive changes
        changes = []
        if old_config.get("strict", False):
            changes.append("loosened_constraints")
        if not old_config.get("feedback_loop", True):
            changes.append("enabled_feedback_loop")
        if old_config.get("max_retries", 3) < 5:
            changes.append("increased_retries")
        # Simulated update
        new_config = {**old_config, "adapted": True, "version": old_config.get("version", 0) + 1}
        harness["config"] = new_config
        harness["updates"] += 1
        update = HarnessUpdate(
            update_id=f"{stream_name}_v{new_config['version']}_{int(time.time())}",
            timestamp=datetime.now().isoformat(),
            trigger_reason="performance_drift" if self.check_adaptation_needed(stream_name) else "scheduled",
            changes=changes,
            performance_delta=0.05,
            harness_benefit=0.03,
        )
        self.update_history.append(update)
        return update

    def sustained_improvement(self, stream_name: str, agent: Any, cycles: int = 10) -> List[HarnessUpdate]:
        """Run sustained self-improvement loop on a task stream."""
        updates = []
        for cycle in range(cycles):
            stream = self.task_streams.get(stream_name)
            if not stream:
                break
            # Simulate task execution
            for task in stream.tasks:
                result = {"score": 0.5 + (cycle * 0.05)}  # Simulated improvement
                self.evaluate(stream_name, result)
            if self.check_adaptation_needed(stream_name):
                update = self.adapt_harness(stream_name)
                updates.append(update)
        return updates

    def disentangle_capability(self, harness_update: HarnessUpdate, agent_baseline: float, agent_evolved: float) -> Dict:
        """
        Disentangle evolution capabilities (arXiv 2605.30621):
        Which model produced the best harness update and which benefits most.
        """
        harness_benefit = harness_update.harness_benefit
        raw_evolution = agent_evolved - agent_baseline
        harness_contribution = min(harness_benefit, raw_evolution * 0.5)
        intrinsic_evolution = raw_evolution - harness_contribution
        return {
            "harness_update_benefit": harness_benefit,
            "raw_evolution_gain": raw_evolution,
            "harness_contribution": harness_contribution,
            "intrinsic_evolution": intrinsic_evolution,
            "conclusion": "harness" if harness_contribution > intrinsic_evolution else "intrinsic",
        }

    def get_update_history(self) -> List[Dict]:
        return [{"update_id": u.update_id, "timestamp": u.timestamp,
                 "trigger": u.trigger_reason, "changes": u.changes,
                 "delta": u.performance_delta} for u in self.update_history]

    def to_dict(self) -> Dict:
        return {
            "streams": list(self.task_streams.keys()),
            "harnesses": list(self.harnesses.keys()),
            "total_updates": len(self.update_history),
            "latest_update": self.update_history[-1].update_id if self.update_history else None,
        }


__all__ = ["AdaptiveHarness", "TaskStream", "HarnessUpdate", "TaskType"]
