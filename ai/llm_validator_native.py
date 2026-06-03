"""LLM Validator — Native Python (stdlib only)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto

class ValidationType(Enum):
    REQUIRED = auto()
    TYPE = auto()
    RANGE = auto()
    PATTERN = auto()
    LENGTH = auto()
    CUSTOM = auto()

@dataclass
class ValidationRule:
    id: str
    field: str
    validation_type: ValidationType
    params: Dict[str, Any] = field(default_factory=dict)
    message: str = ""

@dataclass
class ValidationError:
    field: str
    rule_id: str
    message: str
    value: Any = None

class Validator:
    def __init__(self) -> None:
        self._rules: List[ValidationRule] = []

    def add_rule(self, rule: ValidationRule) -> None:
        self._rules.append(rule)

    def validate(self, data: Dict[str, Any]) -> List[ValidationError]:
        errors = []
        for rule in self._rules:
            value = data.get(rule.field)
            if rule.validation_type == ValidationType.REQUIRED and (value is None or value == ""):
                errors.append(ValidationError(rule.field, rule.id, rule.message or rule.field + " is required", value))
            elif rule.validation_type == ValidationType.TYPE and value is not None:
                expected = rule.params.get("type")
                if expected and not isinstance(value, eval(expected)):
                    errors.append(ValidationError(rule.field, rule.id, rule.message or rule.field + " must be " + expected, value))
            elif rule.validation_type == ValidationType.RANGE and value is not None:
                min_v = rule.params.get("min")
                max_v = rule.params.get("max")
                if min_v is not None and value < min_v:
                    errors.append(ValidationError(rule.field, rule.id, rule.message or rule.field + " too small", value))
                if max_v is not None and value > max_v:
                    errors.append(ValidationError(rule.field, rule.id, rule.message or rule.field + " too large", value))
            elif rule.validation_type == ValidationType.PATTERN and value is not None:
                pattern = rule.params.get("pattern", "")
                if pattern and not re.match(pattern, str(value)):
                    errors.append(ValidationError(rule.field, rule.id, rule.message or rule.field + " invalid format", value))
            elif rule.validation_type == ValidationType.LENGTH and value is not None:
                min_len = rule.params.get("min", 0)
                max_len = rule.params.get("max", float('inf'))
                length = len(str(value))
                if length < min_len or length > max_len:
                    errors.append(ValidationError(rule.field, rule.id, rule.message or rule.field + " length invalid", value))
        return errors

    def is_valid(self, data: Dict[str, Any]) -> bool:
        return len(self.validate(data)) == 0

    def get_stats(self, errors: List[ValidationError]) -> Dict[str, Any]:
        counts = {}
        for err in errors:
            counts[err.field] = counts.get(err.field, 0) + 1
        return {"total_errors": len(errors), "by_field": counts}

def run() -> None:
    print("Validator test")
    e = Validator()
    e.add_rule(ValidationRule("r1", "name", ValidationType.REQUIRED, message="Name required"))
    e.add_rule(ValidationRule("r2", "age", ValidationType.RANGE, {"min": 0, "max": 150}, "Age must be 0-150"))
    e.add_rule(ValidationRule("r3", "email", ValidationType.PATTERN, {"pattern": r"^[^@]+@[^@]+\.[^@]+$"}, "Invalid email"))
    data = {"name": "Alice", "age": 30, "email": "alice@example.com"}
    errors = e.validate(data)
    print("  Valid data: " + str(e.is_valid(data)) + ", errors: " + str(len(errors)))
    bad_data = {"name": "", "age": 200, "email": "not-an-email"}
    errors = e.validate(bad_data)
    for err in errors:
        print("  Error: " + err.field + " - " + err.message)
    print("  Stats: " + str(e.get_stats(errors)))
    print("Validator test complete.")

if __name__ == "__main__":
    run()
