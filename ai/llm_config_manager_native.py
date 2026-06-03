"""
llm_config_manager_native.py
MAGNATRIX-OS Configuration Manager
Native Python, stdlib only.
Provides environment-specific configuration management with hierarchical overrides,
hot-reloading, schema validation, and secret interpolation.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable


class ConfigScope(Enum):
    DEFAULT = auto()
    ENVIRONMENT = auto()
    USER = auto()
    RUNTIME = auto()


class ConfigStatus(Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    PENDING = "pending"


@dataclass
class ConfigEntry:
    key: str
    value: Any
    scope: ConfigScope = ConfigScope.DEFAULT
    description: str = ""
    status: ConfigStatus = ConfigStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    modified_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "scope": self.scope.name,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "tags": self.tags,
        }


@dataclass
class ConfigSchema:
    key: str
    expected_type: type
    required: bool = True
    default: Any = None
    validator: Optional[Callable[[Any], bool]] = None
    description: str = ""

    def validate(self, value: Any) -> bool:
        if value is None and self.required and self.default is None:
            return False
        if value is not None and not isinstance(value, self.expected_type):
            return False
        if self.validator and value is not None:
            return self.validator(value)
        return True


class ConfigManagerEngine:
    """
    Hierarchical configuration manager with hot-reload support.
    Priority: RUNTIME > USER > ENVIRONMENT > DEFAULT
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        self._store: Dict[str, Dict[str, ConfigEntry]] = {
            scope.name: {} for scope in ConfigScope
        }
        self._schemas: Dict[str, ConfigSchema] = {}
        self._lock = threading.RLock()
        self._watchers: List[Callable] = []
        self._config_path = config_path
        self._last_reload: float = 0.0
        self._watch_thread: Optional[threading.Thread] = None
        self._stop_watch = threading.Event()
        if config_path:
            self._start_file_watcher(config_path)

    def _start_file_watcher(self, path: str) -> None:
        def watcher() -> None:
            while not self._stop_watch.is_set():
                try:
                    p = Path(path)
                    if p.exists():
                        mtime = p.stat().st_mtime
                        if mtime > self._last_reload:
                            self._last_reload = mtime
                            self.load_from_file(path)
                            self._notify_watchers()
                except Exception:
                    pass
                time.sleep(2.0)

        self._watch_thread = threading.Thread(target=watcher, daemon=True)
        self._watch_thread.start()

    def _notify_watchers(self) -> None:
        for cb in self._watchers:
            try:
                cb()
            except Exception:
                pass

    def register_schema(self, schema: ConfigSchema) -> None:
        with self._lock:
            self._schemas[schema.key] = schema

    def set(self, key: str, value: Any, scope: ConfigScope = ConfigScope.RUNTIME,
            description: str = "", tags: Optional[List[str]] = None) -> None:
        with self._lock:
            if key in self._schemas:
                if not self._schemas[key].validate(value):
                    raise ValueError(f"Schema validation failed for key: {key}")
            entry = ConfigEntry(
                key=key, value=value, scope=scope, description=description,
                tags=tags or [], modified_at=time.time()
            )
            self._store[scope.name][key] = entry

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            for scope in (ConfigScope.RUNTIME, ConfigScope.USER,
                          ConfigScope.ENVIRONMENT, ConfigScope.DEFAULT):
                if key in self._store[scope.name]:
                    entry = self._store[scope.name][key]
                    if entry.status == ConfigStatus.ACTIVE:
                        val = entry.value
                        if isinstance(val, str):
                            val = self._interpolate_secrets(val)
                        return val
            # Fallback to schema default
            if key in self._schemas:
                return self._schemas[key].default
            return default

    def _interpolate_secrets(self, value: str) -> str:
        pattern = re.compile(r'\$\{SECRET:([^}]+)\}')

        def replacer(match: Any) -> str:
            secret_key = match.group(1)
            return os.environ.get(secret_key, match.group(0))

        return pattern.sub(replacer, value)

    def get_all(self, scope: Optional[ConfigScope] = None) -> Dict[str, Any]:
        with self._lock:
            result: Dict[str, Any] = {}
            scopes = [scope] if scope else list(ConfigScope)
            for sc in scopes:
                for entry in self._store[sc.name].values():
                    if entry.status == ConfigStatus.ACTIVE:
                        result[entry.key] = entry.value
            return result

    def load_from_file(self, path: str) -> None:
        p = Path(path)
        if not p.exists():
            return
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, value in data.items():
            self.set(key, value, ConfigScope.ENVIRONMENT)

    def save_to_file(self, path: str, scope: Optional[ConfigScope] = None) -> None:
        data = self.get_all(scope)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def load_from_env(self, prefix: str = "MAGNATRIX_") -> None:
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                try:
                    parsed = json.loads(value)
                except Exception:
                    parsed = value
                self.set(config_key, parsed, ConfigScope.ENVIRONMENT)

    def add_watcher(self, callback: Callable) -> None:
        self._watchers.append(callback)

    def remove_watcher(self, callback: Callable) -> None:
        if callback in self._watchers:
            self._watchers.remove(callback)

    def deprecate(self, key: str) -> bool:
        with self._lock:
            for scope in ConfigScope:
                if key in self._store[scope.name]:
                    self._store[scope.name][key].status = ConfigStatus.DEPRECATED
                    return True
        return False

    def validate_all(self) -> List[str]:
        errors: List[str] = []
        with self._lock:
            for key, schema in self._schemas.items():
                val = self.get(key)
                if not schema.validate(val):
                    errors.append(f"Validation failed: {key} (expected {schema.expected_type.__name__})")
        return errors

    def get_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            for scope in (ConfigScope.RUNTIME, ConfigScope.USER,
                          ConfigScope.ENVIRONMENT, ConfigScope.DEFAULT):
                if key in self._store[scope.name]:
                    return self._store[scope.name][key].to_dict()
        return None

    def diff(self, other: ConfigManagerEngine) -> Dict[str, Any]:
        self_flat = self.get_all()
        other_flat = other.get_all()
        all_keys = set(self_flat.keys()) | set(other_flat.keys())
        diff: Dict[str, Any] = {}
        for k in all_keys:
            if self_flat.get(k) != other_flat.get(k):
                diff[k] = {"self": self_flat.get(k), "other": other_flat.get(k)}
        return diff

    def export(self) -> Dict[str, Any]:
        with self._lock:
            export: Dict[str, Any] = {}
            for scope in ConfigScope:
                export[scope.name] = {k: v.to_dict() for k, v in self._store[scope.name].items()}
            return export

    def shutdown(self) -> None:
        self._stop_watch.set()
        if self._watch_thread:
            self._watch_thread.join(timeout=1.0)


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Configuration Manager")
    print("=" * 60)

    engine = ConfigManagerEngine()

    # Register schemas
    engine.register_schema(ConfigSchema(
        key="llm.model", expected_type=str, default="gpt-4o",
        description="Default LLM model identifier"
    ))
    engine.register_schema(ConfigSchema(
        key="llm.temperature", expected_type=float, default=0.7,
        validator=lambda x: 0.0 <= x <= 2.0,
        description="Sampling temperature"
    ))
    engine.register_schema(ConfigSchema(
        key="llm.max_tokens", expected_type=int, default=4096,
        validator=lambda x: x > 0,
        description="Maximum token output"
    ))

    # Set values at different scopes
    engine.set("llm.model", "gpt-4o", ConfigScope.DEFAULT, "Default model")
    engine.set("llm.temperature", 0.5, ConfigScope.ENVIRONMENT, "Production temp")
    engine.set("llm.max_tokens", 8192, ConfigScope.RUNTIME, "Runtime override")
    engine.set("api.base_url", "https://api.example.com", ConfigScope.DEFAULT)
    engine.set("api.key", "${SECRET:API_KEY}", ConfigScope.ENVIRONMENT, "API key with secret interpolation")

    # Load from env (simulated)
    os.environ["MAGNATRIX_DEBUG"] = "true"
    os.environ["MAGNATRIX_LOG_LEVEL"] = "info"
    engine.load_from_env("MAGNATRIX_")

    print("\n--- All Active Configs ---")
    for k, v in engine.get_all().items():
        print(f"  {k} = {v}")

    print("\n--- Hierarchical Resolution ---")
    print(f"  llm.model       -> {engine.get('llm.model')}")
    print(f"  llm.temperature -> {engine.get('llm.temperature')}")
    print(f"  llm.max_tokens  -> {engine.get('llm.max_tokens')}")
    print(f"  debug           -> {engine.get('debug')}")
    print(f"  log_level       -> {engine.get('log_level')}")
    print(f"  api.key         -> {engine.get('api.key')}")
    print(f"  missing_key     -> {engine.get('missing_key', 'fallback')}")

    print("\n--- Metadata ---")
    meta = engine.get_metadata("llm.max_tokens")
    if meta:
        for k, v in meta.items():
            print(f"  {k}: {v}")

    print("\n--- Validation ---")
    errors = engine.validate_all()
    print(f"  Errors: {errors if errors else 'None'}")

    # Save / load test
    test_path = "/tmp/magnatrix_config_test.json"
    engine.save_to_file(test_path)
    engine2 = ConfigManagerEngine()
    engine2.load_from_file(test_path)
    print("\n--- Diff After Reload ---")
    diff = engine.diff(engine2)
    print(f"  Differences: {len(diff)}")

    # Cleanup
    engine.shutdown()
    if os.path.exists(test_path):
        os.remove(test_path)
    for k in list(os.environ.keys()):
        if k.startswith("MAGNATRIX_"):
            del os.environ[k]

    print("\nConfig Manager test complete.")


if __name__ == "__main__":
    run()
