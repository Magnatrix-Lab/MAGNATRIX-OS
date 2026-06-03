"""LLM Pipeline Engine — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto

class PipelineStageStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    SKIPPED = auto()

@dataclass
class PipelineStage:
    id: str
    name: str
    processor: Callable[[Any], Any]
    dependencies: List[str] = field(default_factory=list)
    status: PipelineStageStatus = PipelineStageStatus.PENDING
    input_data: Any = None
    output_data: Any = None
    error: Optional[str] = None

class PipelineEngine:
    def __init__(self) -> None:
        self._stages: Dict[str, PipelineStage] = {}

    def add_stage(self, stage: PipelineStage) -> None:
        self._stages[stage.id] = stage

    def _resolve_order(self) -> List[str]:
        resolved = []
        unresolved = set(self._stages.keys())
        while unresolved:
            progress = False
            for sid in list(unresolved):
                stage = self._stages[sid]
                if all(dep in resolved for dep in stage.dependencies):
                    resolved.append(sid)
                    unresolved.remove(sid)
                    progress = True
            if not progress:
                raise ValueError("Circular dependency in pipeline stages")
        return resolved

    def run(self, initial_data: Any) -> Dict[str, Any]:
        order = self._resolve_order()
        data = initial_data
        for sid in order:
            stage = self._stages[sid]
            stage.status = PipelineStageStatus.RUNNING
            stage.input_data = data
            try:
                stage.output_data = stage.processor(data)
                stage.status = PipelineStageStatus.COMPLETED
                data = stage.output_data
            except Exception as ex:
                stage.status = PipelineStageStatus.FAILED
                stage.error = str(ex)
                raise
        return {sid: self._stages[sid].output_data for sid in order}

    def get_stats(self) -> Dict[str, Any]:
        return {"stages": len(self._stages), "completed": sum(1 for s in self._stages.values() if s.status == PipelineStageStatus.COMPLETED), "failed": sum(1 for s in self._stages.values() if s.status == PipelineStageStatus.FAILED)}

def run() -> None:
    print("Pipeline Engine test")
    e = PipelineEngine()
    e.add_stage(PipelineStage("s1", "tokenize", lambda x: x.split()))
    e.add_stage(PipelineStage("s2", "uppercase", lambda x: [w.upper() for w in x], dependencies=["s1"]))
    e.add_stage(PipelineStage("s3", "join", lambda x: " ".join(x), dependencies=["s2"]))
    results = e.run("hello world test")
    print("  Results: " + str(results))
    print("  Stats: " + str(e.get_stats()))
    print("Pipeline Engine test complete.")

if __name__ == "__main__":
    run()
