"""LLM Step Sequencer — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto

class StepStatus(Enum):
    PENDING = auto()
    ACTIVE = auto()
    COMPLETED = auto()
    FAILED = auto()
    RETRYING = auto()

@dataclass
class Step:
    id: str
    name: str
    action: Callable[[Any], Any]
    retry_count: int = 0
    max_retries: int = 3
    status: StepStatus = StepStatus.PENDING
    input_data: Any = None
    output_data: Any = None
    error: Optional[str] = None

class StepSequencer:
    def __init__(self) -> None:
        self._steps: List[Step] = []

    def add_step(self, step: Step) -> None:
        self._steps.append(step)

    def execute(self, initial_data: Any) -> List[Step]:
        data = initial_data
        for step in self._steps:
            step.input_data = data
            step.status = StepStatus.ACTIVE
            attempt = 0
            while attempt <= step.max_retries:
                try:
                    step.output_data = step.action(data)
                    step.status = StepStatus.COMPLETED
                    data = step.output_data
                    break
                except Exception as ex:
                    attempt += 1
                    step.retry_count = attempt
                    step.error = str(ex)
                    if attempt > step.max_retries:
                        step.status = StepStatus.FAILED
                        break
                    step.status = StepStatus.RETRYING
        return self._steps

    def get_stats(self) -> Dict[str, Any]:
        return {"total": len(self._steps), "completed": sum(1 for s in self._steps if s.status == StepStatus.COMPLETED), "failed": sum(1 for s in self._steps if s.status == StepStatus.FAILED), "retries": sum(s.retry_count for s in self._steps)}

def run() -> None:
    print("Step Sequencer test")
    e = StepSequencer()
    e.add_step(Step("s1", "double", lambda x: x * 2))
    e.add_step(Step("s2", "add ten", lambda x: x + 10))
    e.add_step(Step("s3", "divide", lambda x: x / 2))
    results = e.execute(5)
    for step in results:
        print("  " + step.id + ": " + step.status.name + " -> " + str(step.output_data))
    print("  Stats: " + str(e.get_stats()))
    print("Step Sequencer test complete.")

if __name__ == "__main__":
    run()
