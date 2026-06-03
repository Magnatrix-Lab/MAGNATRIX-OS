"""LLM ReAct Framework — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum, auto

class ReActPhase(Enum):
    THOUGHT = auto()
    ACTION = auto()
    OBSERVATION = auto()
    FINISH = auto()

@dataclass
class ReActStep:
    phase: ReActPhase
    content: str
    step_number: int
    metadata: Dict[str, Any] = field(default_factory=dict)

class ReActFrameworkEngine:
    def __init__(self, max_iterations: int = 10) -> None:
        self.max_iterations = max_iterations
        self._steps: List[ReActStep] = []
        self._iteration = 0

    def thought(self, content: str) -> ReActStep:
        self._iteration += 1
        step = ReActStep(ReActPhase.THOUGHT, content, self._iteration)
        self._steps.append(step)
        return step

    def action(self, content: str) -> ReActStep:
        step = ReActStep(ReActPhase.ACTION, content, self._iteration)
        self._steps.append(step)
        return step

    def observation(self, content: str) -> ReActStep:
        step = ReActStep(ReActPhase.OBSERVATION, content, self._iteration)
        self._steps.append(step)
        return step

    def finish(self, content: str) -> ReActStep:
        step = ReActStep(ReActPhase.FINISH, content, self._iteration)
        self._steps.append(step)
        return step

    def get_trace(self) -> str:
        lines = []
        for step in self._steps:
            lines.append(step.phase.value.upper() + " [" + str(step.step_number) + "]: " + step.content)
        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        by_phase = {}
        for s in self._steps:
            by_phase[s.phase.value] = by_phase.get(s.phase.value, 0) + 1
        return {"iterations": self._iteration, "steps": len(self._steps), "by_phase": by_phase}

def run() -> None:
    print("ReAct Framework test")
    e = ReActFrameworkEngine(max_iterations=5)
    e.thought("I need to find the capital of France")
    e.action("Search for capital of France")
    e.observation("Paris is the capital of France")
    e.finish("The capital of France is Paris")
    print("  Trace:")
    print(e.get_trace())
    print("  Stats: " + str(e.get_stats()))
    print("ReAct Framework test complete.")

if __name__ == "__main__":
    run()
