#!/usr/bin/env python3
"""
MAGNATRIX-OS Config Schema Native
Configuration schema validation and management.
Pure Python stdlib.
"""
import json, os, re
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field


@dataclass
class FieldSpec:
    type: type
    required: bool = True
    default: Any = None
    min: Optional[Union[int, float]] = None
    max: Optional[Union[int, float]] = None
    allowed: Optional[List[Any]] = None
    validator: Optional[Callable] = None


class ConfigSchemaNative:
    """
    Schema-based configuration validation.
    Defines expected fields, types, ranges, and custom validators.
    """

    def __init__(self, schema: Dict[str, FieldSpec] = None):
        self.schema = schema or {}
        self._errors: List[str] = []

    def validate(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate config against schema, return validated config."""
        self._errors = []
        validated = {}

        for key, spec in self.schema.items():
            value = config.get(key)
            if value is None:
                if spec.required and spec.default is None:
                    self._errors.append(f"Missing required field: {key}")
                    continue
                value = spec.default

            # Type check
            if value is not None and not isinstance(value, spec.type):
                try:
                    value = spec.type(value)
                except (ValueError, TypeError):
                    self._errors.append(f"Field '{key}': expected {spec.type.__name__}, got {type(value).__name__}")
                    continue

            # Range check
            if spec.min is not None and value < spec.min:
                self._errors.append(f"Field '{key}': value {value} < min {spec.min}")
            if spec.max is not None and value > spec.max:
                self._errors.append(f"Field '{key}': value {value} > max {spec.max}")

            # Allowed values check
            if spec.allowed is not None and value not in spec.allowed:
                self._errors.append(f"Field '{key}': value {value} not in allowed {spec.allowed}")

            # Custom validator
            if spec.validator and not spec.validator(value):
                self._errors.append(f"Field '{key}': custom validation failed")

            validated[key] = value

        # Check for unknown fields
        for key in config:
            if key not in self.schema:
                self._errors.append(f"Unknown field: {key}")

        return validated

    def is_valid(self) -> bool:
        return len(self._errors) == 0

    def errors(self) -> List[str]:
        return self._errors

    def to_json(self) -> str:
        """Serialize schema to JSON."""
        schema_dict = {}
        for key, spec in self.schema.items():
            schema_dict[key] = {
                "type": spec.type.__name__,
                "required": spec.required,
                "default": spec.default,
                "min": spec.min,
                "max": spec.max,
                "allowed": spec.allowed,
            }
        return json.dumps(schema_dict, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "ConfigSchemaNative":
        """Deserialize schema from JSON."""
        data = json.loads(json_str)
        schema = {}
        type_map = {"str": str, "int": int, "float": float, "bool": bool, "list": list, "dict": dict}
        for key, spec_data in data.items():
            schema[key] = FieldSpec(
                type=type_map.get(spec_data["type"], str),
                required=spec_data.get("required", True),
                default=spec_data.get("default"),
                min=spec_data.get("min"),
                max=spec_data.get("max"),
                allowed=spec_data.get("allowed"),
            )
        return cls(schema)


def _demo():
    print("=" * 60)
    print("MAGNATRIX-OS Config Schema Demo")
    print("=" * 60)
    schema = {
        "name": FieldSpec(str, required=True),
        "port": FieldSpec(int, default=8080, min=1, max=65535),
        "debug": FieldSpec(bool, default=False),
        "log_level": FieldSpec(str, default="INFO", allowed=["DEBUG", "INFO", "WARN", "ERROR"]),
    }
    validator = ConfigSchemaNative(schema)

    print("\n[1] Valid config:")
    valid = validator.validate({"name": "MAGNATRIX", "port": 8888, "debug": True})
    print(f"    Valid: {validator.is_valid()}, Config: {valid}")

    print("\n[2] Invalid config:")
    invalid = validator.validate({"name": "Test", "port": 99999, "log_level": "INVALID"})
    print(f"    Valid: {validator.is_valid()}, Errors: {validator.errors()}")

    print("\n[3] Schema JSON:")
    print(validator.to_json()[:200])

    print("=" * 60)


if __name__ == "__main__":
    _demo()
