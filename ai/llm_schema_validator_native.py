"""LLM Schema Validator — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class SchemaType(Enum):
    STRING = auto()
    INTEGER = auto()
    NUMBER = auto()
    BOOLEAN = auto()
    ARRAY = auto()
    OBJECT = auto()
    NULL = auto()

@dataclass
class SchemaField:
    name: str
    field_type: SchemaType
    required: bool = True
    default: Any = None
    pattern: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class SchemaValidator:
    def __init__(self) -> None:
        self._fields: Dict[str, SchemaField] = {}

    def add_field(self, field: SchemaField) -> None:
        self._fields[field.name] = field

    def validate(self, data: Dict[str, Any]) -> List[str]:
        errors = []
        for name, field in self._fields.items():
            value = data.get(name)
            if value is None and field.required:
                errors.append(name + " is required")
                continue
            if value is None:
                continue
            if field.field_type == SchemaType.STRING and not isinstance(value, str):
                errors.append(name + " must be string")
            elif field.field_type == SchemaType.INTEGER and not isinstance(value, int):
                errors.append(name + " must be integer")
            elif field.field_type == SchemaType.NUMBER and not isinstance(value, (int, float)):
                errors.append(name + " must be number")
            elif field.field_type == SchemaType.BOOLEAN and not isinstance(value, bool):
                errors.append(name + " must be boolean")
            elif field.field_type == SchemaType.ARRAY and not isinstance(value, list):
                errors.append(name + " must be array")
            elif field.field_type == SchemaType.OBJECT and not isinstance(value, dict):
                errors.append(name + " must be object")
        for key in data:
            if key not in self._fields:
                errors.append("Unknown field: " + key)
        return errors

    def is_valid(self, data: Dict[str, Any]) -> bool:
        return len(self.validate(data)) == 0

    def get_stats(self) -> Dict[str, Any]:
        return {"fields": len(self._fields), "required": sum(1 for f in self._fields.values() if f.required)}

def run() -> None:
    print("Schema Validator test")
    e = SchemaValidator()
    e.add_field(SchemaField("name", SchemaType.STRING, True))
    e.add_field(SchemaField("age", SchemaType.INTEGER, True))
    e.add_field(SchemaField("email", SchemaType.STRING, False))
    data = {"name": "Alice", "age": 30}
    print("  Valid: " + str(e.is_valid(data)) + ", errors: " + str(e.validate(data)))
    bad = {"name": "Bob", "age": "thirty"}
    print("  Invalid: " + str(e.is_valid(bad)) + ", errors: " + str(e.validate(bad)))
    print("  Stats: " + str(e.get_stats()))
    print("Schema Validator test complete.")

if __name__ == "__main__":
    run()
