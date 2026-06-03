"""
llm_data_catalog_native.py
MAGNATRIX-OS Data Catalog Engine
Native Python, stdlib only.
Provides data catalog with schema registry, dataset discovery, lineage links, and metadata management.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set


class DatasetStatus(Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DRAFT = "draft"
    ARCHIVED = "archived"


class DataType(Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    TIMESTAMP = "timestamp"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class ColumnSchema:
    name: str
    data_type: DataType
    nullable: bool = True
    description: str = ""
    tags: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "data_type": self.data_type.value,
            "nullable": self.nullable, "description": self.description,
            "tags": self.tags, "constraints": self.constraints,
        }


@dataclass
class Dataset:
    id: str
    name: str
    description: str
    columns: List[ColumnSchema]
    owner: str = ""
    status: DatasetStatus = DatasetStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    lineage_sources: List[str] = field(default_factory=list)
    lineage_targets: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "owner": self.owner, "status": self.status.value,
            "created_at": self.created_at, "updated_at": self.updated_at,
            "tags": self.tags, "metadata": self.metadata,
            "columns": [c.to_dict() for c in self.columns],
            "lineage_sources": self.lineage_sources,
            "lineage_targets": self.lineage_targets,
        }


@dataclass
class SearchHit:
    dataset: Dataset
    score: float
    matched_fields: List[str]


class DataCatalogEngine:
    """
    Data catalog with schema registry, search, and lineage tracking.
    """

    def __init__(self) -> None:
        self._datasets: Dict[str, Dataset] = {}
        self._name_index: Dict[str, str] = {}  # lowercase name -> id
        self._tag_index: Dict[str, Set[str]] = {}  # tag -> set of dataset ids

    def register_dataset(self, dataset: Dataset) -> None:
        self._datasets[dataset.id] = dataset
        self._name_index[dataset.name.lower()] = dataset.id
        for tag in dataset.tags:
            self._tag_index.setdefault(tag, set()).add(dataset.id)

    def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        return self._datasets.get(dataset_id)

    def search(self, query: str, tags: Optional[List[str]] = None) -> List[SearchHit]:
        query_lower = query.lower()
        hits: List[SearchHit] = []
        for ds in self._datasets.values():
            score = 0.0
            matched: List[str] = []
            if query_lower in ds.name.lower():
                score += 10.0
                matched.append("name")
            if query_lower in ds.description.lower():
                score += 5.0
                matched.append("description")
            for col in ds.columns:
                if query_lower in col.name.lower():
                    score += 3.0
                    matched.append(f"column:{col.name}")
            if score > 0:
                hits.append(SearchHit(dataset=ds, score=score, matched_fields=matched))

        if tags:
            tag_ids = set()
            for tag in tags:
                tag_ids |= self._tag_index.get(tag, set())
            hits = [h for h in hits if h.dataset.id in tag_ids]

        hits.sort(key=lambda x: x.score, reverse=True)
        return hits

    def get_by_tag(self, tag: str) -> List[Dataset]:
        ids = self._tag_index.get(tag, set())
        return [self._datasets[i] for i in ids if i in self._datasets]

    def list_datasets(self, status: Optional[DatasetStatus] = None) -> List[Dataset]:
        datasets = list(self._datasets.values())
        if status:
            datasets = [d for d in datasets if d.status == status]
        return datasets

    def add_lineage(self, source_id: str, target_id: str) -> bool:
        if source_id not in self._datasets or target_id not in self._datasets:
            return False
        self._datasets[source_id].lineage_targets.append(target_id)
        self._datasets[target_id].lineage_sources.append(source_id)
        return True

    def get_upstream(self, dataset_id: str) -> List[Dataset]:
        ds = self._datasets.get(dataset_id)
        if not ds:
            return []
        return [self._datasets[sid] for sid in ds.lineage_sources if sid in self._datasets]

    def get_downstream(self, dataset_id: str) -> List[Dataset]:
        ds = self._datasets.get(dataset_id)
        if not ds:
            return []
        return [self._datasets[tid] for tid in ds.lineage_targets if tid in self._datasets]

    def get_schema(self, dataset_id: str) -> Optional[List[Dict[str, Any]]]:
        ds = self._datasets.get(dataset_id)
        if not ds:
            return None
        return [c.to_dict() for c in ds.columns]

    def validate_record(self, dataset_id: str, record: Dict[str, Any]) -> List[str]:
        ds = self._datasets.get(dataset_id)
        if not ds:
            return ["Dataset not found"]
        errors: List[str] = []
        col_names = {c.name for c in ds.columns}
        for key in record:
            if key not in col_names:
                errors.append(f"Unknown column: {key}")
        for col in ds.columns:
            if col.name not in record and not col.nullable:
                errors.append(f"Missing required column: {col.name}")
        return errors

    def export_catalog(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([d.to_dict() for d in self._datasets.values()], f, indent=2, default=str)

    def import_catalog(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for d in data:
            columns = [ColumnSchema(
                name=c["name"], data_type=DataType(c["data_type"]),
                nullable=c.get("nullable", True), description=c.get("description", ""),
                tags=c.get("tags", []), constraints=c.get("constraints", {}),
            ) for c in d.get("columns", [])]
            ds = Dataset(
                id=d["id"], name=d["name"], description=d.get("description", ""),
                columns=columns, owner=d.get("owner", ""),
                status=DatasetStatus(d.get("status", "active")),
                tags=d.get("tags", []), metadata=d.get("metadata", {}),
                lineage_sources=d.get("lineage_sources", []),
                lineage_targets=d.get("lineage_targets", []),
            )
            self.register_dataset(ds)

    def stats(self) -> Dict[str, Any]:
        return {
            "datasets": len(self._datasets),
            "tags": len(self._tag_index),
            "active": len([d for d in self._datasets.values() if d.status == DatasetStatus.ACTIVE]),
            "total_columns": sum(len(d.columns) for d in self._datasets.values()),
        }


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Data Catalog Engine")
    print("=" * 60)

    engine = DataCatalogEngine()

    # Register datasets
    ds1 = Dataset(
        id="customers", name="customers_v1", description="Customer demographic data",
        owner="data_team", tags=["core", "customers"],
        columns=[
            ColumnSchema("customer_id", DataType.STRING, nullable=False, description="Unique customer ID"),
            ColumnSchema("age", DataType.INTEGER, nullable=True, description="Customer age"),
            ColumnSchema("email", DataType.STRING, nullable=False, description="Contact email"),
            ColumnSchema("signup_date", DataType.TIMESTAMP, nullable=False),
        ]
    )
    ds2 = Dataset(
        id="transactions", name="transactions_v1", description="Purchase transaction records",
        owner="finance_team", tags=["core", "transactions"],
        columns=[
            ColumnSchema("transaction_id", DataType.STRING, nullable=False),
            ColumnSchema("customer_id", DataType.STRING, nullable=False),
            ColumnSchema("amount", DataType.FLOAT, nullable=False),
            ColumnSchema("timestamp", DataType.TIMESTAMP, nullable=False),
        ]
    )
    ds3 = Dataset(
        id="features", name="customer_features", description="Engineered features for ML",
        owner="ml_team", tags=["ml", "features"],
        columns=[
            ColumnSchema("customer_id", DataType.STRING, nullable=False),
            ColumnSchema("ltv_score", DataType.FLOAT, nullable=True),
            ColumnSchema("churn_risk", DataType.FLOAT, nullable=True),
        ]
    )

    for ds in [ds1, ds2, ds3]:
        engine.register_dataset(ds)

    print("\n--- Stats ---")
    print(engine.stats())

    print("\n--- Search: 'customer' ---")
    hits = engine.search("customer")
    for h in hits:
        print(f"  [{h.score:.1f}] {h.dataset.name}: matched {h.matched_fields}")

    print("\n--- By tag: 'core' ---")
    core_ds = engine.get_by_tag("core")
    for ds in core_ds:
        print(f"  {ds.name} ({ds.owner})")

    print("\n--- Lineage: customers -> features ---")
    engine.add_lineage("customers", "features")
    engine.add_lineage("transactions", "features")
    print(f"  Upstream of features: {[d.name for d in engine.get_upstream('features')]}")
    print(f"  Downstream of customers: {[d.name for d in engine.get_downstream('customers')]}")

    print("\n--- Schema validation ---")
    errors = engine.validate_record("customers", {
        "customer_id": "C123", "age": 30, "email": "test@example.com",
        "signup_date": "2023-01-01", "unknown_col": "x"
    })
    print(f"  Validation errors: {errors}")

    print("\nData Catalog test complete.")


if __name__ == "__main__":
    run()
