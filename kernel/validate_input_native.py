
"""
kernel/validate_input_native.py — MAGNATRIX-OS Input Validation Decorator System

Provides decorators and validators for function input validation.
Pure Python, stdlib only. Zero dependencies.

Usage:
    @validate_input(
        user_id=TypeValidator(int),
        email=[RegexValidator(r"^[^@]+@[^@]+$"), LengthValidator(5, 254)],
        age=RangeValidator(0, 150),
        role=ChoiceValidator(["admin", "user", "guest"]),
    )
    def create_user(user_id, email, age, role="guest"):
        ...

Components:
    • validate_input — decorator factory
    • InputValidator — base validator class
    • TypeValidator — Python type check
    • RangeValidator — numeric range
    • RegexValidator — pattern matching
    • LengthValidator — min/max length
    • ChoiceValidator — enum/choice validation
    • SchemaValidator — nested dict schema
    • Sanitizer — input sanitization
    • ValidationError — custom exception
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union


# ════════════════════════════════════════════════════════════════════════════
# ValidationError
# ════════════════════════════════════════════════════════════════════════════

class ValidationError(Exception):
    """Raised when input validation fails."""

    def __init__(
        self,
        field: str,
        value: Any,
        expected: str,
        actual_error: Optional[str] = None,
    ):
        self.field = field
        self.value = value
        self.expected = expected
        self.actual_error = actual_error
        msg = f"Validation failed for '{field}': expected {expected}, got {repr(value)[:100]}"
        if actual_error:
            msg += f" ({actual_error})"
        super().__init__(msg)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "value": repr(self.value)[:100],
            "expected": self.expected,
            "error": self.actual_error,
        }


class ValidationSummary(Exception):
    """Multiple validation errors collected."""

    def __init__(self, errors: List[ValidationError]):
        self.errors = errors
        lines = [f"  - {e.field}: {e.expected}" for e in errors]
        super().__init__("Multiple validation errors:\n" + "\n".join(lines))


# ════════════════════════════════════════════════════════════════════════════
# Sanitizer
# ════════════════════════════════════════════════════════════════════════════

class Sanitizer:
    """Input sanitization utilities."""

    @staticmethod
    def strip(value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value

    @staticmethod
    def lower(value: Any) -> Any:
        if isinstance(value, str):
            return value.lower()
        return value

    @staticmethod
    def upper(value: Any) -> Any:
        if isinstance(value, str):
            return value.upper()
        return value

    @staticmethod
    def escape_html(value: Any) -> Any:
        if isinstance(value, str):
            return (
                value.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
            )
        return value

    @staticmethod
    def truncate(value: Any, max_len: int, suffix: str = "...") -> Any:
        if isinstance(value, str) and len(value) > max_len:
            return value[: max_len - len(suffix)] + suffix
        return value

    @staticmethod
    def remove_control_chars(value: Any) -> Any:
        if isinstance(value, str):
            return "".join(ch for ch in value if ord(ch) >= 32 or ch in "\n\r\t")
        return value


# ════════════════════════════════════════════════════════════════════════════
# InputValidator (base)
# ════════════════════════════════════════════════════════════════════════════

class InputValidator(ABC):
    """Base class for all validators."""

    @abstractmethod
    def validate(self, field: str, value: Any) -> None:
        """Validate value. Raise ValidationError if invalid."""
        pass

    def __and__(self, other: InputValidator) -> ChainValidator:
        return ChainValidator([self, other])


class ChainValidator(InputValidator):
    """Chain multiple validators together."""

    def __init__(self, validators: List[InputValidator]):
        self.validators = validators

    def validate(self, field: str, value: Any) -> None:
        errors = []
        for v in self.validators:
            try:
                v.validate(field, value)
            except ValidationError as e:
                errors.append(e)
        if errors:
            raise ValidationSummary(errors)


# ════════════════════════════════════════════════════════════════════════════
# Concrete Validators
# ════════════════════════════════════════════════════════════════════════════

class TypeValidator(InputValidator):
    """Validate Python type."""

    def __init__(self, expected_type: Type, allow_none: bool = False):
        self.expected_type = expected_type
        self.allow_none = allow_none

    def validate(self, field: str, value: Any) -> None:
        if value is None and self.allow_none:
            return
        if not isinstance(value, self.expected_type):
            raise ValidationError(
                field, value,
                f"type {self.expected_type.__name__}",
                f"actual type {type(value).__name__}"
            )


class RangeValidator(InputValidator):
    """Validate numeric range."""

    def __init__(
        self,
        min_val: Optional[Union[int, float]] = None,
        max_val: Optional[Union[int, float]] = None,
    ):
        self.min_val = min_val
        self.max_val = max_val

    def validate(self, field: str, value: Any) -> None:
        if not isinstance(value, (int, float)):
            raise ValidationError(field, value, "numeric value")
        if self.min_val is not None and value < self.min_val:
            raise ValidationError(
                field, value,
                f"value >= {self.min_val}",
                f"got {value}"
            )
        if self.max_val is not None and value > self.max_val:
            raise ValidationError(
                field, value,
                f"value <= {self.max_val}",
                f"got {value}"
            )


class RegexValidator(InputValidator):
    """Validate string against regex pattern."""

    def __init__(self, pattern: str, flags: int = 0):
        self.pattern = re.compile(pattern, flags)
        self.pattern_str = pattern

    def validate(self, field: str, value: Any) -> None:
        if not isinstance(value, str):
            raise ValidationError(field, value, "string")
        if not self.pattern.match(value):
            raise ValidationError(
                field, value,
                f"match pattern {self.pattern_str}",
            )


class LengthValidator(InputValidator):
    """Validate string/list/dict length."""

    def __init__(
        self,
        min_len: Optional[int] = None,
        max_len: Optional[int] = None,
    ):
        self.min_len = min_len
        self.max_len = max_len

    def validate(self, field: str, value: Any) -> None:
        if not hasattr(value, "__len__"):
            raise ValidationError(field, value, "sized object")
        length = len(value)
        if self.min_len is not None and length < self.min_len:
            raise ValidationError(
                field, value,
                f"length >= {self.min_len}",
                f"got length {length}"
            )
        if self.max_len is not None and length > self.max_len:
            raise ValidationError(
                field, value,
                f"length <= {self.max_len}",
                f"got length {length}"
            )


class ChoiceValidator(InputValidator):
    """Validate value is one of allowed choices."""

    def __init__(self, choices: List[Any], case_sensitive: bool = True):
        self.choices = choices
        self.case_sensitive = case_sensitive

    def validate(self, field: str, value: Any) -> None:
        if not self.case_sensitive and isinstance(value, str):
            valid = value.lower() in [str(c).lower() for c in self.choices]
        else:
            valid = value in self.choices
        if not valid:
            raise ValidationError(
                field, value,
                f"one of {self.choices}",
            )


class SchemaValidator(InputValidator):
    """Validate nested dict schema."""

    def __init__(self, schema: Dict[str, InputValidator], required: Optional[List[str]] = None):
        self.schema = schema
        self.required = required or list(schema.keys())

    def validate(self, field: str, value: Any) -> None:
        if not isinstance(value, dict):
            raise ValidationError(field, value, "dict")

        errors = []
        for key in self.required:
            if key not in value:
                errors.append(ValidationError(
                    f"{field}.{key}", None,
                    f"required key '{key}'"
                ))

        for key, validator in self.schema.items():
            if key in value:
                v_list = validator if isinstance(validator, list) else [validator]
                for v in v_list:
                    try:
                        v.validate(f"{field}.{key}", value[key])
                    except (ValidationError, ValidationSummary) as e:
                        if isinstance(e, ValidationSummary):
                            errors.extend(e.errors)
                        else:
                            errors.append(e)

        if errors:
            raise ValidationSummary(errors)


class EmailValidator(InputValidator):
    """Validate email address format."""

    def __init__(self, domains: Optional[List[str]] = None):
        self.domains = domains
        self.pattern = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    def validate(self, field: str, value: Any) -> None:
        if not isinstance(value, str):
            raise ValidationError(field, value, "string email")
        if not self.pattern.match(value):
            raise ValidationError(field, value, "valid email format")
        if self.domains:
            domain = value.split("@")[-1].lower()
            if domain not in [d.lower() for d in self.domains]:
                raise ValidationError(
                    field, value,
                    f"email from domain in {self.domains}",
                )


class URLValidator(InputValidator):
    """Validate URL format."""

    def __init__(self, schemes: Optional[List[str]] = None):
        self.schemes = schemes or ["http", "https"]
        self.pattern = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")

    def validate(self, field: str, value: Any) -> None:
        if not isinstance(value, str):
            raise ValidationError(field, value, "string URL")
        if not self.pattern.match(value):
            raise ValidationError(field, value, f"URL with scheme in {self.schemes}")
        scheme = value.split("://")[0].lower()
        if scheme not in [s.lower() for s in self.schemes]:
            raise ValidationError(field, value, f"URL scheme in {self.schemes}")


# ════════════════════════════════════════════════════════════════════════════
# validate_input decorator
# ════════════════════════════════════════════════════════════════════════════

def validate_input(
    _func: Optional[Callable] = None,
    **validators: Union[InputValidator, List[InputValidator]]
) -> Callable:
    """
    Decorator for input validation.

    Usage:
        @validate_input(user_id=TypeValidator(int), name=LengthValidator(1, 100))
        def process(user_id, name):
            ...

    Supports chained validators:
        @validate_input(email=[RegexValidator(r"...@..."), LengthValidator(5, 254)])
        def send_email(email):
            ...
    """
    def decorator(func: Callable) -> Callable:
        import inspect
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())

        def wrapper(*args, **kwargs) -> Any:
            # Build argument mapping
            bound: Dict[str, Any] = {}
            for i, arg in enumerate(args):
                if i < len(params):
                    bound[params[i]] = arg
            bound.update(kwargs)

            errors: List[ValidationError] = []

            for field, validator in validators.items():
                if field not in bound:
                    continue  # Skip missing optional fields

                value = bound[field]

                # Sanitize first
                value = Sanitizer.strip(value)
                value = Sanitizer.remove_control_chars(value)

                # Validate
                v_list = validator if isinstance(validator, list) else [validator]
                for v in v_list:
                    try:
                        v.validate(field, value)
                    except (ValidationError, ValidationSummary) as e:
                        if isinstance(e, ValidationSummary):
                            errors.extend(e.errors)
                        else:
                            errors.append(e)

            if errors:
                raise ValidationSummary(errors)

            return func(*args, **kwargs)

        wrapper._validators = validators
        wrapper._original = func
        return wrapper

    if _func is not None:
        return decorator(_func)
    return decorator


# ════════════════════════════════════════════════════════════════════════════
# ValidationResult helper
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class ValidationResult:
    valid: bool
    errors: List[ValidationError] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


def validate_dict(data: Dict[str, Any], schema: Dict[str, Any]) -> ValidationResult:
    """
    Validate a dict against a schema without decorator.

    schema: {field_name: validator or [validators]}
    """
    errors = []
    for field, validator in schema.items():
        if field not in data:
            errors.append(ValidationError(field, None, "required field"))
            continue
        value = Sanitizer.strip(data[field])
        value = Sanitizer.remove_control_chars(value)
        v_list = validator if isinstance(validator, list) else [validator]
        for v in v_list:
            try:
                v.validate(field, value)
            except (ValidationError, ValidationSummary) as e:
                if isinstance(e, ValidationSummary):
                    errors.extend(e.errors)
                else:
                    errors.append(e)
    return ValidationResult(len(errors) == 0, errors)


# ════════════════════════════════════════════════════════════════════════════
# DEMO / SELF-TEST
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Input Validation System — Self-Test")
    print("=" * 60)

    # Test 1: Type validation
    print("\n[1] TypeValidator")
    v = TypeValidator(int)
    v.validate("age", 25)  # OK
    try:
        v.validate("age", "twenty-five")
        assert False, "Should have raised"
    except ValidationError as e:
        print(f"  ✓ Caught: {e}")

    # Test 2: Range validation
    print("\n[2] RangeValidator")
    v = RangeValidator(0, 150)
    v.validate("age", 25)
    try:
        v.validate("age", 200)
        assert False
    except ValidationError as e:
        print(f"  ✓ Caught: {e}")

    # Test 3: Regex validation
    print("\n[3] RegexValidator")
    v = RegexValidator(r"^[a-z0-9_]+$", flags=re.IGNORECASE)
    v.validate("username", "user_123")
    try:
        v.validate("username", "user-123")
        assert False
    except ValidationError as e:
        print(f"  ✓ Caught: {e}")

    # Test 4: Length validation
    print("\n[4] LengthValidator")
    v = LengthValidator(3, 20)
    v.validate("password", "secure123")
    try:
        v.validate("password", "ab")
        assert False
    except ValidationError as e:
        print(f"  ✓ Caught: {e}")

    # Test 5: Choice validation
    print("\n[5] ChoiceValidator")
    v = ChoiceValidator(["admin", "user", "guest"])
    v.validate("role", "admin")
    try:
        v.validate("role", "superuser")
        assert False
    except ValidationError as e:
        print(f"  ✓ Caught: {e}")

    # Test 6: Schema validation
    print("\n[6] SchemaValidator")
    schema = SchemaValidator({
        "name": LengthValidator(1, 50),
        "age": RangeValidator(0, 150),
        "email": [RegexValidator(r"^[^@]+@[^@]+$"), LengthValidator(5, 254)],
    }, required=["name", "age"])
    schema.validate("user", {"name": "Alice", "age": 30, "email": "alice@test.com"})
    try:
        schema.validate("user", {"age": 30})
        assert False
    except ValidationSummary as e:
        print(f"  ✓ Caught missing field: {len(e.errors)} errors")

    # Test 7: Email validator
    print("\n[7] EmailValidator")
    v = EmailValidator(domains=["test.com", "example.com"])
    v.validate("email", "user@test.com")
    try:
        v.validate("email", "user@bad.com")
        assert False
    except ValidationError as e:
        print(f"  ✓ Caught: {e}")

    # Test 8: Decorator
    print("\n[8] @validate_input decorator")
    @validate_input(
        user_id=TypeValidator(int),
        name=[LengthValidator(1, 50), RegexValidator(r"^[A-Za-z ]+$")],
        age=RangeValidator(0, 150),
        role=ChoiceValidator(["admin", "user"], case_sensitive=False),
    )
    def create_user(user_id, name, age, role="user"):
        return {"id": user_id, "name": name, "age": age, "role": role}

    result = create_user(1, "Alice Smith", 30, "ADMIN")
    print(f"  ✓ Valid call: {result}")
    try:
        create_user("abc", "Alice", 30)
        assert False
    except ValidationSummary as e:
        print(f"  ✓ Caught {len(e.errors)} errors in invalid call")

    # Test 9: validate_dict helper
    print("\n[9] validate_dict helper")
    result = validate_dict(
        {"name": "Bob", "age": 25},
        {"name": LengthValidator(1, 50), "age": RangeValidator(0, 150)}
    )
    print(f"  ✓ Dict validation: valid={result.valid}, errors={len(result.errors)}")

    # Test 10: URL validator
    print("\n[10] URLValidator")
    v = URLValidator(["https"])
    v.validate("url", "https://example.com")
    try:
        v.validate("url", "ftp://example.com")
        assert False
    except ValidationError as e:
        print(f"  ✓ Caught: {e}")

    print("\n" + "=" * 60)
    print("All self-tests passed ✓")
    print("=" * 60)
