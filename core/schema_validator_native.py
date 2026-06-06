#!/usr/bin/env python3
"""
Schema Validator for MAGNATRIX-OS
Data validation, type coercion, constraint checking.
Pure stdlib -- no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional, Tuple


class ValidationError:
    """Single validation error."""

    def __init__(self, field: str, message: str, value: Any) -> None:
        self.field = field
        self.message = message
        self.value = value


class SchemaValidator:
    """Data schema validator."""

    def __init__(self) -> None:
        self._fields: Dict[str, Dict[str, Any]] = {}

    def field(self, name: str, type_: type, required: bool = True, default: Any = None, 
              min_val: Optional[Any] = None, max_val: Optional[Any] = None, 
              pattern: Optional[str] = None, allowed: Optional[List[Any]] = None) -> None:
        self._fields[name] = {
            'type': type_,
            'required': required,
            'default': default,
            'min': min_val,
            'max': max_val,
            'pattern': re.compile(pattern) if pattern else None,
            'allowed': set(allowed) if allowed else None,
        }

    def validate(self, data: Dict[str, Any]) -> Tuple[bool, List[ValidationError]]:
        errors = []

        for name, rules in self._fields.items():
            value = data.get(name)

            # Check required
            if value is None and rules['required'] and rules['default'] is None:
                errors.append(ValidationError(name, 'Field is required', None))
                continue

            if value is None and rules['default'] is not None:
                data[name] = rules['default']
                value = rules['default']

            if value is None:
                continue

            # Type check
            if not isinstance(value, rules['type']):
                try:
                    data[name] = rules['type'](value)
                    value = data[name]
                except (ValueError, TypeError):
                    errors.append(ValidationError(name, f'Expected {rules["type"].__name__}, got {type(value).__name__}', value))
                    continue

            # Range check
            if rules['min'] is not None and value < rules['min']:
                errors.append(ValidationError(name, f'Minimum value is {rules["min"]}', value))

            if rules['max'] is not None and value > rules['max']:
                errors.append(ValidationError(name, f'Maximum value is {rules["max"]}', value))

            # Pattern check
            if rules['pattern'] and isinstance(value, str):
                if not rules['pattern'].match(value):
                    errors.append(ValidationError(name, f'Value does not match pattern', value))

            # Allowed values check
            if rules['allowed'] and value not in rules['allowed']:
                errors.append(ValidationError(name, f'Value not in allowed list', value))

        return len(errors) == 0, errors

    def coerce(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Coerce data to match schema."""
        self.validate(data)
        return data


def _demo() -> None:
    print("=== Schema Validator Demo ===\n")

    validator = SchemaValidator()
    validator.field('name', str, required=True, min_val=1)
    validator.field('age', int, required=True, min_val=0, max_val=150)
    validator.field('email', str, required=True, pattern=r'^[^@]+@[^@]+\.[^@]+$')
    validator.field('role', str, allowed=['admin', 'editor', 'viewer'])
    validator.field('score', float, default=0.0, min_val=0.0, max_val=100.0)

    # Valid data
    data1 = {'name': 'Alice', 'age': 30, 'email': 'alice@example.com', 'role': 'admin'}
    valid, errors = validator.validate(data1)
    print(f"Valid data: {valid}, errors: {len(errors)}")
    print(f"Coerced data: {data1}")

    # Invalid data
    data2 = {'name': '', 'age': 200, 'email': 'invalid', 'role': 'hacker'}
    valid, errors = validator.validate(data2)
    print(f"\nInvalid data: {valid}")
    for e in errors:
        print(f"  {e.field}: {e.message}")

    print("\n=== Schema Validator Demo Complete ===")


if __name__ == '__main__':
    _demo()
