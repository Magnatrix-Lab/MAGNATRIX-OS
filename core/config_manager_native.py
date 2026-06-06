#!/usr/bin/env python3
"""
Config Manager for MAGNATRIX-OS
Centralized configuration with schema validation, hot-reload support,
environment variable interpolation, and hierarchical overrides.
Native stdlib only — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import copy
import dataclasses
import enum
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


class ConfigSource(enum.Enum):
    FILE = "file"
    ENV = "env"
    DEFAULT = "default"
    RUNTIME = "runtime"


@dataclasses.dataclass
class ConfigSchema:
    """Schema definition for a single config key."""
    key: str
    type_hint: str  # "str", "int", "float", "bool", "list", "dict", "path"
    default: Any = None
    required: bool = False
    description: str = ""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[Any]] = None
    env_var: Optional[str] = None
    secret: bool = False  # mask in logs

    def validate(self, value: Any) -> Tuple[bool, str]:
        if value is None and self.required:
            return False, f"'{self.key}' is required but missing"
        if value is None:
            return True, ""
        type_ok = self._check_type(value)
        if not type_ok[0]:
            return type_ok
        if self.min_value is not None and isinstance(value, (int, float)) and value < self.min_value:
            return False, f"'{self.key}' below minimum {self.min_value}"
        if self.max_value is not None and isinstance(value, (int, float)) and value > self.max_value:
            return False, f"'{self.key}' above maximum {self.max_value}"
        if self.allowed_values is not None and value not in self.allowed_values:
            return False, f"'{self.key}' must be one of {self.allowed_values}"
        return True, ""

    def _check_type(self, value: Any) -> Tuple[bool, str]:
        mapping = {
            "str": str, "int": int, "float": float, "bool": bool,
            "list": list, "dict": dict, "path": str,
        }
        expected = mapping.get(self.type_hint)
        if expected is None:
            return True, ""
        if self.type_hint == "bool" and isinstance(value, str):
            return True, ""  # allow string bools
        if self.type_hint == "path" and isinstance(value, str):
            return True, ""
        if not isinstance(value, expected):
            return False, f"'{self.key}' expected {self.type_hint}, got {type(value).__name__}"
        return True, ""


class ConfigManager:
    """Hierarchical config manager with schema validation and hot reload."""

    def __init__(self, config_path: Optional[str] = None) -> None:
        self._config_path = Path(config_path) if config_path else None
        self._values: Dict[str, Any] = {}
        self._sources: Dict[str, ConfigSource] = {}
        self._schemas: Dict[str, ConfigSchema] = {}
        self._defaults: Dict[str, Any] = {}
        self._listeners: List[Callable[[str, Any, Any], None]] = []
        self._last_load: float = 0.0
        self._load()

    # ------------------------------------------------------------------
    # Schema registration
    # ------------------------------------------------------------------

    def register_schema(self, schema: ConfigSchema) -> None:
        self._schemas[schema.key] = schema
        if schema.default is not None and schema.key not in self._values:
            self._values[schema.key] = schema.default
            self._sources[schema.key] = ConfigSource.DEFAULT

    def register_schemas(self, schemas: List[ConfigSchema]) -> None:
        for s in schemas:
            self.register_schema(s)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self._config_path and self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for k, v in data.items():
                    self._values[k] = self._interpolate(v)
                    self._sources[k] = ConfigSource.FILE
                self._last_load = self._config_path.stat().st_mtime
            except Exception:
                pass
        # Overlay environment variables
        for schema in self._schemas.values():
            if schema.env_var and schema.env_var in os.environ:
                raw = os.environ[schema.env_var]
                self._values[schema.key] = self._coerce(schema.type_hint, raw)
                self._sources[schema.key] = ConfigSource.ENV

    def _interpolate(self, value: Any) -> Any:
        """Replace ${VAR} and ${VAR:-default} with environment variables."""
        if isinstance(value, str):
            pattern = re.compile(r"\$\{(\w+)(?::-([^}]*))?\}")
            def replacer(m: re.Match) -> str:
                var, default = m.group(1), m.group(2)
                return os.environ.get(var, default or "")
            return pattern.sub(replacer, value)
        if isinstance(value, dict):
            return {k: self._interpolate(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._interpolate(v) for v in value]
        return value

    def _coerce(self, type_hint: str, raw: str) -> Any:
        if type_hint == "bool":
            return raw.lower() in ("true", "1", "yes", "on")
        if type_hint == "int":
            return int(raw)
        if type_hint == "float":
            return float(raw)
        if type_hint == "list":
            return [x.strip() for x in raw.split(",")] if raw else []
        if type_hint == "dict":
            return json.loads(raw) if raw else {}
        return raw

    def reload(self) -> bool:
        """Reload config file if it changed on disk."""
        if not self._config_path:
            return False
        try:
            mtime = self._config_path.stat().st_mtime
        except Exception:
            return False
        if mtime > self._last_load:
            old_values = copy.deepcopy(self._values)
            self._values.clear()
            self._sources.clear()
            self._load()
            # Merge defaults back in
            for k, v in self._defaults.items():
                if k not in self._values:
                    self._values[k] = v
                    self._sources[k] = ConfigSource.DEFAULT
            # Notify listeners
            for k in set(old_values.keys()) | set(self._values.keys()):
                old = old_values.get(k)
                new = self._values.get(k)
                if old != new:
                    for listener in self._listeners:
                        listener(k, old, new)
            return True
        return False

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        return self._values.get(key, default)

    def get_typed(self, key: str, type_hint: str, default: Any = None) -> Any:
        val = self._values.get(key, default)
        if val is None:
            return default
        return self._coerce(type_hint, str(val)) if isinstance(val, str) else val

    def set(self, key: str, value: Any, validate: bool = True) -> None:
        if validate and key in self._schemas:
            ok, msg = self._schemas[key].validate(value)
            if not ok:
                raise ValueError(msg)
        old = self._values.get(key)
        self._values[key] = value
        self._sources[key] = ConfigSource.RUNTIME
        for listener in self._listeners:
            listener(key, old, value)

    def has(self, key: str) -> bool:
        return key in self._values

    def keys(self) -> List[str]:
        return sorted(self._values.keys())

    def all(self) -> Dict[str, Any]:
        return dict(self._values)

    def source(self, key: str) -> Optional[ConfigSource]:
        return self._sources.get(key)

    def get_schema(self, key: str) -> Optional[ConfigSchema]:
        return self._schemas.get(key)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_all(self) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        for key, schema in self._schemas.items():
            value = self._values.get(key)
            ok, msg = schema.validate(value)
            if not ok:
                errors.append(msg)
        return len(errors) == 0, errors

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Optional[str] = None) -> None:
        target = Path(path) if path else self._config_path
        if not target:
            raise ValueError("No config path set")
        target.parent.mkdir(parents=True, exist_ok=True)
        # Strip secret values for safe logging
        safe = {}
        for k, v in self._values.items():
            if k in self._schemas and self._schemas[k].secret:
                safe[k] = "***"
            else:
                safe[k] = v
        with open(target, "w", encoding="utf-8") as f:
            json.dump(safe, f, indent=2, ensure_ascii=False)

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._values, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Change listeners
    # ------------------------------------------------------------------

    def add_listener(self, callback: Callable[[str, Any, Any], None]) -> None:
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[str, Any, Any], None]) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        by_source: Dict[str, int] = {}
        for src in self._sources.values():
            by_source[src.value] = by_source.get(src.value, 0) + 1
        return {
            "total_keys": len(self._values),
            "registered_schemas": len(self._schemas),
            "by_source": by_source,
            "config_path": str(self._config_path) if self._config_path else None,
            "last_load": self._last_load,
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump({
            "app_name": "MAGNATRIX-OS",
            "max_workers": "8",
            "debug_mode": "false",
            "api_timeout": "30.5",
            "allowed_hosts": "localhost,127.0.0.1",
            "db_url": "${DB_URL:-sqlite:///default.db}",
        }, f)
        temp_path = f.name

    mgr = ConfigManager(temp_path)
    mgr.register_schemas([
        ConfigSchema("app_name", "str", required=True, description="Application name"),
        ConfigSchema("max_workers", "int", default=4, min_value=1, max_value=64, description="Worker pool size"),
        ConfigSchema("debug_mode", "bool", default=False, description="Enable debug output"),
        ConfigSchema("api_timeout", "float", default=30.0, min_value=1.0, max_value=300.0, description="API timeout seconds"),
        ConfigSchema("allowed_hosts", "list", default=["localhost"], description="Allowed hostnames"),
        ConfigSchema("db_url", "str", default="sqlite:///default.db", description="Database URL", secret=True),
    ])
    mgr.reload()
    print("=== Config Manager Demo ===\n")
    print(f"app_name: {mgr.get('app_name')}")
    print(f"max_workers: {mgr.get('max_workers')} (type: {type(mgr.get('max_workers')).__name__})")
    print(f"debug_mode: {mgr.get('debug_mode')} (type: {type(mgr.get('debug_mode')).__name__})")
    print(f"api_timeout: {mgr.get('api_timeout')} (type: {type(mgr.get('api_timeout')).__name__})")
    print(f"allowed_hosts: {mgr.get('allowed_hosts')} (type: {type(mgr.get('allowed_hosts')).__name__})")
    print(f"db_url: {mgr.get('db_url')} (masked in save: {mgr.get_schema('db_url') and mgr.get_schema('db_url').secret})")
    print(f"\nStats: {mgr.stats()}")
    valid, errors = mgr.validate_all()
    print(f"Validation: {'PASS' if valid else 'FAIL'} {errors}")
    os.remove(temp_path)


if __name__ == "__main__":
    _demo()
