"""GRPO Trainer — Group Relative Policy Optimization for RL-based self-improvement.

Modul ini menyediakan:
- PolicyModel untuk generative policy dengan sampling
- RewardModel untuk scoring outputs
- GRPOTrainer untuk group-based RL training loop
- AdvantageCalculator untuk relative advantage computation
- ExperienceBuffer untuk storing rollouts

Berdasarkan: DeepSeek R1 training (FareedKhan-dev/train-deepseek-r1)
"""

from __future__ import annotations

import json
import time
import uuid
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum, auto


class RLStatus(Enum):
    IDLE = auto()
    SAMPLING = auto()
    SCORING = auto()
    COMPUTING_ADVANTAGE = auto()
    UPDATING_POLICY = auto()
    COMPLETED = auto()


@dataclass
class Rollout:
    """Single policy rollout with prompt, response, and reward."""
    rollout_id: str
    prompt: str
    response: str
    reward: float = 0.0
    group_id: str = ""
    token_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class GroupBatch:
    """Batch of rollouts for the same prompt (group)."""
    group_id: str
    prompt: str
    rollouts: List[Rollout] = field(default_factory=list)
    mean_reward: float = 0.0
    std_reward: float = 0.0

    def compute_stats(self) -> None:
        if not self.rollouts:
            return
        rewards = [r.reward for r in self.rollouts]
        self.mean_reward = sum(rewards) / len(rewards)
        if len(rewards) > 1:
            variance = sum((r - self.mean_reward) ** 2 for r in rewards) / len(rewards)
            self.std_reward = variance ** 0.5
        else:
            self.std_reward = 1.0

    def get_advantages(self) -> Dict[str, float]:
        """Compute relative advantages for each rollout."""
        if self.std_reward == 0:
            return {r.rollout_id: 0.0 for r in self.rollouts}
        return {r.rollout_id: (r.reward - self.mean_reward) / (self.std_reward + 1e-8) for r in self.rollouts}


class PolicyModel:
    """Generative policy that produces responses from prompts."""

    def __init__(self, temperature: float = 0.7, max_tokens: int = 512):
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._history: List[Dict[str, Any]] = []

    def generate(self, prompt: str, generator_fn: Optional[Callable[[str], str]] = None) -> str:
        generator_fn = generator_fn or self._default_generator
        response = generator_fn(prompt)
        self._history.append({"prompt": prompt[:100], "response": response[:100]})
        return response

    def _default_generator(self, prompt: str) -> str:
        # Simulated: template-based responses with randomness
        templates = [
            f"Based on '{prompt[:30]}', the answer is likely {{result}}.",
            f"Considering '{prompt[:30]}', I think {{result}}.",
            f"The solution to '{prompt[:30]}' would be {{result}}.",
            f"After analyzing '{prompt[:30]}', the conclusion is {{result}}.",
        ]
        # Deterministic seed from prompt
        seed = sum(ord(c) for c in prompt) % 1000
        random.seed(seed + int(time.time() * 1000) % 100)
        template = random.choice(templates)
        result = random.choice(["42", "positive", "negative", "A", "B", "correct", "valid"])
        return template.format(result=result)

    def sample_group(self, prompt: str, group_size: int = 4,
                     generator_fn: Optional[Callable[[str], str]] = None) -> List[Rollout]:
        rollouts = []
        for i in range(group_size):
            response = self.generate(prompt, generator_fn)
            rollouts.append(Rollout(
                rollout_id=f"r-{str(uuid.uuid4())[:8]}",
                prompt=prompt,
                response=response,
                token_count=max(1, len(response) // 4),
            ))
        return rollouts


class RewardModel:
    """Score generated responses based on rules or learned preferences."""

    def __init__(self):
        self._rules: List[Tuple[str, Callable[[str, str], float], float]] = []
        self._register_default_rules()

    def _register_default_rules(self):
        # Length reward: not too short, not too long
        self.add_rule("length", lambda p, r: 1.0 if 20 < len(r) < 500 else 0.5, weight=0.2)
        # Format reward: contains reasoning structure
        self.add_rule("reasoning", lambda p, r: 1.0 if any(k in r.lower() for k in ["because", "therefore", "since", "thus"]) else 0.3, weight=0.3)
        # Relevance reward: response contains prompt keywords
        self.add_rule("relevance", self._relevance_score, weight=0.3)
        # Correctness reward: contains expected answer patterns
        self.add_rule("correctness", lambda p, r: 1.0 if any(k in r.lower() for k in ["correct", "valid", "true", "answer is"]) else 0.5, weight=0.2)

    def _relevance_score(self, prompt: str, response: str) -> float:
        prompt_words = set(prompt.lower().split())
        response_words = set(response.lower().split())
        if not prompt_words:
            return 1.0
        overlap = len(prompt_words & response_words) / len(prompt_words)
        return min(1.0, overlap * 2)

    def add_rule(self, name: str, scorer: Callable[[str, str], float], weight: float = 1.0) -> None:
        self._rules.append((name, scorer, weight))

    def score(self, prompt: str, response: str) -> Tuple[float, Dict[str, float]]:
        total_weight = sum(w for _, _, w in self._rules)
        if total_weight == 0:
            return 0.0, {}
        scores = {}
        total = 0.0
        for name, scorer, weight in self._rules:
            s = scorer(prompt, response)
            scores[name] = round(s, 3)
            total += s * (weight / total_weight)
        return round(total, 3), scores

    def score_batch(self, rollouts: List[Rollout]) -> List[Rollout]:
        for r in rollouts:
            r.reward, r.metadata["reward_breakdown"] = self.score(r.prompt, r.response)
        return rollouts


class ExperienceBuffer:
    """Store and manage training rollouts."""

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._groups: Dict[str, GroupBatch] = {}
        self._all_rollouts: List[Rollout] = []

    def add_group(self, group: GroupBatch) -> None:
        self._groups[group.group_id] = group
        self._all_rollouts.extend(group.rollouts)
        if len(self._all_rollouts) > self.max_size:
            self._all_rollouts = self._all_rollouts[-self.max_size:]

    def sample_groups(self, n: int = 1) -> List[GroupBatch]:
        groups = list(self._groups.values())
        if len(groups) <= n:
            return groups
        return random.sample(groups, n)

    def get_best_rollouts(self, top_k: int = 10) -> List[Rollout]:
        sorted_rollouts = sorted(self._all_rollouts, key=lambda r: r.reward, reverse=True)
        return sorted_rollouts[:top_k]

    def get_stats(self) -> Dict[str, Any]:
        if not self._all_rollouts:
            return {}
        rewards = [r.reward for r in self._all_rollouts]
        return {
            "total_rollouts": len(self._all_rollouts),
            "total_groups": len(self._groups),
            "mean_reward": round(sum(rewards) / len(rewards), 3),
            "max_reward": round(max(rewards), 3),
            "min_reward": round(min(rewards), 3),
        }


class GRPOTrainer:
    """Group Relative Policy Optimization trainer."""

    def __init__(self, policy: PolicyModel, reward_model: RewardModel,
                 group_size: int = 4, learning_rate: float = 1e-5, epsilon: float = 0.2,
                 kl_penalty: float = 0.01):
        self.policy = policy
        self.reward_model = reward_model
        self.group_size = group_size
        self.lr = learning_rate
        self.epsilon = epsilon  # clipping parameter
        self.kl_penalty = kl_penalty
        self.buffer = ExperienceBuffer()
        self._status = RLStatus.IDLE
        self._step = 0
        self._history: List[Dict[str, Any]] = []

    def train_step(self, prompts: List[str]) -> Dict[str, Any]:
        self._status = RLStatus.SAMPLING
        groups = []
        for prompt in prompts:
            # Sample group
            rollouts = self.policy.sample_group(prompt, self.group_size)
            # Score
            self._status = RLStatus.SCORING
            rollouts = self.reward_model.score_batch(rollouts)
            # Group batch
            group = GroupBatch(
                group_id=str(uuid.uuid4())[:12],
                prompt=prompt,
                rollouts=rollouts,
            )
            group.compute_stats()
            groups.append(group)
            self.buffer.add_group(group)

        # Compute advantages and update (simulated)
        self._status = RLStatus.COMPUTING_ADVANTAGE
        total_advantage = 0.0
        total_rollouts = 0
        for group in groups:
            advantages = group.get_advantages()
            for rid, adv in advantages.items():
                total_advantage += adv
                total_rollouts += 1
                # Simulated: update policy parameters based on advantage
                # In real implementation: compute policy gradient with advantage
        mean_advantage = total_advantage / max(total_rollouts, 1)

        self._status = RLStatus.UPDATING_POLICY
        # Simulated policy update
        self._step += 1
        self.policy.temperature = max(0.1, self.policy.temperature * 0.995)

        self._status = RLStatus.COMPLETED
        step_record = {
            "step": self._step,
            "groups": len(groups),
            "rollouts": total_rollouts,
            "mean_advantage": round(mean_advantage, 4),
            "mean_reward": round(sum(g.mean_reward for g in groups) / len(groups), 4),
            "buffer_stats": self.buffer.get_stats(),
        }
        self._history.append(step_record)
        return step_record

    def train(self, prompts: List[str], num_steps: int = 10) -> List[Dict[str, Any]]:
        results = []
        for i in range(num_steps):
            result = self.train_step(prompts)
            results.append(result)
        return results

    def get_status(self) -> RLStatus:
        return self._status

    def get_history(self) -> List[Dict[str, Any]]:
        return self._history

    def export_model(self, path: str) -> None:
        """Export policy metadata."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "step": self._step,
                "temperature": self.policy.temperature,
                "history": self._history,
                "buffer_stats": self.buffer.get_stats(),
            }, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("GRPO TRAINER DEMO")
    print("=" * 70)

    # Setup
    policy = PolicyModel(temperature=1.0, max_tokens=256)
    reward_model = RewardModel()
    trainer = GRPOTrainer(policy, reward_model, group_size=4, learning_rate=1e-4)

    prompts = [
        "What is 2+2?",
        "Explain quantum computing in one sentence.",
        "Is the Earth flat?",
        "How does photosynthesis work?",
    ]

    # 1. Single training step
    print("\n[1] Training Step")
    result = trainer.train_step(prompts)
    print(f"  Step {result['step']}: {result['groups']} groups, {result['rollouts']} rollouts")
    print(f"  Mean advantage: {result['mean_advantage']:.4f}")
    print(f"  Mean reward: {result['mean_reward']:.4f}")

    # 2. Sample group details
    print("\n[2] Group Rollout Details")
    groups = trainer.buffer.sample_groups(1)
    if groups:
        group = groups[0]
        print(f"  Prompt: {group.prompt}")
        print(f"  Mean reward: {group.mean_reward:.3f}, Std: {group.std_reward:.3f}")
        advantages = group.get_advantages()
        for r in group.rollouts:
            print(f"    {r.rollout_id[:8]}: reward={r.reward:.3f}, advantage={advantages.get(r.rollout_id, 0):.3f}")
            print(f"      Response: {r.response[:60]}...")
            print(f"      Breakdown: {r.metadata.get('reward_breakdown', {})}")

    # 3. Full training
    print("\n[3] Full Training (5 steps)")
    results = trainer.train(prompts, num_steps=5)
    for r in results:
        print(f"  Step {r['step']}: mean_reward={r['mean_reward']:.3f}, advantage={r['mean_advantage']:.3f}")

    # 4. Best rollouts
    print("\n[4] Best Rollouts")
    best = trainer.buffer.get_best_rollouts(3)
    for r in best:
        print(f"  Reward={r.reward:.3f}: {r.response[:60]}...")

    # 5. Buffer stats
    print(f"\n[5] Buffer Stats")
    print(f"  {trainer.buffer.get_stats()}")

    # 6. Status
    print(f"\n[6] Trainer Status: {trainer.get_status().name}")
    print(f"  History: {len(trainer.get_history())} steps")
    print(f"  Policy temperature: {trainer.policy.temperature:.3f}")

    # 7. Export
    print("\n[7] Export Model")
    trainer.export_model("/tmp/grpo_model.json")
    print("  Exported to /tmp/grpo_model.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
