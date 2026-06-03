"""
llm_schema_registry_native.py
MAGNATRIX-OS Schema Registry Engine
Native Python, stdlib only.
Provides schema registration, versioning, compatibility checking, evolution tracking,
and validation for data contracts between MAGNATRIX-OS services and pipelines.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class CompatibilityMode(Enum):
    BACKWARD = "backward"
    FORWARD = "forward"
    FULL = "full"
    NONE = "none"


class SchemaType(Enum):
    JSON = "json"
    AVRO = "avro"
    PROTOBUF = "protobuf"
    CUSTOM = "custom"


@dataclass
class SchemaField:
    name: str
    field_type: str
    required: bool = True
    default: Any = None
    description: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "type": self.field_type, "required": self.required,
            "default": self.default, "description": self.description, "tags": self.tags,
        }


@dataclass
class SchemaVersion:
    version: str
    schema_id: str
    fields: List[SchemaField]
    compatibility: CompatibilityMode = CompatibilityMode.BACKWARD
    schema_type: SchemaType = SchemaType.JSON
    created_at: float = field(default_factory=time.time)
    created_by: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version, "schema_id": self.schema_id,
            "fields": [f.to_dict() for f in self.fields],
            "compatibility": self.compatibility.value,
            "schema_type": self.schema_type.value,
            "created_at": self.created_at, "created_by": self.created_by,
            "description": self.description, "metadata": self.metadata,
        }

    def get_field_names(self) -> Set[str]:
        return {f.name for f in self.fields}

    def get_required_fields(self) -> Set[str]:
        return {f.name for f in self.fields if f.required}


class SchemaRegistryEngine:
    """
    Schema registry with versioning, compatibility checking, and validation.
    """

    def __init__(self) -> None:
        self._schemas: Dict[str, List[SchemaVersion]] = {}  # schema_id -> versions
        self._latest: Dict[str, str] = {}  # schema_id -> latest version
        self._subjects: Dict[str, str] = {}  # subject -> schema_id mapping
        self._validators: Dict[str, Callable[[Dict[str, Any]], bool]] = {}

    def register_schema(self, schema_version: SchemaVersion) -> bool:
        sid = schema_version.schema_id
        if sid not in self._schemas:
            self._schemas[sid] = []
        else:
            # Check compatibility with latest
            latest = self._get_latest_version(sid)
            if latest:
                compat = self._check_compatibility(latest, schema_version)
                if not compat:
                    return False
        self._schemas[sid].append(schema_version)
        self._schemas[sid].sort(key=lambda v: v.created_at)
        self._latest[sid] = schema_version.version
        return True

    def _get_latest_version(self, schema_id: str) -> Optional[SchemaVersion]:
        versions = self._schemas.get(schema_id, [])
        if not versions:
            return None
        return versions[-1]

    def _check_compatibility(self, old: SchemaVersion, new: SchemaVersion) -> bool:
        if new.compatibility == CompatibilityMode.NONE:
            return True

        old_fields = {f.name: f for f in old.fields}
        new_fields = {f.name: f for f in new.fields}

        if new.compatibility == CompatibilityMode.BACKWARD:
            # Old readers can read new data: new can only add optional fields
            for name, field in new_fields.items():
                if name not in old_fields and field.required:
                    return False
            return True

        elif new.compatibility == CompatibilityMode.FORWARD:
            # New readers can read old data: can't remove required fields
            for name, field in old_fields.items():
                if name not in new_fields and field.required:
                    return False
            return True

        elif new.compatibility == CompatibilityMode.FULL:
            # Both backward and forward
            return self._check_compatibility(old, new) and self._check_compatibility_forward(old, new)

        return True

    def _check_compatibility_forward(self, old: SchemaVersion, new: SchemaVersion) -> bool:
        old_fields = {f.name: f for f in old.fields}
        new_fields = {f.name: f for f in new.fields}
        for name, field in old_fields.items():
            if name not in new_fields and field.required:
                return False
        return True

    def get_schema(self, schema_id: str, version: Optional[str] = None) -> Optional[SchemaVersion]:
        versions = self._schemas.get(schema_id, [])
        if not version:
            return self._get_latest_version(schema_id)
        for v in versions:
            if v.version == version:
                return v
        return None

    def get_versions(self, schema_id: str) -> List[SchemaVersion]:
        return list(self._schemas.get(schema_id, []))

    def validate(self, schema_id: str, data: Dict[str, Any], version: Optional[str] = None) -> List[str]:
        schema = self.get_schema(schema_id, version)
        if not schema:
            return [f"Schema {schema_id} not found"]
        errors = []
        field_dict = {f.name: f for f in schema.fields}
        # Check required fields
        for name, field in field_dict.items():
            if field.required and name not in data:
                errors.append(f"Missing required field: {name}")
        # Check unknown fields
        for key in data:
            if key not in field_dict:
                errors.append(f"Unknown field: {key}")
        # Check custom validators
        for name, validator in self._validators.items():
            if name in data and not validator(data[name]):
                errors.append(f"Validation failed for field: {name}")
        return errors

    def add_validator(self, field_name: str, validator: Callable[[Any], bool]) -> None:
        self._validators[field_name] = validator

    def evolve(self, schema_id: str, new_fields: List[SchemaField], description: str = "",
               compatibility: CompatibilityMode = CompatibilityMode.BACKWARD,
               created_by: str = "") -> Optional[SchemaVersion]:
        latest = self._get_latest_version(schema_id)
        if not latest:
            return None
        new_version_str = self._bump_version(latest.version)
        sv = SchemaVersion(
            version=new_version_str, schema_id=schema_id, fields=latest.fields + new_fields,
            compatibility=compatibility, created_by=created_by, description=description,
        )
        if self.register_schema(sv):
            return sv
        return None

    def _bump_version(self, version: str) -> str:
        parts = version.split(".")
        if len(parts) == 3:
            return f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"
        return f"{version}.1"

    def compare_versions(self, schema_id: str, v1: str, v2: str) -> Dict[str, Any]:
        sv1 = self.get_schema(schema_id, v1)
        sv2 = self.get_schema(schema_id, v2)
        if not sv1 or not sv2:
            return {"error": "Version not found"}
        f1 = {f.name: f for f in sv1.fields}
        f2 = {f.name: f for f in sv2.fields}
        added = [k for k in f2 if k not in f1]
        removed = [k for k in f1 if k not in f2]
        changed = []
        for k in f1:
            if k in f2 and f1[k].field_type != f2[k].field_type:
                changed.append({"name": k, "old": f1[k].field_type, "new": f2[k].field_type})
        return {"added": added, "removed": removed, "changed": changed}

    def list_schemas(self) -> List[str]:
        return list(self._schemas.keys())

    def get_stats(self, schema_id: Optional[str] = None) -> Dict[str, Any]:
        if schema_id:
            versions = self._schemas.get(schema_id, [])
            return {
                "schema_id": schema_id,
                "versions": len(versions),
                "latest": self._latest.get(schema_id),
                "fields_latest": len(versions[-1].fields) if versions else 0,
            }
        return {
            "schemas": len(self._schemas),
            "total_versions": sum(len(v) for v in self._schemas.values()),
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({k: [v.to_dict() for v in versions] for k, versions in self._schemas.items()}, f, indent=2, default=str)

    def import_schemas(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for sid, versions in data.items():
            for vd in versions:
                fields = [SchemaField(
                    name=f["name"], field_type=f["type"], required=f.get("required", True),
                    default=f.get("default"), description=f.get("description", ""), tags=f.get("tags", [])
                ) for f in vd.get("fields", [])]
                sv = SchemaVersion(
                    version=vd["version"], schema_id=vd["schema_id"], fields=fields,
                    compatibility=CompatibilityMode(vd.get("compatibility", "backward")),
                    schema_type=SchemaType(vd.get("schema_type", "json")),
                    created_by=vd.get("created_by", ""), description=vd.get("description", ""),
                    metadata=vd.get("metadata", {}),
                )
                self.register_schema(sv)


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Schema Registry Engine")
    print("=" * 60)

    engine = SchemaRegistryEngine()

    # Register initial schema
    v1 = SchemaVersion(
        version="1.0.0", schema_id="customer_event",
        fields=[
            SchemaField("customer_id", "string", required=True),
            SchemaField("event_type", "string", required=True),
            SchemaField("timestamp", "string", required=True),
            SchemaField("value", "float", required=False, default=0.0),
        ],
        compatibility=CompatibilityMode.BACKWARD, created_by="user_a"
    )
    engine.register_schema(v1)
    print("Registered v1.0.0")

    # Evolve: add optional field
    v2 = SchemaVersion(
        version="1.1.0", schema_id="customer_event",
        fields=[
            SchemaField("customer_id", "string", required=True),
            SchemaField("event_type", "string", required=True),
            SchemaField("timestamp", "string", required=True),
            SchemaField("value", "float", required=False, default=0.0),
            SchemaField("metadata", "object", required=False, default={}),
        ],
        compatibility=CompatibilityMode.BACKWARD, created_by="user_b"
    )
    ok = engine.register_schema(v2)
    print(f"Registered v1.1.0 (backward compatible): {ok}")

    # Try to add required field (should fail backward compat)
    v3 = SchemaVersion(
        version="2.0.0", schema_id="customer_event",
        fields=[
            SchemaField("customer_id", "string", required=True),
            SchemaField("event_type", "string", required=True),
            SchemaField("timestamp", "string", required=True),
            SchemaField("value", "float", required=False, default=0.0),
            SchemaField("metadata", "object", required=False, default={}),
            SchemaField("session_id", "string", required=True),  # Required new field
        ],
        compatibility=CompatibilityMode.BACKWARD, created_by="user_c"
    )
    ok = engine.register_schema(v3)
    print(f"Registered v2.0.0 (should fail backward compat): {ok}")

    print("\n--- Validate data ---")
    data = {"customer_id": "C123", "event_type": "click", "timestamp": "2024-01-01T00:00:00Z"}
    errors = engine.validate("customer_event", data)
    print(f"  Validation errors: {errors}")

    data_bad = {"customer_id": "C123", "timestamp": "2024-01-01T00:00:00Z"}
    errors = engine.validate("customer_event", data_bad)
    print(f"  Validation errors (missing event_type): {errors}")

    print("\n--- Compare versions ---")
    diff = engine.compare_versions("customer_event", "1.0.0", "1.1.0")
    print(f"  Added: {diff['added']}")
    print(f"  Removed: {diff['removed']}")
    print(f"  Changed: {diff['changed']}")

    print("\n--- Stats ---")
    print(engine.get_stats())
    print(engine.get_stats("customer_event"))

    print("\nSchema Registry test complete.")


if __name__ == "__main__":
    run()
