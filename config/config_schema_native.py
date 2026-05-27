#!/usr/bin/env python3
"""
config/config_schema_native.py
==============================
Configuration Schema Validation

Validates MAGNATRIX-OS configuration against typed schema on boot.
Prevents silent misconfigurations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, Union


@dataclass
class FieldSpec:
    type: Type
    required: bool = True
    default: Any = None
    default_factory: Any = None
    min: Optional[Union[int, float]] = None
    max: Optional[Union[int, float]] = None
    allowed: Optional[List[Any]] = None


class ConfigSchema:
    """Schema validator for MAGNATRIX configuration."""

    SCHEMA: Dict[str, Dict[str, FieldSpec]] = {
        "kernel": {
            "log_level": FieldSpec(str, default="INFO", allowed=["DEBUG", "INFO", "WARN", "ERROR"]),
            "max_workers": FieldSpec(int, default=4, min=1, max=64),
        },
        "identity": {
            "key_store": FieldSpec(str, default="/var/lib/magnatrix/identities"),
            "auto_rotate": FieldSpec(bool, default=True),
        },
        "p2p": {
            "listen_port": FieldSpec(int, default=8000, min=1024, max=65535),
            "bootstrap_peers": FieldSpec(list, default_factory=list),
        },
        "sandbox": {
            "enabled": FieldSpec(bool, default=True),
            "max_cpu_percent": FieldSpec(int, default=80, min=1, max=100),
        },
    }

    @classmethod
    def validate(cls, config: Dict[str, Any]) -> List[str]:
        """Validate config against schema. Returns list of error messages."""
        errors: List[str] = []
        for section, fields in cls.SCHEMA.items():
            section_data = config.get(section, {})
            if not isinstance(section_data, dict):
                errors.append(f"Section '{section}' must be a dict, got {type(section_data).__name__}")
                continue
            for field_name, spec in fields.items():
                value = section_data.get(field_name, spec.default)
                if value is None and spec.required:
                    errors.append(f"Missing required field: {section}.{field_name}")
                    continue
                if value is not None and not isinstance(value, spec.type):
                    errors.append(f"{section}.{field_name}: expected {spec.type.__name__}, got {type(value).__name__}")
                    continue
                if spec.min is not None and value is not None and value < spec.min:
                    errors.append(f"{section}.{field_name}: {value} < minimum {spec.min}")
                if spec.max is not None and value is not None and value > spec.max:
                    errors.append(f"{section}.{field_name}: {value} > maximum {spec.max}")
                if spec.allowed is not None and value is not None and value not in spec.allowed:
                    errors.append(f"{section}.{field_name}: '{value}' not in allowed values {spec.allowed}")
        return errors

    @classmethod
    def validate_or_raise(cls, config: Dict[str, Any]) -> None:
        errors = cls.validate(config)
        if errors:
            raise ValueError("Configuration validation failed:\n  - " + "\n  - ".join(errors))


def demo():
    print("=" * 60)
    print("MAGNATRIX-OS  |  CONFIG SCHEMA VALIDATION")
    print("=" * 60)

    good = {
        "kernel": {"log_level": "INFO", "max_workers": 8},
        "p2p": {"listen_port": 8000},
    }
    print(f"Valid config: {ConfigSchema.validate(good)}")

    bad = {
        "kernel": {"log_level": "INVALID", "max_workers": 200},
        "p2p": {"listen_port": 80},
    }
    errors = ConfigSchema.validate(bad)
    for e in errors:
        print(f"  Error: {e}")

    print("=" * 60)


if __name__ == "__main__":
    demo()
