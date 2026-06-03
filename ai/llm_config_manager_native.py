"""LLM Config Manager — Native Python (stdlib only)."""
from __future__ import annotations
import json, os
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

class ConfigManager:
    def __init__(self, config_path: Optional[str] = None) -> None:
        self.config_path = config_path
        self._config: Dict[str, Any] = {}
        if config_path and os.path.exists(config_path):
            self.load(config_path)

    def set(self, key: str, value: Any) -> None:
        keys = key.split(".")
        current = self._config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        current = self._config
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    def load(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            self._config = json.load(f)

    def save(self, path: Optional[str] = None) -> None:
        save_path = path or self.config_path
        if not save_path:
            raise ValueError("No path specified")
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2)

    def get_stats(self) -> Dict[str, Any]:
        return {"keys": len(self._flatten(self._config)), "nested": self._count_nested(self._config)}

    def _flatten(self, d: Dict, prefix: str = "") -> Dict[str, Any]:
        items = {}
        for k, v in d.items():
            new_key = prefix + k if not prefix else prefix + "." + k
            if isinstance(v, dict):
                items.update(self._flatten(v, new_key))
            else:
                items[new_key] = v
        return items

    def _count_nested(self, d: Dict) -> int:
        count = 0
        for v in d.values():
            if isinstance(v, dict):
                count += 1 + self._count_nested(v)
        return count

def run() -> None:
    print("Config Manager test")
    e = ConfigManager()
    e.set("model.name", "gpt-4")
    e.set("model.temperature", 0.7)
    e.set("api.timeout", 30)
    e.set("api.retry", 3)
    print("  model.name: " + str(e.get("model.name")))
    print("  api.timeout: " + str(e.get("api.timeout")))
    print("  Stats: " + str(e.get_stats()))
    print("Config Manager test complete.")

if __name__ == "__main__":
    run()
