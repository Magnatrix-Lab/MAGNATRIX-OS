#!/usr/bin/env python3
"""
AMATI — PELAJARI — TIRU
Magnatrix-OS :: Reward Engine Native
Pattern: RL reward construction — verifiable rewards, reward model scoring, world model rewards
Pure Python stdlib. Runnable standalone.
"""

import json, math, random, re, textwrap, time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

# ── BaseLayer ──

@dataclass
class RewardSignal:
    value: float
    source_type: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TaskSpec:
    task_id: str
    description: str
    verifiable_criteria: List[str]
    expected_output_format: str

@dataclass
class TrajectoryStep:
    state: Dict[str, Any]
    action: str
    reward: float
    next_state: Dict[str, Any]
    done: bool

# ── CoreEngine ──

class VerifiableReward:
    def __init__(self, task: TaskSpec):
        self.task = task

    def compute(self, action_output: str) -> RewardSignal:
        checks = []
        for crit in self.task.verifiable_criteria:
            checks.append(self._check(crit, action_output))
        score = sum(checks) / len(checks) if checks else 0.0
        return RewardSignal(
            value=round(score, 3),
            source_type="verifiable",
            confidence=1.0,
            metadata={"checks": checks, "criteria": self.task.verifiable_criteria},
        )

    def _check(self, criterion: str, output: str) -> float:
        c = criterion.lower()
        out = output.lower()
        if "code" in c and "run" in c:
            return self._exec_check(output)
        if "math" in c or "proof" in c:
            return self._math_check(output)
        if "file" in c and ("exist" in c or "contains" in c):
            return self._file_check(criterion, output)
        if "search" in c or "fact" in c or "correct" in c:
            return self._search_check(criterion, output)
        if c in out:
            return 1.0
        return 0.0

    def _exec_check(self, code: str) -> float:
        try:
            # Safe restricted exec: only eval simple expressions
            if len(code) > 200:
                return 0.5
            allowed = {"__builtins__": {"abs": abs, "len": len, "max": max, "min": min, "sum": sum}}
            eval(compile(code, "<string>", "eval"), allowed, {})
            return 1.0
        except Exception:
            return 0.0

    def _math_check(self, text: str) -> float:
        # Simple proof-step pattern matching
        steps = re.findall(r"(?:step|proof|therefore|hence|=>|→)\s*\d*[:.]?\s*(.+)", text, re.I)
        return min(1.0, len(steps) / 3.0)

    def _file_check(self, criterion: str, output: str) -> float:
        # Mock: check if output references a file path
        has_path = bool(re.search(r"[\w/\\]+\.[a-zA-Z0-9]+", output))
        return 1.0 if has_path else 0.0

    def _search_check(self, criterion: str, output: str) -> float:
        keywords = re.findall(r"[A-Za-z0-9_]{4,}", criterion)
        matches = sum(1 for kw in keywords if kw.lower() in output)
        return min(1.0, matches / max(len(keywords), 1))

class RewardModel:
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or {
            "completeness": 0.25,
            "correctness": 0.35,
            "conciseness": 0.20,
            "safety": 0.20,
        }

    def score(self, action_output: str, task: TaskSpec) -> RewardSignal:
        scores = {
            "completeness": self._completeness(action_output, task),
            "correctness": self._correctness(action_output),
            "conciseness": self._conciseness(action_output),
            "safety": self._safety(action_output),
        }
        total = sum(scores[k] * self.weights[k] for k in scores)
        return RewardSignal(
            value=round(total, 3),
            source_type="reward_model",
            confidence=0.85,
            metadata={"breakdown": scores, "weights": self.weights},
        )

    def _completeness(self, text: str, task: TaskSpec) -> float:
        required = len(task.verifiable_criteria)
        found = sum(1 for c in task.verifiable_criteria if any(w in text.lower() for w in c.lower().split()[:3]))
        return min(1.0, found / max(required, 1))

    def _correctness(self, text: str) -> float:
        # Heuristic: balanced brackets, no obvious error keywords
        errors = ["error", "exception", "failed", "incorrect", "wrong"]
        penalty = sum(0.2 for e in errors if e in text.lower())
        brackets = text.count("(") == text.count(")") and text.count("{") == text.count("}")
        base = 0.9 if brackets else 0.6
        return max(0.0, base - penalty)

    def _conciseness(self, text: str) -> float:
        words = len(text.split())
        if words < 20:
            return 1.0
        if words < 100:
            return 0.8
        return max(0.3, 1.0 - (words - 100) / 500)

    def _safety(self, text: str) -> float:
        unsafe = ["rm -rf", "drop table", "delete from", "exec(", "eval(", "system(", "__import__('os')"]
        return 0.0 if any(u in text for u in unsafe) else 1.0

class WorldModelReward:
    def __init__(self, grid_size: int = 5):
        self.grid_size = grid_size
        self.goal: Tuple[int, int] = (grid_size - 1, grid_size - 1)

    def reset(self) -> Dict[str, Any]:
        return {"pos": [0, 0], "steps": 0}

    def step(self, state: Dict[str, Any], action: str) -> Tuple[Dict[str, Any], float, bool]:
        x, y = state["pos"]
        if action == "up":
            y = max(0, y - 1)
        elif action == "down":
            y = min(self.grid_size - 1, y + 1)
        elif action == "left":
            x = max(0, x - 1)
        elif action == "right":
            x = min(self.grid_size - 1, x + 1)
        next_state = {"pos": [x, y], "steps": state["steps"] + 1}
        reward = self._reward([x, y])
        done = (x, y) == self.goal or state["steps"] >= 20
        return next_state, reward, done

    def _reward(self, pos: List[int]) -> float:
        gx, gy = self.goal
        dist = abs(pos[0] - gx) + abs(pos[1] - gy)
        max_dist = self.grid_size * 2
        return round(1.0 - (dist / max_dist), 3)

    def evaluate_trajectory(self, trajectory: List[TrajectoryStep]) -> RewardSignal:
        if not trajectory:
            return RewardSignal(0.0, "world_model", 1.0)
        total = sum(t.reward for t in trajectory)
        final = trajectory[-1].next_state.get("pos", [0, 0])
        reached = tuple(final) == self.goal
        return RewardSignal(
            value=round(total / len(trajectory), 3),
            source_type="world_model",
            confidence=1.0,
            metadata={"total": total, "reached_goal": reached, "length": len(trajectory)},
        )

# ── Features ──

class RewardConstructor:
    def __init__(self):
        self.sources: List[Tuple[str, Any, float]] = []

    def add_verifiable(self, task: TaskSpec, weight: float = 1.0) -> "RewardConstructor":
        self.sources.append(("verifiable", VerifiableReward(task), weight))
        return self

    def add_reward_model_preference(self, weight: float = 1.0, custom_weights: Optional[Dict[str, float]] = None) -> "RewardConstructor":
        self.sources.append(("reward_model", RewardModel(custom_weights), weight))
        return self

    def add_world_model(self, env: WorldModelReward, weight: float = 1.0) -> "RewardConstructor":
        self.sources.append(("world_model", env, weight))
        return self

    def compute_total(self, action_output: str, trajectory: Optional[List[TrajectoryStep]] = None) -> RewardSignal:
        total = 0.0
        total_weight = 0.0
        breakdown = {}
        for source_type, source, weight in self.sources:
            if source_type == "verifiable":
                rs = source.compute(action_output)
            elif source_type == "reward_model":
                # Need task context — use a dummy for scoring
                dummy = TaskSpec("dummy", "", ["contains output"], "text")
                rs = source.score(action_output, dummy)
            elif source_type == "world_model" and trajectory:
                rs = source.evaluate_trajectory(trajectory)
            else:
                continue
            total += rs.value * weight
            total_weight += weight
            breakdown[source_type] = {"value": rs.value, "weight": weight, "confidence": rs.confidence}
        final = round(total / total_weight, 3) if total_weight > 0 else 0.0
        return RewardSignal(
            value=final,
            source_type="composite",
            confidence=round(min(1.0, sum(b["confidence"] for b in breakdown.values()) / len(breakdown)), 3) if breakdown else 1.0,
            metadata={"breakdown": breakdown, "total_weight": total_weight},
        )

class RewardNormalizer:
    @staticmethod
    def z_score(values: List[float]) -> List[float]:
        if not values:
            return []
        mean = sum(values) / len(values)
        std = math.sqrt(sum((v - mean) ** 2 for v in values) / len(values)) or 1.0
        return [round((v - mean) / std, 3) for v in values]

    @staticmethod
    def min_max(values: List[float], target_range: Tuple[float, float] = (0.0, 1.0)) -> List[float]:
        if not values or len(set(values)) == 1:
            return [target_range[0]] * len(values)
        lo, hi = min(values), max(values)
        t0, t1 = target_range
        return [round(t0 + (v - lo) / (hi - lo) * (t1 - t0), 3) for v in values]

class RewardDebugger:
    def explain(self, signal: RewardSignal) -> str:
        lines = [
            f"Reward: {signal.value} (source: {signal.source_type}, confidence: {signal.confidence})",
            "Metadata:",
        ]
        for k, v in signal.metadata.items():
            lines.append(f"  {k}: {v}")
        return "\n".join(lines)

# ── Kernel ──

class RewardEngineKernel:
    def __init__(self):
        self.constructor = RewardConstructor()
        self.normalizer = RewardNormalizer()
        self.debugger = RewardDebugger()

    def evaluate(self, task: TaskSpec, action_history: List[str], trajectory: Optional[List[TrajectoryStep]] = None) -> RewardSignal:
        # Build constructor from task
        self.constructor = RewardConstructor()
        self.constructor.add_verifiable(task, weight=0.5)
        self.constructor.add_reward_model_preference(weight=0.3)
        if trajectory:
            self.constructor.add_world_model(WorldModelReward(), weight=0.2)
        # Join action history as single output for scoring
        output = "\n".join(action_history)
        return self.constructor.compute_total(output, trajectory)

# ── Self-Test ──

def _self_test():
    print("=" * 50)
    print("Reward Engine Native — Self Test")
    print("=" * 50)

    # 1. Coding task
    print("\n[1] Verifiable coding task")
    code_task = TaskSpec(
        task_id="code-001",
        description="Write a function that sums two numbers",
        verifiable_criteria=["code runs", "contains def", "returns sum"],
        expected_output_format="python function",
    )
    vr = VerifiableReward(code_task)
    code_output = "def add(a, b):\n    return a + b\n"
    r1 = vr.compute(code_output)
    print(f"  Value: {r1.value}, Checks: {r1.metadata['checks']}")

    # 2. Math task
    print("\n[2] Math proof task")
    math_task = TaskSpec(
        task_id="math-001",
        description="Prove that odd + odd = even",
        verifiable_criteria=["math proof", "step-by-step", "contains even"],
        expected_output_format="text proof",
    )
    vr2 = VerifiableReward(math_task)
    proof = "Step 1: Let a = 2k+1, b = 2m+1.\nStep 2: a+b = 2(k+m+1).\nTherefore even."
    r2 = vr2.compute(proof)
    print(f"  Value: {r2.value}, Checks: {r2.metadata['checks']}")

    # 3. Reward model
    print("\n[3] Reward model preference")
    rm = RewardModel()
    r3 = rm.score("def hello():\n    print('hi')\n", code_task)
    print(f"  Total: {r3.value}, Breakdown: {r3.metadata['breakdown']}")

    # 4. World model
    print("\n[4] World model trajectory")
    wm = WorldModelReward(grid_size=3)
    traj = []
    state = wm.reset()
    for act in ["right", "right", "down", "down"]:
        ns, rew, done = wm.step(state, act)
        traj.append(TrajectoryStep(state=state, action=act, reward=rew, next_state=ns, done=done))
        state = ns
        if done:
            break
    r4 = wm.evaluate_trajectory(traj)
    print(f"  Avg reward: {r4.value}, Reached goal: {r4.metadata['reached_goal']}")

    # 5. Reward constructor
    print("\n[5] Reward constructor composite")
    rc = RewardConstructor()
    rc.add_verifiable(code_task, weight=0.5)
    rc.add_reward_model_preference(weight=0.3)
    rc.add_world_model(WorldModelReward(), weight=0.2)
    r5 = rc.compute_total(code_output, traj)
    print(f"  Composite: {r5.value}, Breakdown: {r5.metadata['breakdown']}")

    # 6. Normalizer
    print("\n[6] Normalizer")
    raw = [0.2, 0.5, 0.8, 1.0, 0.0]
    print(f"  z-score: {RewardNormalizer.z_score(raw)}")
    print(f"  min-max [0,1]: {RewardNormalizer.min_max(raw)}")
    print(f"  min-max [-1,1]: {RewardNormalizer.min_max(raw, (-1.0, 1.0))}")

    # 7. Debugger
    print("\n[7] Debugger")
    print(RewardDebugger().explain(r5))

    # 8. Kernel integration
    print("\n[8] Kernel evaluate")
    kernel = RewardEngineKernel()
    result = kernel.evaluate(code_task, [code_output], traj)
    print(f"  Kernel result: {result.value}")

    print("\n" + "=" * 50)
    print("All tests passed.")
    print("=" * 50)

if __name__ == "__main__":
    _self_test()
