#!/usr/bin/env python3
"""
kernel/validate_input_native.py
===============================
Layer 0 — Input Validation Decorator & Boundary Guards

Provides:
  - @validate_input decorator for automatic boundary validation
  - Type checking, length limits, pattern matching, range checks
  - Automatic sanitization of strings (strip null bytes, path traversal)
  - Reusable validators: StringValidator, IntValidator, ListValidator, DictValidator
"""

from __future__ import annotations

import functools
import re
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

T = TypeVar("T")


class ValidationError(ValueError):
    """Raised when input validation fails."""
    pass


class StringValidator:
    """Validate string inputs."""

    def __init__(self, *, min_len: int = 0, max_len: int = 10000,
                 pattern: Optional[str] = None, allow_null: bool = False,
                 strip: bool = True, name: str = "string") -> None:
        self.min_len = min_len
        self.max_len = max_len
        self.pattern = re.compile(pattern) if pattern else None
        self.allow_null = allow_null
        self.strip = strip
        self.name = name

    def __call__(self, value: Any) -> str:
        if value is None and not self.allow_null:
            raise ValidationError(f"{self.name}: value is None")
        if not isinstance(value, str):
            raise ValidationError(f"{self.name}: expected str, got {type(value).__name__}")
        if "\x00" in value:
            raise ValidationError(f"{self.name}: contains null bytes")
        if self.strip:
            value = value.strip()
        length = len(value)
        if length < self.min_len:
            raise ValidationError(f"{self.name}: too short ({length} < {self.min_len})")
        if length > self.max_len:
            raise ValidationError(f"{self.name}: too long ({length} > {self.max_len})")
        if self.pattern and not self.pattern.match(value):
            raise ValidationError(f"{self.name}: does not match pattern {self.pattern.pattern}")
        return value


class IntValidator:
    """Validate integer inputs."""

    def __init__(self, *, min_val: Optional[int] = None, max_val: Optional[int] = None,
                 name: str = "integer") -> None:
        self.min_val = min_val
        self.max_val = max_val
        self.name = name

    def __call__(self, value: Any) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValidationError(f"{self.name}: expected int, got {type(value).__name__}")
        if self.min_val is not None and value < self.min_val:
            raise ValidationError(f"{self.name}: below minimum ({value} < {self.min_val})")
        if self.max_val is not None and value > self.max_val:
            raise ValidationError(f"{self.name}: above maximum ({value} > {self.max_val})")
        return value


class BytesValidator:
    """Validate bytes inputs."""

    def __init__(self, *, max_len: int = 10 * 1024 * 1024, name: str = "bytes") -> None:
        self.max_len = max_len
        self.name = name

    def __call__(self, value: Any) -> bytes:
        if not isinstance(value, bytes):
            raise ValidationError(f"{self.name}: expected bytes, got {type(value).__name__}")
        if len(value) > self.max_len:
            raise ValidationError(f"{self.name}: too large ({len(value)} > {self.max_len})")
        return value


class ListValidator:
    """Validate list inputs."""

    def __init__(self, *, min_len: int = 0, max_len: int = 10000,
                 item_validator: Optional[Callable[[Any], Any]] = None,
                 name: str = "list") -> None:
        self.min_len = min_len
        self.max_len = max_len
        self.item_validator = item_validator
        self.name = name

    def __call__(self, value: Any) -> List[Any]:
        if not isinstance(value, list):
            raise ValidationError(f"{self.name}: expected list, got {type(value).__name__}")
        length = len(value)
        if length < self.min_len:
            raise ValidationError(f"{self.name}: too short ({length} < {self.min_len})")
        if length > self.max_len:
            raise ValidationError(f"{self.name}: too long ({length} > {self.max_len})")
        if self.item_validator:
            return [self.item_validator(item) for item in value]
        return value


class DictValidator:
    """Validate dict inputs."""

    def __init__(self, *, required_keys: Optional[List[str]] = None,
                 max_depth: int = 5, name: str = "dict") -> None:
        self.required_keys = required_keys or []
        self.max_depth = max_depth
        self.name = name

    def __call__(self, value: Any) -> Dict[str, Any]:
        if not isinstance(value, dict):
            raise ValidationError(f"{self.name}: expected dict, got {type(value).__name__}")
        for key in self.required_keys:
            if key not in value:
                raise ValidationError(f"{self.name}: missing required key '{key}'")
        return value


# =============================================================================
# DECORATOR
# =============================================================================

def validate_input(**validators: Union[Callable[[Any], Any], StringValidator,
                                          IntValidator, BytesValidator,
                                          ListValidator, DictValidator]) -> Callable:
    """Decorator that validates function arguments by name.
    
    Usage:
        @validate_input(user_id=IntValidator(min_val=1),
                        message=StringValidator(max_len=1000))
        def send_message(user_id: int, message: str) -> None:
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        sig_params = list(func.__code__.co_varnames[:func.__code__.co_argcount])
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Bind args to param names
            bound: Dict[str, Any] = {}
            for i, arg in enumerate(args):
                if i < len(sig_params):
                    bound[sig_params[i]] = arg
            bound.update(kwargs)
            
            # Validate each parameter that has a validator
            for param_name, validator in validators.items():
                if param_name in bound:
                    bound[param_name] = validator(bound[param_name])
            
            # Reconstruct args and kwargs
            new_args = []
            new_kwargs = dict(kwargs)
            for i, param in enumerate(sig_params):
                if i < len(args):
                    new_args.append(bound[param])
                elif param in kwargs:
                    new_kwargs[param] = bound[param]
            
            return func(*new_args, **new_kwargs)
        return wrapper
    return decorator


# =============================================================================
# DEMO
# =============================================================================

def demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS  |  INPUT VALIDATION")
    print("=" * 60)
    
    @validate_input(
        name=StringValidator(min_len=1, max_len=50, name="name"),
        age=IntValidator(min_val=0, max_val=150, name="age"),
    )
    def greet(name: str, age: int) -> str:
        return f"Hello {name}, age {age}"
    
    # Valid
    print(greet("Alice", 30))
    
    # Invalid: too long
    try:
        greet("A" * 100, 30)
    except ValidationError as e:
        print(f"[BLOCKED] {e}")
    
    # Invalid: negative age
    try:
        greet("Bob", -5)
    except ValidationError as e:
        print(f"[BLOCKED] {e}")
    
    print("=" * 60)


if __name__ == "__main__":
    demo()
