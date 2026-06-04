"""Schema Validator — JSON-like schema enforcement, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum, auto
import re

class SchemaType(Enum):
    STRING = auto()
    INTEGER = auto()
    NUMBER = auto()
    BOOLEAN = auto()
    ARRAY = auto()
    OBJECT = auto()
    NULL = auto()

@dataclass
class ValidationError:
    path: str
    message: str
    expected: str
    actual: Any

class SchemaValidator:
    def __init__(self, schema: Dict):
        self.schema = schema
        self.errors: List[ValidationError] = []

    def _validate_type(self, value: Any, expected: SchemaType) -> bool:
        if expected == SchemaType.STRING:
            return isinstance(value, str)
        elif expected == SchemaType.INTEGER:
            return isinstance(value, int) and not isinstance(value, bool)
        elif expected == SchemaType.NUMBER:
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        elif expected == SchemaType.BOOLEAN:
            return isinstance(value, bool)
        elif expected == SchemaType.ARRAY:
            return isinstance(value, list)
        elif expected == SchemaType.OBJECT:
            return isinstance(value, dict)
        elif expected == SchemaType.NULL:
            return value is None
        return False

    def _get_type(self, type_name: str) -> SchemaType:
        return SchemaType[type_name.upper()]

    def validate(self, data: Any, schema: Optional[Dict] = None, path: str = "") -> bool:
        schema = schema or self.schema
        self.errors = []
        self._validate(data, schema, path)
        return len(self.errors) == 0

    def _validate(self, data: Any, schema: Dict, path: str):
        if "type" in schema:
            expected = self._get_type(schema["type"]) if isinstance(schema["type"], str) else None
            if expected and not self._validate_type(data, expected):
                self.errors.append(ValidationError(path, f"Type mismatch", schema["type"], type(data).__name__))
        if "properties" in schema and isinstance(data, dict):
            for prop, prop_schema in schema["properties"].items():
                if prop not in data and schema.get("required", []).__contains__(prop):
                    self.errors.append(ValidationError(path + "." + prop, "Missing required property", "required", None))
                elif prop in data:
                    self._validate(data[prop], prop_schema, path + "." + prop)
        if "items" in schema and isinstance(data, list):
            for i, item in enumerate(data):
                self._validate(item, schema["items"], f"{path}[{i}]")
        if "minLength" in schema and isinstance(data, (str, list)) and len(data) < schema["minLength"]:
            self.errors.append(ValidationError(path, "Too short", f">= {schema['minLength']}", len(data)))
        if "maxLength" in schema and isinstance(data, (str, list)) and len(data) > schema["maxLength"]:
            self.errors.append(ValidationError(path, "Too long", f"<= {schema['maxLength']}", len(data)))
        if "pattern" in schema and isinstance(data, str) and not re.match(schema["pattern"], data):
            self.errors.append(ValidationError(path, "Pattern mismatch", schema["pattern"], data))

    def stats(self) -> Dict:
        return {"valid": len(self.errors) == 0, "errors": len(self.errors), "details": [{"path": e.path, "msg": e.message} for e in self.errors[:5]]}

def run():
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "minLength": 1},
            "age": {"type": "integer", "minimum": 0},
            "email": {"type": "string", "pattern": r"^.*@.*\..*$"},
        },
        "required": ["name", "age"]
    }
    validator = SchemaValidator(schema)
    print(validator.validate({"name": "Alice", "age": 30, "email": "a@b.com"}))
    print(validator.stats())
    print(validator.validate({"name": "", "age": -1, "email": "bad"}))
    print(validator.stats())

if __name__ == "__main__":
    run()
