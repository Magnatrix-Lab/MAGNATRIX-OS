"""Data Ingestion Pipeline — ETL pipeline untuk LLM data: extract, transform, validate, load.

Modul ini menyediakan:
- DataExtractor untuk multiple sources (file, API, stream, database)
- DataTransformer dengan filter, map, reduce operations
- DataValidator dengan schema validation
- DataLoader untuk batch loading
- Pipeline orchestrator dengan dependency tracking
"""

from __future__ import annotations

import json
import time
import uuid
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class DataSourceType(Enum):
    FILE = auto()
    API = auto()
    STREAM = auto()
    DATABASE = auto()
    MEMORY = auto()


class DataFormat(Enum):
    JSON = auto()
    CSV = auto()
    TEXT = auto()
    MARKDOWN = auto()
    XML = auto()


class PipelineStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    PAUSED = auto()


@dataclass
class DataRecord:
    """Single record dalam pipeline."""
    record_id: str
    source: str
    data: Dict[str, Any]
    format: DataFormat = DataFormat.JSON
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    valid: bool = True
    errors: List[str] = field(default_factory=list)


@dataclass
class PipelineStage:
    """Single stage dalam pipeline."""
    stage_id: str
    name: str
    operation: Callable[[DataRecord], DataRecord]
    filter_fn: Optional[Callable[[DataRecord], bool]] = None


class DataExtractor:
    """Extract data dari berbagai sources."""

    def __init__(self):
        self._sources: Dict[str, Tuple[DataSourceType, Callable[[], List[DataRecord]]]] = {}

    def register_source(self, name: str, source_type: DataSourceType, extractor_fn: Callable[[], List[DataRecord]]) -> None:
        self._sources[name] = (source_type, extractor_fn)

    def extract(self, source_name: str) -> List[DataRecord]:
        _, fn = self._sources.get(source_name, (None, lambda: []))
        return fn()

    def extract_all(self) -> List[DataRecord]:
        records = []
        for name, (_, fn) in self._sources.items():
            records.extend(fn())
        return records

    @staticmethod
    def from_file(path: str, format: DataFormat = DataFormat.JSON) -> List[DataRecord]:
        records = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                if format == DataFormat.JSON:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            records.append(DataRecord(str(uuid.uuid4())[:8], path, item, format))
                    else:
                        records.append(DataRecord(str(uuid.uuid4())[:8], path, data, format))
                elif format == DataFormat.TEXT:
                    content = f.read()
                    records.append(DataRecord(str(uuid.uuid4())[:8], path, {"content": content}, format))
        except Exception as e:
            records.append(DataRecord(str(uuid.uuid4())[:8], path, {"error": str(e)}, format, valid=False, errors=[str(e)]))
        return records

    @staticmethod
    def from_text(text: str, source: str = "inline") -> List[DataRecord]:
        return [DataRecord(str(uuid.uuid4())[:8], source, {"content": text}, DataFormat.TEXT)]


class DataTransformer:
    """Transform data dengan map/filter/reduce operations."""

    def __init__(self):
        self._operations: List[Tuple[str, Callable[[DataRecord], DataRecord]]] = []

    def add_map(self, name: str, fn: Callable[[Dict[str, Any]], Dict[str, Any]]) -> DataTransformer:
        self._operations.append((name, lambda r: DataRecord(r.record_id, r.source, fn(r.data), r.format, r.timestamp, r.metadata, r.valid, r.errors)))
        return self

    def add_filter(self, name: str, fn: Callable[[DataRecord], bool]) -> DataTransformer:
        self._operations.append((name, lambda r: r if fn(r) else DataRecord(r.record_id, r.source, r.data, r.format, r.timestamp, r.metadata, False, r.errors + [f"Filtered by {name}"])))
        return self

    def add_clean(self, name: str, fn: Callable[[Dict[str, Any]], Dict[str, Any]]) -> DataTransformer:
        self._operations.append((name, lambda r: DataRecord(r.record_id, r.source, fn(r.data), r.format, r.timestamp, r.metadata, r.valid, r.errors)))
        return self

    def transform(self, records: List[DataRecord]) -> List[DataRecord]:
        results = []
        for record in records:
            current = record
            for name, op in self._operations:
                current = op(current)
            results.append(current)
        return results

    def transform_batch(self, records: List[DataRecord]) -> List[DataRecord]:
        return self.transform(records)

    @staticmethod
    def clean_text(data: Dict[str, Any]) -> Dict[str, Any]:
        if "content" in data and isinstance(data["content"], str):
            text = data["content"]
            # Remove extra whitespace
            text = re.sub(r'\s+', ' ', text)
            # Remove special characters but keep basic punctuation
            text = re.sub(r'[^\w\s.,;:!?()-]', '', text)
            data["content"] = text.strip()
        return data

    @staticmethod
    def extract_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
        if "content" in data and isinstance(data["content"], str):
            text = data["content"]
            data["word_count"] = len(text.split())
            data["char_count"] = len(text)
        return data


class DataValidator:
    """Validate data records against schema."""

    def __init__(self):
        self._schemas: Dict[str, Dict[str, Any]] = {}

    def register_schema(self, name: str, schema: Dict[str, Any]) -> None:
        self._schemas[name] = schema

    def validate(self, record: DataRecord, schema_name: str) -> DataRecord:
        schema = self._schemas.get(schema_name)
        if not schema:
            return record
        errors = []
        for field, spec in schema.items():
            if field not in record.data:
                if spec.get("required", False):
                    errors.append(f"Missing required field: {field}")
                continue
            value = record.data[field]
            expected_type = spec.get("type")
            if expected_type == "string" and not isinstance(value, str):
                errors.append(f"Field {field} should be string, got {type(value).__name__}")
            elif expected_type == "number" and not isinstance(value, (int, float)):
                errors.append(f"Field {field} should be number, got {type(value).__name__}")
            elif expected_type == "integer" and not isinstance(value, int):
                errors.append(f"Field {field} should be integer, got {type(value).__name__}")
            elif expected_type == "boolean" and not isinstance(value, bool):
                errors.append(f"Field {field} should be boolean, got {type(value).__name__}")
            elif expected_type == "array" and not isinstance(value, list):
                errors.append(f"Field {field} should be array, got {type(value).__name__}")
            elif expected_type == "object" and not isinstance(value, dict):
                errors.append(f"Field {field} should be object, got {type(value).__name__}")
        if errors:
            record.valid = False
            record.errors.extend(errors)
        return record

    def validate_batch(self, records: List[DataRecord], schema_name: str) -> List[DataRecord]:
        return [self.validate(r, schema_name) for r in records]


class DataLoader:
    """Load data ke destination."""

    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self._destinations: Dict[str, Callable[[List[DataRecord]], int]] = {}

    def register_destination(self, name: str, loader_fn: Callable[[List[DataRecord]], int]) -> None:
        self._destinations[name] = loader_fn

    def load(self, records: List[DataRecord], destination: str) -> Tuple[int, int]:
        loader = self._destinations.get(destination)
        if not loader:
            return 0, 0
        valid_records = [r for r in records if r.valid]
        batches = [valid_records[i:i+self.batch_size] for i in range(0, len(valid_records), self.batch_size)]
        total_loaded = 0
        for batch in batches:
            total_loaded += loader(batch)
        return total_loaded, len(valid_records) - total_loaded

    @staticmethod
    def to_json_file(records: List[DataRecord], path: str) -> int:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump([r.data for r in records], f, indent=2)
            return len(records)
        except Exception:
            return 0


class DataPipeline:
    """Orchestrate ETL pipeline."""

    def __init__(self, pipeline_id: str, name: str):
        self.pipeline_id = pipeline_id
        self.name = name
        self.extractor = DataExtractor()
        self.transformer = DataTransformer()
        self.validator = DataValidator()
        self.loader = DataLoader()
        self._stages: List[PipelineStage] = []
        self._status = PipelineStatus.PENDING
        self._records: List[DataRecord] = []
        self._logs: List[Dict[str, Any]] = []
        self._stats = {"extracted": 0, "transformed": 0, "valid": 0, "invalid": 0, "loaded": 0}

    def add_stage(self, stage: PipelineStage) -> None:
        self._stages.append(stage)

    def run(self, source: str, destination: Optional[str] = None, schema_name: Optional[str] = None) -> Dict[str, Any]:
        self._status = PipelineStatus.RUNNING
        start = time.time()

        # Extract
        self._records = self.extractor.extract(source)
        self._stats["extracted"] = len(self._records)
        self._log("extract", f"Extracted {len(self._records)} records")

        # Transform
        self._records = self.transformer.transform(self._records)
        self._stats["transformed"] = len(self._records)
        self._log("transform", f"Transformed {len(self._records)} records")

        # Validate
        if schema_name:
            self._records = self.validator.validate_batch(self._records, schema_name)
        self._stats["valid"] = sum(1 for r in self._records if r.valid)
        self._stats["invalid"] = sum(1 for r in self._records if not r.valid)
        self._log("validate", f"Valid: {self._stats['valid']}, Invalid: {self._stats['invalid']}")

        # Custom stages
        for stage in self._stages:
            processed = []
            for record in self._records:
                if stage.filter_fn and not stage.filter_fn(record):
                    continue
                processed.append(stage.operation(record))
            self._records = processed
            self._log("stage", f"Stage {stage.name}: {len(processed)} records")

        # Load
        if destination:
            loaded, failed = self.loader.load(self._records, destination)
            self._stats["loaded"] = loaded
            self._log("load", f"Loaded {loaded}, Failed {failed}")

        self._status = PipelineStatus.COMPLETED
        duration = time.time() - start
        self._log("complete", f"Pipeline completed in {duration:.2f}s")

        return {
            "pipeline_id": self.pipeline_id,
            "status": self._status.name,
            "duration": round(duration, 2),
            "stats": self._stats,
            "records": len(self._records)
        }

    def get_records(self, valid_only: bool = True) -> List[DataRecord]:
        if valid_only:
            return [r for r in self._records if r.valid]
        return self._records

    def _log(self, stage: str, message: str) -> None:
        self._logs.append({"timestamp": time.time(), "stage": stage, "message": message})

    def get_logs(self) -> List[Dict[str, Any]]:
        return self._logs

    def get_stats(self) -> Dict[str, Any]:
        return {**self._stats, "status": self._status.name, "total_logs": len(self._logs)}

    def export_results(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "pipeline_id": self.pipeline_id,
                "stats": self._stats,
                "records": [r.data for r in self._records if r.valid],
                "logs": self._logs
            }, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("DATA INGESTION PIPELINE DEMO")
    print("=" * 70)

    # 1. Extract dari file
    print("\n[1] Extract from File")
    # Create sample file
    sample_data = [
        {"name": "Alice", "age": 30, "city": "Boston", "role": "engineer"},
        {"name": "Bob", "age": 25, "city": "New York", "role": "designer"},
        {"name": "Charlie", "age": 35, "city": "San Francisco", "role": "manager"},
        {"name": "Diana", "age": 28, "city": "Boston", "role": "engineer"},
    ]
    with open("/tmp/sample_data.json", "w", encoding="utf-8") as f:
        json.dump(sample_data, f)

    extractor = DataExtractor()
    extractor.register_source("sample", DataSourceType.FILE, lambda: DataExtractor.from_file("/tmp/sample_data.json", DataFormat.JSON))
    records = extractor.extract("sample")
    print(f"  Extracted {len(records)} records")

    # 2. Transform
    print("\n[2] Transform")
    transformer = DataTransformer()
    transformer.add_filter("age_filter", lambda r: r.data.get("age", 0) >= 25)
    transformer.add_map("uppercase_name", lambda d: {**d, "name": d.get("name", "").upper()})
    transformer.add_clean("metadata", DataTransformer.extract_metadata)
    records = transformer.transform(records)
    print(f"  After transform: {len(records)} records")
    for r in records:
        print(f"    {r.data}")

    # 3. Validate
    print("\n[3] Validate")
    validator = DataValidator()
    validator.register_schema("person", {
        "name": {"type": "string", "required": True},
        "age": {"type": "integer", "required": True},
        "city": {"type": "string", "required": False},
    })
    records = validator.validate_batch(records, "person")
    valid = [r for r in records if r.valid]
    invalid = [r for r in records if not r.valid]
    print(f"  Valid: {len(valid)}, Invalid: {len(invalid)}")

    # 4. Pipeline
    print("\n[4] Full Pipeline")
    pipeline = DataPipeline("pipe-1", "Employee Pipeline")
    pipeline.extractor.register_source("employees", DataSourceType.MEMORY, lambda: [
        DataRecord(str(i), "memory", d, DataFormat.JSON)
        for i, d in enumerate([
            {"name": "John", "age": 30, "dept": "Engineering"},
            {"name": "Jane", "age": 25, "dept": "Design"},
            {"name": "Jack", "age": "invalid", "dept": "Sales"},  # Invalid age
            {"name": "Jill", "age": 35, "dept": "Engineering"},
        ])
    ])
    pipeline.transformer.add_filter("age_filter", lambda r: isinstance(r.data.get("age"), int) and r.data["age"] >= 25)
    pipeline.validator.register_schema("employee", {
        "name": {"type": "string", "required": True},
        "age": {"type": "integer", "required": True},
        "dept": {"type": "string", "required": True},
    })
    result = pipeline.run("employees", schema_name="employee")
    print(f"  Pipeline result: {result}")
    print(f"  Valid records: {len(pipeline.get_records())}")

    # 5. Export
    print("\n[5] Export Results")
    pipeline.export_results("/tmp/pipeline_results.json")
    print(f"  Exported to /tmp/pipeline_results.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
