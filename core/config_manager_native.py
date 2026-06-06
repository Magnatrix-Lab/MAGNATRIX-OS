#!/usr/bin/env python3
"""
Configuration Manager for MAGNATRIX-OS
Centralized config with env vars, file loading, hot reload, secrets injection.
Pure stdlib -- no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional, Callable


class ConfigManager:
    """Centralized configuration manager with hot reload."""

    def __init__(self, config_path: Optional[str] = None) -> None:
        self._config: Dict[str, Any] = {}
        self._defaults: Dict[str, Any] = {}
        self._secrets: Dict[str, str] = {}
        self._config_path = config_path
        self._last_load: float = 0
        self._reload_interval: int = 5
        self._callbacks: List[Callable[[str, Any], None]] = []

    def set_default(self, key: str, value: Any) -> None:
        self._defaults[key] = value
        if key not in self._config:
            self._config[key] = value

    def load_file(self, path: str) -> None:
        """Load config from JSON file."""
        if not os.path.exists(path):
            return
        with open(path, 'r') as f:
            data = json.load(f)
        self._config.update(data)
        self._config_path = path
        self._last_load = time.time()

    def load_env(self, prefix: str = "MAGNATRIX_") -> None:
        """Load config from environment variables with prefix."""
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower().replace('__', '.')
                self._config[config_key] = self._cast_value(value)

    def _cast_value(self, value: str) -> Any:
        """Auto-cast string to proper type."""
        if value.lower() in ('true', 'yes', '1'):
            return True
        if value.lower() in ('false', 'no', '0'):
            return False
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value with dot notation."""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """Set config value with dot notation."""
        keys = key.split('.')
        target = self._config
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        old = target.get(keys[-1])
        target[keys[-1]] = value

        # Notify callbacks
        for cb in self._callbacks:
            cb(key, value)

    def inject_secret(self, key: str, env_var: str) -> None:
        """Inject secret from environment variable."""
        value = os.environ.get(env_var)
        if value:
            self._secrets[key] = value
            self._config[key] = value

    def get_secret(self, key: str) -> Optional[str]:
        return self._secrets.get(key)

    def hot_reload(self) -> None:
        """Reload config if file changed."""
        if self._config_path and os.path.exists(self._config_path):
            mtime = os.path.getmtime(self._config_path)
            if mtime > self._last_load:
                self.load_file(self._config_path)

    def start_auto_reload(self, interval: int = 5) -> None:
        """Start background auto-reload."""
        import threading
        self._reload_interval = interval

        def reload_loop():
            while True:
                time.sleep(interval)
                self.hot_reload()

        threading.Thread(target=reload_loop, daemon=True).start()

    def on_change(self, callback: Callable[[str, Any], None]) -> None:
        self._callbacks.append(callback)

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._config)

    def save(self, path: Optional[str] = None) -> None:
        save_path = path or self._config_path
        if save_path:
            with open(save_path, 'w') as f:
                json.dump(self._config, f, indent=2, default=str)


def _demo() -> None:
    print("=== Config Manager Demo ===\n")

    cfg = ConfigManager()

    # Set defaults
    cfg.set_default('app.name', 'MAGNATRIX-OS')
    cfg.set_default('app.debug', False)
    cfg.set_default('db.timeout', 30)

    # Load from dict
    cfg.set('llm.model', 'llama3.2:3b')
    cfg.set('llm.temperature', 0.7)
    cfg.set('llm.max_tokens', 2048)

    # Dot notation access
    print(f"app.name: {cfg.get('app.name')}")
    print(f"llm.model: {cfg.get('llm.model')}")
    print(f"llm.temperature: {cfg.get('llm.temperature')}")
    print(f"nonexistent: {cfg.get('nonexistent', 'default')}")

    # Save and load
    cfg.save('/tmp/magnatrix_test_config.json')
    cfg2 = ConfigManager('/tmp/magnatrix_test_config.json')
    print(f"\nLoaded config: {cfg2.get('llm.model')}")

    print("\n=== Config Manager Demo Complete ===")


if __name__ == '__main__':
    _demo()
