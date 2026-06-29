"""TMax Agent Rollout Simulator -- Simulate terminal agent execution traces."""
from dataclasses import dataclass
from pathlib import Path
import json, random

@dataclass
class RolloutStep:
    step_id: str = ""
    command: str = ""
    observation: str = ""
    reward: float = 0.0
    done: bool = False
    timestamp: float = 0.0

@dataclass
class RolloutTrace:
    trace_id: str = ""
    task_id: str = ""
    agent_id: str = ""
    steps: list[RolloutStep] = None
    total_reward: float = 0.0
    success: bool = False
    length: int = 0

    def __post_init__(self):
        if self.steps is None:
            self.steps = []

class TmaxAgentRolloutSimulator:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._traces: list[RolloutTrace] = []
        self._persist_path = self.root / "tmax_rollouts.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._traces = []
            for t in data.get("traces", []):
                trace = RolloutTrace(trace_id=t["trace_id"], task_id=t["task_id"], agent_id=t["agent_id"], total_reward=t["total_reward"], success=t["success"], length=t["length"])
                trace.steps = [RolloutStep(**s) for s in t.get("steps", [])]
                self._traces.append(trace)

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "traces": [{
                "trace_id": t.trace_id, "task_id": t.task_id, "agent_id": t.agent_id,
                "total_reward": t.total_reward, "success": t.success, "length": t.length,
                "steps": [s.__dict__ for s in t.steps]
            } for t in self._traces]
        }, indent=2))

    def simulate(self, trace_id: str, task_id: str, agent_id: str, max_steps: int = 10) -> RolloutTrace:
        import time
        trace = RolloutTrace(trace_id=trace_id, task_id=task_id, agent_id=agent_id)
        commands = ["ls", "pwd", "cat file.txt", "grep pattern file", "cd src", "python script.py", "git status", "echo done"]
        observations = ["file1.txt file2.py", "/home/user", "content...", "match found", "", "Running...", "clean", "done"]

        for i in range(max_steps):
            cmd = random.choice(commands)
            obs = random.choice(observations)
            reward = 0.1 if i < max_steps - 1 else 1.0
            done = i == max_steps - 1 or random.random() < 0.1
            step = RolloutStep(
                step_id=f"{trace_id}_step_{i}", command=cmd, observation=obs,
                reward=reward, done=done, timestamp=time.time()
            )
            trace.steps.append(step)
            trace.total_reward += reward
            if done:
                break

        trace.success = trace.total_reward > 0.5
        trace.length = len(trace.steps)
        self._traces.append(trace)
        self._save()
        return trace

    def get_trace(self, trace_id: str) -> RolloutTrace | None:
        for t in self._traces:
            if t.trace_id == trace_id:
                return t
        return None

    def list_by_task(self, task_id: str) -> list[RolloutTrace]:
        return [t for t in self._traces if t.task_id == task_id]

    def list_by_agent(self, agent_id: str) -> list[RolloutTrace]:
        return [t for t in self._traces if t.agent_id == agent_id]

    def avg_reward(self, agent_id: str) -> float:
        traces = [t for t in self._traces if t.agent_id == agent_id]
        if not traces:
            return 0.0
        return sum(t.total_reward for t in traces) / len(traces)

    def to_dict(self) -> dict:
        return {"trace_count": len(self._traces)}

    def get_stats(self) -> dict:
        by_task = {}
        by_agent = {}
        success = 0
        for t in self._traces:
            by_task[t.task_id] = by_task.get(t.task_id, 0) + 1
            by_agent[t.agent_id] = by_agent.get(t.agent_id, 0) + 1
            if t.success:
                success += 1
        avg_reward = sum(t.total_reward for t in self._traces) / len(self._traces) if self._traces else 0
        return {"traces": len(self._traces), "by_task": by_task, "by_agent": by_agent, "success_rate": round(success / len(self._traces), 2) if self._traces else 0, "avg_reward": round(avg_reward, 2)}

__all__ = ["TmaxAgentRolloutSimulator", "RolloutTrace", "RolloutStep"]
