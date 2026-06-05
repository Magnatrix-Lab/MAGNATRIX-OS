"""ETL Pipeline Engine — extract, transform, load, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Any, Optional
from enum import Enum, auto
import json

class ETLStage(Enum):
    EXTRACT = auto()
    TRANSFORM = auto()
    LOAD = auto()

@dataclass
class ETLStep:
    step_id: str
    stage: ETLStage
    func: Callable
    config: Dict = field(default_factory=dict)

class ETLPipeline:
    def __init__(self):
        self.steps: List[ETLStep] = []
        self.data: Any = None
        self.errors: List[Dict] = []
        self.metrics: Dict = {"records_in": 0, "records_out": 0, "errors": 0}

    def add_step(self, step_id: str, stage: ETLStage, func: Callable, config: Dict = None):
        self.steps.append(ETLStep(step_id, stage, func, config or {}))

    def run(self, source: Any) -> Any:
        self.data = source
        self.metrics["records_in"] = len(self.data) if isinstance(self.data, list) else 1
        for step in self.steps:
            try:
                self.data = step.func(self.data, step.config)
            except Exception as e:
                self.errors.append({"step": step.step_id, "error": str(e)})
                self.metrics["errors"] += 1
        self.metrics["records_out"] = len(self.data) if isinstance(self.data, list) else 1
        return self.data

    def stats(self) -> Dict:
        return {"steps": len(self.steps), **self.metrics, "errors": len(self.errors)}

def run():
    pipeline = ETLPipeline()
    pipeline.add_step("extract", ETLStage.EXTRACT, lambda data, cfg: [{"id": i, "name": f"item_{i}"} for i in range(5)], {})
    pipeline.add_step("transform", ETLStage.TRANSFORM, lambda data, cfg: [{**d, "upper_name": d["name"].upper()} for d in data], {})
    pipeline.add_step("filter", ETLStage.TRANSFORM, lambda data, cfg: [d for d in data if d["id"] % 2 == 0], {})
    pipeline.add_step("load", ETLStage.LOAD, lambda data, cfg: json.dumps(data), {})
    result = pipeline.run(None)
    print(result)
    print(pipeline.stats())

if __name__ == "__main__":
    run()
