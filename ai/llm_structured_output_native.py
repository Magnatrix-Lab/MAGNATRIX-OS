"""
llm_structured_output_native.py
MAGNATRIX-OS Structured Output Engine
Native Python, stdlib only.
Provides structured output generation with schema enforcement, JSON mode, and type validation.
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

class StructuredOutputEngine:
    def __init__(self) -> None:
        self._schemas: Dict[str, Dict[str, type]] = {}

    def register_schema(self, name: str, schema: Dict[str, type]) -> None:
        self._schemas[name] = schema

    def validate(self, schema_name: str, data: Dict[str, Any]) -> List[str]:
        schema = self._schemas.get(schema_name)
        if not schema:
            return ["Schema not found"]
        errors = []
        for key, expected_type in schema.items():
            if key not in data:
                errors.append(f"Missing field: {key}")
            elif not isinstance(data[key], expected_type):
                errors.append(f"Type mismatch for {key}: expected {expected_type.__name__}, got {type(data[key]).__name__}")
        for key in data:
            if key not in schema:
                errors.append(f"Unknown field: {key}")
        return errors

    def parse_json(self, text: str, schema_name: Optional[str] = None) -> Dict[str, Any]:
        try:
            data = json.loads(text)
            if schema_name:
                errors = self.validate(schema_name, data)
                if errors:
                    return {"data": data, "errors": errors, "valid": False}
            return {"data": data, "valid": True}
        except json.JSONDecodeError as e:
            return {"error": str(e), "valid": False}

    def format_output(self, data: Dict[str, Any], format: str = "json") -> str:
        if format == "json":
            return json.dumps(data, indent=2)
        elif format == "yaml":
            lines = []
            for k, v in data.items():
                lines.append(f"{k}: {v}")
            return "\n".join(lines)
        return str(data)

    def get_stats(self) -> Dict[str, Any]:
        return {"schemas": len(self._schemas)}

def run() -> None:
    print("=" * 60); print("MAGNATRIX-OS Structured Output"); print("=" * 60)
    e = StructuredOutputEngine()
    e.register_schema("person", {"name": str, "age": int, "email": str})
    data = {"name": "Alice", "age": 30, "email": "alice@example.com"}
    print(f"  Validation: {e.validate('person', data)}")
    bad_data = {"name": "Bob", "age": "thirty"}
    print(f"  Validation errors: {e.validate('person', bad_data)}")
    result = e.parse_json('{"name":"Charlie","age":25}', "person")
    print(f"  Parse result: {result}")
    print("\nStructured Output test complete.")
if __name__ == "__main__": run()
