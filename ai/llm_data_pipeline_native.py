"""Data Pipeline — Ingestion, transformation, validation, and ETL workflow.

Modul ini menyediakan:
- DataSource untuk multiple input formats (JSON, CSV, text, API)
- DataTransformer untuk cleaning, normalization, enrichment
- DataValidator untuk schema validation dan quality checks
- Pipeline untuk chain ingestion → transform → validate → output
- PipelineRunner untuk execution dengan monitoring
"""

from __future__ import annotations

import json
import time
import uuid
import csv
import io
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from enum import Enum, auto


class DataFormat(Enum):
    JSON = "json"
    CSV = "csv"
    TEXT = "text"
    API = "api"
    STREAM = "stream"


class ValidationSeverity(Enum):
    INFO = auto()
    WARNING = auto()
    ERROR = auto()


@dataclass
class DataRecord:
    """Single record in pipeline."""
    record_id: str
    data: Dict[str, Any]
    source: str = ""
    format: DataFormat = DataFormat.JSON
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class ValidationResult:
    """Validation result for a record."""
    record_id: str
    passed: bool
    issues: List[Dict[str, Any]] = field(default_factory=list)

    def add_issue(self, field: str, message: str, severity: ValidationSeverity = ValidationSeverity.WARNING) -> None:
        self.issues.append({"field": field, "message": message, "severity": severity.name})
        if severity == ValidationSeverity.ERROR:
            self.passed = False


class DataSource:
    """Read data from various sources."""

    def __init__(self, source_id: str, name: str):
        self.source_id = source_id
        self.name = name

    def read_json(self, content: str) -> List[DataRecord]:
        try:
            data = json.loads(content)
            if isinstance(data, list):
                return [DataRecord(str(uuid.uuid4())[:8], item, self.name, DataFormat.JSON) for item in data]
            return [DataRecord(str(uuid.uuid4())[:8], data, self.name, DataFormat.JSON)]
        except Exception as e:
            return [DataRecord(str(uuid.uuid4())[:8], {"error": str(e), "raw": content[:100]}, self.name, DataFormat.JSON)]

    def read_csv(self, content: str) -> List[DataRecord]:
        try:
            reader = csv.DictReader(io.StringIO(content))
            return [DataRecord(str(uuid.uuid4())[:8], row, self.name, DataFormat.CSV) for row in reader]
        except Exception as e:
            return [DataRecord(str(uuid.uuid4())[:8], {"error": str(e)}, self.name, DataFormat.CSV)]

    def read_text(self, content: str) -> List[DataRecord]:
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        return [DataRecord(str(uuid.uuid4())[:8], {"text": line}, self.name, DataFormat.TEXT) for line in lines]

    def read_api(self, fetch_fn: Callable[[], Dict[str, Any]]) -> List[DataRecord]:
        try:
            data = fetch_fn()
            if isinstance(data, list):
                return [DataRecord(str(uuid.uuid4())[:8], item, self.name, DataFormat.API) for item in data]
            return [DataRecord(str(uuid.uuid4())[:8], data, self.name, DataFormat.API)]
        except Exception as e:
            return [DataRecord(str(uuid.uuid4())[:8], {"error": str(e)}, self.name, DataFormat.API)]


class DataTransformer:
    """Transform data records."""

    def __init__(self):
        self._transforms: List[Tuple[str, Callable[[Dict[str, Any]], Dict[str, Any]]]] = []

    def add_transform(self, name: str, fn: Callable[[Dict[str, Any]], Dict[str, Any]]) -> DataTransformer:
        self._transforms.append((name, fn))
        return self

    def transform(self, record: DataRecord) -> DataRecord:
        current = dict(record.data)
        for name, fn in self._transforms:
            try:
                current = fn(current)
            except Exception as e:
                current["_transform_error"] = f"{name}: {str(e)}"
                break
        record.data = current
        return record

    def transform_batch(self, records: List[DataRecord]) -> List[DataRecord]:
        return [self.transform(r) for r in records]

    @staticmethod
    def normalize_keys(data: Dict[str, Any]) -> Dict[str, Any]:
        return {k.lower().strip().replace(" ", "_"): v for k, v in data.items()}

    @staticmethod
    def trim_strings(data: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v.strip() if isinstance(v, str) else v for k, v in data.items()}

    @staticmethod
    def add_timestamp(data: Dict[str, Any]) -> Dict[str, Any]:
        data["_processed_at"] = time.time()
        return data

    @staticmethod
    def remove_empty(data: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in data.items() if v not in (None, "", [], {})}

    @staticmethod
    def default_pipeline() -> DataTransformer:
        t = DataTransformer()
        t.add_transform("normalize_keys", DataTransformer.normalize_keys)
        t.add_transform("trim_strings", DataTransformer.trim_strings)
        t.add_transform("remove_empty", DataTransformer.remove_empty)
        t.add_transform("add_timestamp", DataTransformer.add_timestamp)
        return t


class DataValidator:
    """Validate data records against schema."""

    def __init__(self):
        self._rules: List[Tuple[str, str, Callable[[Any], bool], str]] = []

    def add_rule(self, field: str, rule_name: str, check_fn: Callable[[Any], bool], message: str) -> None:
        self._rules.append((field, rule_name, check_fn, message))

    def validate(self, record: DataRecord) -> ValidationResult:
        result = ValidationResult(record.record_id, True)
        for field, rule_name, check_fn, message in self._rules:
            value = record.data.get(field)
            try:
                if not check_fn(value):
                    result.add_issue(field, f"{rule_name}: {message}", ValidationSeverity.ERROR)
            except Exception as e:
                result.add_issue(field, f"{rule_name}: Exception {str(e)}", ValidationSeverity.ERROR)
        return result

    def validate_batch(self, records: List[DataRecord]) -> List[ValidationResult]:
        return [self.validate(r) for r in records]

    @staticmethod
    def required(field: str) -> Tuple[str, str, Callable[[Any], bool], str]:
        return (field, "required", lambda v: v is not None and v != "", "Field is required")

    @staticmethod
    def min_length(field: str, length: int) -> Tuple[str, str, Callable[[Any], bool], str]:
        return (field, "min_length", lambda v: isinstance(v, str) and len(v) >= length, f"Min length {length}")

    @staticmethod
    def is_numeric(field: str) -> Tuple[str, str, Callable[[Any], bool], str]:
        return (field, "is_numeric", lambda v: isinstance(v, (int, float)) or (isinstance(v, str) and v.replace(".", "").isdigit()), "Must be numeric")

    @staticmethod
    def in_range(field: str, min_val: float, max_val: float) -> Tuple[str, str, Callable[[Any], bool], str]:
        return (field, "in_range", lambda v: isinstance(v, (int, float)) and min_val <= v <= max_val, f"Must be between {min_val} and {max_val}")


class Pipeline:
    """Data processing pipeline."""

    def __init__(self, pipeline_id: str, name: str):
        self.pipeline_id = pipeline_id
        self.name = name
        self.source: Optional[DataSource] = None
        self.transformer: DataTransformer = DataTransformer()
        self.validator: DataValidator = DataValidator()
        self._output: List[DataRecord] = []
        self._errors: List[Dict[str, Any]] = []

    def set_source(self, source: DataSource) -> Pipeline:
        self.source = source
        return self

    def set_transformer(self, transformer: DataTransformer) -> Pipeline:
        self.transformer = transformer
        return self

    def set_validator(self, validator: DataValidator) -> Pipeline:
        self.validator = validator
        return self

    def run(self, input_data: Union[str, Dict[str, Any], Callable[[], Dict[str, Any]]], fmt: DataFormat = DataFormat.JSON) -> Dict[str, Any]:
        start = time.time()
        # Read
        if fmt == DataFormat.JSON and isinstance(input_data, str):
            records = self.source.read_json(input_data) if self.source else []
        elif fmt == DataFormat.CSV and isinstance(input_data, str):
            records = self.source.read_csv(input_data) if self.source else []
        elif fmt == DataFormat.TEXT and isinstance(input_data, str):
            records = self.source.read_text(input_data) if self.source else []
        elif fmt == DataFormat.API and callable(input_data):
            records = self.source.read_api(input_data) if self.source else []
        else:
            records = [DataRecord(str(uuid.uuid4())[:8], input_data, "direct", fmt)]

        # Transform
        records = self.transformer.transform_batch(records)

        # Validate
        validations = self.validator.validate_batch(records)
        valid_records = []
        for record, validation in zip(records, validations):
            if validation.passed:
                valid_records.append(record)
            else:
                self._errors.append({
                    "record_id": record.record_id,
                    "issues": validation.issues,
                })

        self._output = valid_records
        duration = time.time() - start
        return {
            "pipeline_id": self.pipeline_id,
            "name": self.name,
            "input_count": len(records),
            "output_count": len(valid_records),
            "error_count": len(self._errors),
            "duration": round(duration, 3),
        }

    def get_output(self) -> List[DataRecord]:
        return self._output

    def get_errors(self) -> List[Dict[str, Any]]:
        return self._errors

    def export_output(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([r.data for r in self._output], f, indent=2)


class PipelineRunner:
    """Run multiple pipelines with monitoring."""

    def __init__(self):
        self._pipelines: Dict[str, Pipeline] = {}
        self._runs: List[Dict[str, Any]] = []

    def add_pipeline(self, pipeline: Pipeline) -> None:
        self._pipelines[pipeline.pipeline_id] = pipeline

    def run(self, pipeline_id: str, input_data: Union[str, Dict[str, Any]], fmt: DataFormat = DataFormat.JSON) -> Dict[str, Any]:
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return {"error": "Pipeline not found"}
        result = pipeline.run(input_data, fmt)
        self._runs.append(result)
        return result

    def run_batch(self, pipeline_id: str, items: List[Tuple[Union[str, Dict[str, Any]], DataFormat]]) -> List[Dict[str, Any]]:
        return [self.run(pipeline_id, data, fmt) for data, fmt in items]

    def get_stats(self) -> Dict[str, Any]:
        if not self._runs:
            return {}
        total = len(self._runs)
        return {
            "total_runs": total,
            "avg_input": sum(r.get("input_count", 0) for r in self._runs) / total,
            "avg_output": sum(r.get("output_count", 0) for r in self._runs) / total,
            "avg_errors": sum(r.get("error_count", 0) for r in self._runs) / total,
            "avg_duration": sum(r.get("duration", 0) for r in self._runs) / total,
        }


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("DATA PIPELINE DEMO")
    print("=" * 70)

    # 1. JSON ingestion
    print("\n[1] JSON Ingestion")
    source = DataSource("src-1", "API Source")
    json_data = json.dumps([
        {"name": "Alice", "age": 30, "city": "New York"},
        {"name": "Bob", "age": 25, "city": "London"},
        {"name": "Charlie", "age": 35, "city": "Tokyo"},
    ])
    records = source.read_json(json_data)
    print(f"  Read {len(records)} JSON records")
    for r in records:
        print(f"    {r.record_id}: {r.data}")

    # 2. CSV ingestion
    print("\n[2] CSV Ingestion")
    csv_data = "name,age,city\nAlice,30,New York\nBob,25,London\nCharlie,35,Tokyo"
    records = source.read_csv(csv_data)
    print(f"  Read {len(records)} CSV records")
    for r in records:
        print(f"    {r.record_id}: {r.data}")

    # 3. Transformation
    print("\n[3] Transformation")
    transformer = DataTransformer.default_pipeline()
    record = DataRecord("r1", {"Name": " Alice ", "Age": "30", "City": "New York"})
    transformed = transformer.transform(record)
    print(f"  Before: {record.data}")
    print(f"  After: {transformed.data}")

    # 4. Validation
    print("\n[4] Validation")
    validator = DataValidator()
    validator.add_rule(*DataValidator.required("name"))
    validator.add_rule(*DataValidator.min_length("name", 2))
    validator.add_rule(*DataValidator.is_numeric("age"))
    validator.add_rule(*DataValidator.in_range("age", 0, 150))

    test_records = [
        DataRecord("v1", {"name": "Alice", "age": 30}),
        DataRecord("v2", {"name": "", "age": 30}),
        DataRecord("v3", {"name": "Bob", "age": "not a number"}),
        DataRecord("v4", {"name": "Charlie", "age": 200}),
    ]
    for r in test_records:
        result = validator.validate(r)
        print(f"  {r.record_id}: {'PASS' if result.passed else 'FAIL'} - {len(result.issues)} issues")

    # 5. Full pipeline
    print("\n[5] Full Pipeline")
    pipeline = Pipeline("p1", "User Data Pipeline")
    pipeline.set_source(source)
    pipeline.set_transformer(transformer)
    pipeline.set_validator(validator)
    result = pipeline.run(json_data, DataFormat.JSON)
    print(f"  Pipeline: {result['name']}")
    print(f"  Input: {result['input_count']}, Output: {result['output_count']}, Errors: {result['error_count']}")
    print(f"  Duration: {result['duration']:.3f}s")
    for r in pipeline.get_output():
        print(f"    {r.record_id}: {r.data}")

    # 6. Pipeline runner
    print("\n[6] Pipeline Runner")
    runner = PipelineRunner()
    runner.add_pipeline(pipeline)
    results = runner.run_batch("p1", [
        (json_data, DataFormat.JSON),
        (csv_data, DataFormat.CSV),
    ])
    for r in results:
        print(f"  Run: {r.get('input_count', 0)} in, {r.get('output_count', 0)} out, {r.get('error_count', 0)} errors")
    print(f"  Runner stats: {runner.get_stats()}")

    # 7. Custom transform
    print("\n[7] Custom Transform")
    custom = DataTransformer()
    custom.add_transform("uppercase", lambda d: {k: v.upper() if isinstance(v, str) else v for k, v in d.items()})
    custom.add_transform("add_id", lambda d: {**d, "id": str(uuid.uuid4())[:8]})
    record = DataRecord("c1", {"name": "test", "value": "hello"})
    result = custom.transform(record)
    print(f"  Custom transform: {result.data}")

    # 8. Export
    print("\n[8] Export")
    pipeline.export_output("/tmp/pipeline_output.json")
    print("  Exported to /tmp/pipeline_output.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
