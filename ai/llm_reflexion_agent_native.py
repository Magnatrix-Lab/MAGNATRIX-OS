"""Reflexion Agent — Self-reflecting agent with trial-and-error learning and memory.

Modul ini menyediakan:
- ReflexionMemory untuk menyimpan success/failure patterns
- HeuristicEvaluator untuk mengevaluasi execution quality
- ReflexionAgent untuk agent yang belajar dari kesalahan sendiri
- TrialLoop untuk repeated trial-and-error dengan feedback
- SelfReflection untuk introspective analysis

Berdasarkan: Reflexion pattern dari all-agentic-architectures (FareedKhan-dev)
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class TrialStatus(Enum):
    PENDING = auto()
    SUCCESS = auto()
    FAILURE = auto()
    PARTIAL = auto()


@dataclass
class Trial:
    """Single attempt at a task."""
    trial_id: str
    task: str
    action: str
    result: str
    status: TrialStatus
    reflection: str = ""
    lessons: List[str] = field(default_factory=list)
    score: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class Heuristic:
    """Learned heuristic rule."""
    heuristic_id: str
    pattern: str
    condition: str
    advice: str
    success_count: int = 0
    failure_count: int = 0
    confidence: float = 0.5

    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / max(total, 1)


class ReflexionMemory:
    """Memory of past trials and learned heuristics."""

    def __init__(self, max_trials: int = 1000, max_heuristics: int = 500):
        self.max_trials = max_trials
        self.max_heuristics = max_heuristics
        self._trials: List[Trial] = []
        self._heuristics: Dict[str, Heuristic] = {}
        self._by_task: Dict[str, List[str]] = {}

    def add_trial(self, trial: Trial) -> None:
        self._trials.append(trial)
        self._by_task.setdefault(trial.task, []).append(trial.trial_id)
        if len(self._trials) > self.max_trials:
            self._trials = self._trials[-self.max_trials:]

    def add_heuristic(self, heuristic: Heuristic) -> None:
        self._heuristics[heuristic.heuristic_id] = heuristic
        if len(self._heuristics) > self.max_heuristics:
            # Remove lowest confidence
            worst = min(self._heuristics.values(), key=lambda h: h.confidence)
            del self._heuristics[worst.heuristic_id]

    def get_relevant_heuristics(self, task: str) -> List[Heuristic]:
        """Get heuristics relevant to a task."""
        relevant = []
        for h in self._heuristics.values():
            if h.pattern.lower() in task.lower() or task.lower() in h.pattern.lower():
                relevant.append(h)
        return sorted(relevant, key=lambda h: h.confidence * h.success_rate(), reverse=True)

    def get_task_history(self, task: str) -> List[Trial]:
        tids = self._by_task.get(task, [])
        return [t for t in self._trials if t.trial_id in tids]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._trials)
        successes = sum(1 for t in self._trials if t.status == TrialStatus.SUCCESS)
        failures = sum(1 for t in self._trials if t.status == TrialStatus.FAILURE)
        return {
            "total_trials": total,
            "successes": successes,
            "failures": failures,
            "success_rate": successes / max(total, 1),
            "heuristics": len(self._heuristics),
            "tasks": len(self._by_task),
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "stats": self.get_stats(),
                "heuristics": [{
                    "id": h.heuristic_id, "pattern": h.pattern,
                    "advice": h.advice, "success_rate": h.success_rate(),
                    "confidence": h.confidence,
                } for h in self._heuristics.values()],
            }, f, indent=2)


class HeuristicEvaluator:
    """Evaluate trial quality and extract heuristics."""

    def __init__(self):
        self._evaluators: List[Tuple[str, Callable[[str, str], float]]] = []

    def evaluate(self, task: str, result: str) -> Tuple[float, str, List[str]]:
        """Return (score, reflection, lessons)."""
        score = 0.5
        reflection = ""
        lessons = []

        # Check for completeness
        if len(result) > 50:
            score += 0.2
            lessons.append("Provide detailed responses")
        elif len(result) < 10:
            score -= 0.3
            lessons.append("Avoid overly short responses")

        # Check for correctness indicators
        if any(k in result.lower() for k in ["correct", "success", "completed", "done"]):
            score += 0.2
        if any(k in result.lower() for k in ["error", "fail", "cannot", "unable", "sorry"]):
            score -= 0.3
            reflection += "The response indicates failure or inability. "
            lessons.append("Avoid failure indicators; try alternative approaches")

        # Check for reasoning
        if any(k in result.lower() for k in ["because", "therefore", "reason", "step"]):
            score += 0.1
            lessons.append("Include reasoning in responses")

        # Check task alignment
        task_keywords = set(task.lower().split())
        result_keywords = set(result.lower().split())
        overlap = len(task_keywords & result_keywords) / max(len(task_keywords), 1)
        if overlap > 0.3:
            score += 0.2
        else:
            score -= 0.1
            reflection += "Response may not directly address the task. "
            lessons.append("Directly address the specific task keywords")

        score = max(0.0, min(1.0, score))
        return score, reflection or "No major issues detected", lessons

    def extract_heuristic(self, task: str, trial: Trial) -> Optional[Heuristic]:
        if not trial.lessons:
            return None
        # Create heuristic from lessons
        pattern = task[:50]
        advice = trial.lessons[0] if trial.lessons else "General improvement"
        return Heuristic(
            heuristic_id=str(uuid.uuid4())[:12],
            pattern=pattern,
            condition=f"task contains '{pattern}'",
            advice=advice,
            success_count=1 if trial.status == TrialStatus.SUCCESS else 0,
            failure_count=1 if trial.status == TrialStatus.FAILURE else 0,
            confidence=0.5,
        )


class ReflexionAgent:
    """Agent that learns from self-reflection."""

    def __init__(self, max_trials_per_task: int = 3):
        self.max_trials = max_trials_per_task
        self.memory = ReflexionMemory()
        self.evaluator = HeuristicEvaluator()
        self._execution_count = 0

    def execute(self, task: str, action_fn: Optional[Callable[[str, List[Heuristic]], str]] = None) -> Tuple[str, List[Trial]]:
        action_fn = action_fn or self._default_execute
        trials = []
        best_result = ""
        best_score = -1.0

        for i in range(self.max_trials):
            # Get relevant heuristics
            heuristics = self.memory.get_relevant_heuristics(task)

            # Execute with heuristics
            result = action_fn(task, heuristics)

            # Evaluate
            score, reflection, lessons = self.evaluator.evaluate(task, result)

            # Determine status
            if score >= 0.7:
                status = TrialStatus.SUCCESS
            elif score >= 0.4:
                status = TrialStatus.PARTIAL
            else:
                status = TrialStatus.FAILURE

            trial = Trial(
                trial_id=str(uuid.uuid4())[:12],
                task=task,
                action=result[:100],
                result=result,
                status=status,
                reflection=reflection,
                lessons=lessons,
                score=score,
            )
            trials.append(trial)
            self.memory.add_trial(trial)

            # Extract heuristic
            heuristic = self.evaluator.extract_heuristic(task, trial)
            if heuristic:
                self.memory.add_heuristic(heuristic)

            if score > best_score:
                best_score = score
                best_result = result

            if status == TrialStatus.SUCCESS:
                break

        self._execution_count += 1
        return best_result, trials

    def _default_execute(self, task: str, heuristics: List[Heuristic]) -> str:
        # Apply heuristics as advice
        advice = ""
        for h in heuristics[:3]:
            advice += f"[{h.advice}] "

        # Simulated execution with advice influence
        base = f"Result for task: {task[:40]}"
        if "detailed" in advice.lower():
            base += ". Detailed explanation: This is a comprehensive response with step-by-step reasoning."
        if "reasoning" in advice.lower():
            base += " Because the task requires careful analysis, we proceed systematically."
        if "failure" in advice.lower():
            base = f"Successfully completed: {task[:40]}. Correct answer provided."
        return base

    def get_stats(self) -> Dict[str, Any]:
        return {
            "executions": self._execution_count,
            **self.memory.get_stats(),
        }

    def export_memory(self, path: str) -> None:
        self.memory.export(path)


class TrialLoop:
    """Repeated trial-and-error loop with feedback."""

    def __init__(self, agent: ReflexionAgent, success_threshold: float = 0.7):
        self.agent = agent
        self.success_threshold = success_threshold
        self._runs: List[Dict[str, Any]] = []

    def run(self, task: str, action_fn: Optional[Callable[[str, List[Heuristic]], str]] = None) -> Dict[str, Any]:
        result, trials = self.agent.execute(task, action_fn)
        success = any(t.status == TrialStatus.SUCCESS for t in trials)
        run_record = {
            "run_id": str(uuid.uuid4())[:12],
            "task": task,
            "success": success,
            "trials": len(trials),
            "best_score": max(t.score for t in trials) if trials else 0.0,
            "final_result": result[:100],
            "heuristics_used": len(self.agent.memory.get_relevant_heuristics(task)),
        }
        self._runs.append(run_record)
        return run_record

    def run_batch(self, tasks: List[str]) -> List[Dict[str, Any]]:
        return [self.run(task) for task in tasks]

    def get_summary(self) -> Dict[str, Any]:
        if not self._runs:
            return {}
        total = len(self._runs)
        successes = sum(1 for r in self._runs if r["success"])
        return {
            "total_runs": total,
            "successes": successes,
            "success_rate": successes / total,
            "avg_trials": sum(r["trials"] for r in self._runs) / total,
            "avg_best_score": sum(r["best_score"] for r in self._runs) / total,
        }


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("REFLEXION AGENT DEMO")
    print("=" * 70)

    # 1. Basic execution
    print("\n[1] Basic Execution with Reflexion")
    agent = ReflexionAgent(max_trials_per_task=3)
    result, trials = agent.execute("Calculate the square root of 144")
    print(f"  Task: Calculate the square root of 144")
    print(f"  Trials: {len(trials)}")
    for t in trials:
        print(f"    Trial {t.trial_id[:8]}: {t.status.name} (score={t.score:.2f})")
        print(f"      Reflection: {t.reflection}")
        print(f"      Lessons: {t.lessons}")
    print(f"  Final result: {result[:80]}...")

    # 2. Multiple tasks with learning
    print("\n[2] Batch Tasks with Learning")
    loop = TrialLoop(agent)
    tasks = [
        "Sort these numbers: 5, 2, 8, 1, 9",
        "Find the maximum of [3, 7, 2, 9, 4]",
        "Calculate average of [10, 20, 30]",
        "Reverse the string 'hello'",
    ]
    for task in tasks:
        run = loop.run(task)
        print(f"  {task[:40]}... -> success={run['success']}, trials={run['trials']}, score={run['best_score']:.2f}")

    # 3. Re-execute with learned heuristics
    print("\n[3] Re-execute with Learned Heuristics")
    result2, trials2 = agent.execute("Calculate the square root of 144")
    print(f"  Second attempt: {len(trials2)} trials (was {len(trials)} before)")
    for t in trials2:
        print(f"    Trial: {t.status.name} (score={t.score:.2f})")

    # 4. Heuristics inventory
    print(f"\n[4] Learned Heuristics ({len(agent.memory._heuristics)})")
    for h in sorted(agent.memory._heuristics.values(), key=lambda h: h.confidence, reverse=True)[:5]:
        print(f"  {h.heuristic_id[:8]}: '{h.pattern[:30]}...' -> {h.advice[:50]}... (SR={h.success_rate():.2f})")

    # 5. Memory stats
    print(f"\n[5] Memory Stats")
    print(f"  {agent.get_stats()}")

    # 6. Trial loop summary
    print(f"\n[6] Trial Loop Summary")
    print(f"  {loop.get_summary()}")

    # 7. Export
    print("\n[7] Export Memory")
    agent.export_memory("/tmp/reflexion_memory.json")
    print("  Exported to /tmp/reflexion_memory.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
