#!/usr/bin/env python3
"""ETL Pipeline for MAGNATRIX-OS — Extract, Transform, Load."""
from __future__ import annotations
import json, time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

@dataclass
class ETLStage:
    name: str
    transform: Callable[[Any], Any]

class ETLPipeline:
    def __init__(self, name: str = "pipeline") -> None:
        self.name = name
        self._stages: List[ETLStage] = []
        self._metrics: Dict[str, Any] = {}

    def add_stage(self, stage: ETLStage) -> None:
        self._stages.append(stage)

    def run(self, data: Any) -> Any:
        result = data
        t0 = time.time()
        for stage in self._stages:
            st = time.time()
            result = stage.transform(result)
            self._metrics[stage.name] = {"duration_ms": (time.time() - st) * 1000}
        self._metrics["total_ms"] = (time.time() - t0) * 1000
        return result

    def stats(self) -> Dict[str, Any]:
        return {"stages": len(self._stages), "metrics": self._metrics}
