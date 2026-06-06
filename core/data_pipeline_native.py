#!/usr/bin/env python3
"""
Data Pipeline for MAGNATRIX-OS
ETL, data transformation, streaming, and pipeline orchestration.
Supports map/filter/reduce, batch processing, and pipeline DAG.
Native stdlib only.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import csv
import dataclasses
import enum
import json
import time
from io import StringIO
from pathlib import Path
from typing import Any, Callable, Dict, Generic, Iterator, List, Optional, TypeVar, Union

T = TypeVar("T")
U = TypeVar("U")


class StageType(enum.Enum):
    EXTRACT = "extract"
    TRANSFORM = "transform"
    LOAD = "load"


@dataclasses.dataclass
class PipelineStage:
    name: str
    stage_type: StageType
    handler: Callable[[Any], Any]
    input_schema: Optional[str] = None
    output_schema: Optional[str] = None
    error_handler: Optional[Callable[[Any, Exception], Any]] = None


@dataclasses.dataclass
class PipelineResult:
    stage_name: str
    input_count: int
    output_count: int
    error_count: int
    duration_ms: float
    errors: List[Dict[str, Any]] = dataclasses.field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage_name,
            "in": self.input_count,
            "out": self.output_count,
            "errors": self.error_count,
            "duration_ms": self.duration_ms,
        }


class DataPipeline:
    """ETL pipeline with stage chaining, error handling, and stats."""

    def __init__(self, name: str = "pipeline") -> None:
        self.name = name
        self._stages: List[PipelineStage] = []
        self._results: List[PipelineResult] = []
        self._hooks: List[Callable[[PipelineResult], None]] = []

    # ------------------------------------------------------------------
    # Stage registration
    # ------------------------------------------------------------------

    def add_stage(self, stage: PipelineStage) -> None:
        self._stages.append(stage)

    def map(self, name: str, fn: Callable[[T], U]) -> None:
        self.add_stage(PipelineStage(name, StageType.TRANSFORM, fn))

    def filter(self, name: str, predicate: Callable[[T], bool]) -> None:
        def _filter(data: List[T]) -> List[T]:
            if isinstance(data, list):
                return [d for d in data if predicate(d)]
            return data if predicate(data) else None
        self.add_stage(PipelineStage(name, StageType.TRANSFORM, _filter))

    def reduce(self, name: str, fn: Callable[[T, T], T]) -> None:
        def _reduce(data: List[T]) -> T:
            if isinstance(data, list) and len(data) > 0:
                result = data[0]
                for item in data[1:]:
                    result = fn(result, item)
                return result
            return data
        self.add_stage(PipelineStage(name, StageType.TRANSFORM, _reduce))

    def batch(self, name: str, size: int = 100) -> None:
        def _batch(data: Iterator[T]) -> Iterator[List[T]]:
            batch = []
            for item in data:
                batch.append(item)
                if len(batch) >= size:
                    yield batch
                    batch = []
            if batch:
                yield batch
        self.add_stage(PipelineStage(name, StageType.TRANSFORM, _batch))

    def add_hook(self, hook: Callable[[PipelineResult], None]) -> None:
        self._hooks.append(hook)

    # ------------------------------------------------------------------
    # Extractors
    # ------------------------------------------------------------------

    @staticmethod
    def from_json(data: str | List[str]) -> List[Dict[str, Any]]:
        if isinstance(data, str):
            return [json.loads(data)]
        return [json.loads(line) for line in data]

    @staticmethod
    def from_csv(data: str) -> List[Dict[str, str]]:
        reader = csv.DictReader(StringIO(data))
        return list(reader)

    @staticmethod
    def from_file(path: str) -> Iterator[str]:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                yield line.strip()

    # ------------------------------------------------------------------
    # Transformers
    # ------------------------------------------------------------------

    @staticmethod
    def transform_map(fn: Callable[[Any], Any]) -> Callable[[Any], Any]:
        def _wrapper(data: Any) -> Any:
            if isinstance(data, (list, Iterator)):
                return [fn(item) for item in data]
            return fn(data)
        return _wrapper

    @staticmethod
    def transform_filter(predicate: Callable[[Any], bool]) -> Callable[[Any], Any]:
        def _wrapper(data: Any) -> Any:
            if isinstance(data, (list, Iterator)):
                return [item for item in data if predicate(item)]
            return data if predicate(data) else None
        return _wrapper

    # ------------------------------------------------------------------
    # Loaders
    # ------------------------------------------------------------------

    @staticmethod
    def to_json(data: List[Dict[str, Any]]) -> str:
        return json.dumps(data, indent=2, ensure_ascii=False)

    @staticmethod
    def to_csv(data: List[Dict[str, Any]]) -> str:
        if not data:
            return ""
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()

    @staticmethod
    def to_file(data: List[str], path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            for line in data:
                f.write(line + "\n")

    # ------------------------------------------------------------------
    # Pipeline execution
    # ------------------------------------------------------------------

    def run(self, data: Any) -> Any:
        current = data
        for stage in self._stages:
            start = time.time()
            input_count = len(current) if isinstance(current, list) else 1
            output_count = 0
            error_count = 0
            errors = []
            try:
                if isinstance(current, list):
                    result = []
                    for item in current:
                        try:
                            r = stage.handler(item)
                            if r is not None:
                                result.append(r)
                        except Exception as e:
                            error_count += 1
                            errors.append({"item": str(item)[:100], "error": str(e)})
                            if stage.error_handler:
                                try:
                                    r = stage.error_handler(item, e)
                                    if r is not None:
                                        result.append(r)
                                except Exception:
                                    pass
                    current = result
                    output_count = len(current)
                else:
                    try:
                        current = stage.handler(current)
                        output_count = 1 if current is not None else 0
                    except Exception as e:
                        error_count += 1
                        errors.append({"item": str(current)[:100], "error": str(e)})
                        if stage.error_handler:
                            try:
                                current = stage.error_handler(current, e)
                                output_count = 1 if current is not None else 0
                            except Exception:
                                current = None
            except Exception as e:
                error_count += 1
                errors.append({"stage": stage.name, "error": str(e)})
            duration = (time.time() - start) * 1000
            result = PipelineResult(
                stage_name=stage.name,
                input_count=input_count,
                output_count=output_count,
                error_count=error_count,
                duration_ms=round(duration, 2),
                errors=errors,
            )
            self._results.append(result)
            for hook in self._hooks:
                try:
                    hook(result)
                except Exception:
                    pass
        return current

    def run_stream(self, data: Iterator[T]) -> Iterator[Any]:
        """Process streaming data one item at a time."""
        for item in data:
            current = item
            for stage in self._stages:
                try:
                    current = stage.handler(current)
                except Exception as e:
                    if stage.error_handler:
                        try:
                            current = stage.error_handler(current, e)
                        except Exception:
                            current = None
                    else:
                        current = None
                if current is None:
                    break
            if current is not None:
                yield current

    # ------------------------------------------------------------------
    # DAG support
    # ------------------------------------------------------------------

    def run_dag(self, data: Any, dag: Dict[str, List[str]]) -> Dict[str, Any]:
        """Execute stages in DAG order. dag: {stage_name -> [dependencies]}."""
        # Simple topological sort
        visited = set()
        order = []
        def visit(name: str) -> None:
            if name in visited:
                return
            visited.add(name)
            for dep in dag.get(name, []):
                visit(dep)
            order.append(name)
        for name in dag:
            visit(name)
        # Map name to stage
        stage_map = {s.name: s for s in self._stages}
        outputs = {}
        for name in order:
            stage = stage_map.get(name)
            if not stage:
                continue
            inputs = data
            if dag.get(name):
                dep_outputs = [outputs[d] for d in dag[name] if d in outputs]
                if dep_outputs:
                    inputs = dep_outputs[-1]
            outputs[name] = stage.handler(inputs)
        return outputs

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        total_in = sum(r.input_count for r in self._results)
        total_out = sum(r.output_count for r in self._results)
        total_err = sum(r.error_count for r in self._results)
        total_dur = sum(r.duration_ms for r in self._results)
        return {
            "pipeline": self.name,
            "stages": len(self._stages),
            "total_input": total_in,
            "total_output": total_out,
            "total_errors": total_err,
            "total_duration_ms": round(total_dur, 2),
            "stage_results": [r.to_dict() for r in self._results],
        }

    def get_results(self) -> List[PipelineResult]:
        return self._results

    def reset(self) -> None:
        self._results.clear()


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== Data Pipeline Demo ===\n")
    # Example 1: Simple ETL
    pipeline = DataPipeline("user_etl")
    pipeline.map("parse_json", lambda x: json.loads(x) if isinstance(x, str) else x)
    pipeline.filter("valid_age", lambda x: x.get("age", 0) >= 18)
    pipeline.map("enrich", lambda x: {**x, "status": "active"})
    data = [
        '{"name": "Alice", "age": 30}',
        '{"name": "Bob", "age": 15}',
        '{"name": "Charlie", "age": 25}',
    ]
    result = pipeline.run(data)
    print(f"ETL result: {result}")
    print(f"Stats: {pipeline.stats()}")
    # Example 2: CSV transform
    print("\n--- CSV Pipeline ---")
    csv_data = "name,age\nAlice,30\nBob,15\nCharlie,25\n"
    rows = DataPipeline.from_csv(csv_data)
    pipeline2 = DataPipeline("csv_transform")
    pipeline2.map("double_age", lambda x: {**x, "age": int(x["age"]) * 2})
    result2 = pipeline2.run(rows)
    print(f"Transformed: {result2}")
    # Example 3: DAG
    print("\n--- DAG Pipeline ---")
    pipeline3 = DataPipeline("dag_demo")
    pipeline3.add_stage(PipelineStage("extract", StageType.EXTRACT, lambda x: [i * 2 for i in x]))
    pipeline3.add_stage(PipelineStage("filter", StageType.TRANSFORM, lambda x: [i for i in x if i > 5]))
    pipeline3.add_stage(PipelineStage("load", StageType.LOAD, lambda x: sum(x)))
    dag = {"filter": ["extract"], "load": ["filter"]}
    outputs = pipeline3.run_dag([1, 2, 3, 4, 5], dag)
    print(f"DAG outputs: {outputs}")


if __name__ == "__main__":
    _demo()
