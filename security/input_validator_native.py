"""security/input_validator_native.py — Input validation decorator"""
from __future__ import annotations
import re
from typing import Any, Callable, Dict, List, Optional, Union

class TypeValidator:
    def __init__(self, expected_type: type):
        self.expected_type = expected_type

    def validate(self, value: Any) -> bool:
        return isinstance(value, self.expected_type)

class RangeValidator:
    def __init__(self, min_val: Optional[float] = None, max_val: Optional[float] = None):
        self.min_val = min_val
        self.max_val = max_val

    def validate(self, value: Any) -> bool:
        if not isinstance(value, (int, float)):
            return False
        if self.min_val is not None and value < self.min_val:
            return False
        if self.max_val is not None and value > self.max_val:
            return False
        return True

class RegexValidator:
    def __init__(self, pattern: str):
        self.pattern = re.compile(pattern)

    def validate(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return bool(self.pattern.match(value))

class LengthValidator:
    def __init__(self, min_len: Optional[int] = None, max_len: Optional[int] = None):
        self.min_len = min_len
        self.max_len = max_len

    def validate(self, value: Any) -> bool:
        if not hasattr(value, '__len__'):
            return False
        length = len(value)
        if self.min_len is not None and length < self.min_len:
            return False
        if self.max_len is not None and length > self.max_len:
            return False
        return True

class EmailValidator:
    PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    def validate(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return bool(self.PATTERN.match(value))

class URLValidator:
    PATTERN = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)

    def validate(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return bool(self.PATTERN.match(value))

class SchemaValidator:
    def __init__(self, schema: Dict[str, Any]):
        self.schema = schema

    def validate(self, data: Dict[str, Any]) -> bool:
        for key, validator in self.schema.items():
            if key not in data:
                return False
            if not validator.validate(data[key]):
                return False
        return True

class InputValidator:
    """Main input validation class with decorator support."""

    @staticmethod
    def validate(schema: Dict[str, Any]) -> Callable:
        """Decorator for input validation."""
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                for key, validator in schema.items():
                    value = kwargs.get(key)
                    if value is not None and not validator.validate(value):
                        raise ValueError(f"Validation failed for {key}: {value}")
                return func(*args, **kwargs)
            return wrapper
        return decorator

if __name__ == "__main__":
    print("InputValidator self-test")
    tv = TypeValidator(str)
    assert tv.validate("hello")
    assert not tv.validate(123)

    rv = RangeValidator(0, 100)
    assert rv.validate(50)
    assert not rv.validate(150)

    ev = EmailValidator()
    assert ev.validate("test@example.com")
    assert not ev.validate("invalid")

    print("All tests pass")
