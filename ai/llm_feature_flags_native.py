"""Feature Flags & Configuration — Dynamic configuration, hot reload, validation.

Modul ini menyediakan:
- FeatureFlag dengan toggle, rollout percentage, user targeting
- ConfigManager dengan hot reload dan validation
- Environment-based overrides
- A/B testing integration untuk feature flags
- Audit log untuk config changes
"""

from __future__ import annotations

import json
import time
import uuid
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class FlagState(Enum):
    OFF = auto()
    ON = auto()
    ROLLOUT = auto()
    TARGETED = auto()


@dataclass
class FeatureFlag:
    """Single feature flag definition."""
    flag_id: str
    name: str
    description: str = ""
    state: FlagState = FlagState.OFF
    rollout_percent: float = 0.0  # 0.0 - 100.0
    targeted_users: Set[str] = field(default_factory=set)
    targeted_groups: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    default_value: Any = False

    def is_enabled(self, user_id: Optional[str] = None, user_groups: Optional[List[str]] = None) -> bool:
        if self.state == FlagState.ON:
            return True
        if self.state == FlagState.OFF:
            return False
        if self.state == FlagState.TARGETED:
            if user_id and user_id in self.targeted_users:
                return True
            if user_groups:
                for group in user_groups:
                    if group in self.targeted_groups:
                        return True
            return False
        if self.state == FlagState.ROLLOUT:
            if user_id:
                # Deterministic based on user_id hash
                h = hash(f"{self.flag_id}:{user_id}") % 10000
                return (h / 100) < self.rollout_percent
            return random.random() * 100 < self.rollout_percent
        return bool(self.default_value)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "flag_id": self.flag_id,
            "name": self.name,
            "state": self.state.name,
            "rollout_percent": self.rollout_percent,
            "targeted_users_count": len(self.targeted_users),
            "targeted_groups_count": len(self.targeted_groups),
            "default_value": self.default_value
        }


@dataclass
class ConfigValue:
    """Single configuration value dengan type validation."""
    key: str
    value: Any
    value_type: str = "string"  # string, int, float, bool, json
    description: str = ""
    mutable: bool = True
    updated_at: float = field(default_factory=time.time)


class ConfigValidator:
    """Validate configuration values."""

    def validate(self, value: Any, value_type: str) -> Tuple[bool, Any]:
        try:
            if value_type == "string":
                return True, str(value)
            elif value_type == "int":
                return True, int(value)
            elif value_type == "float":
                return True, float(value)
            elif value_type == "bool":
                if isinstance(value, str):
                    return True, value.lower() in ("true", "1", "yes", "on")
                return True, bool(value)
            elif value_type == "json":
                if isinstance(value, str):
                    return True, json.loads(value)
                return True, value
            return True, value
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            return False, str(e)


class FlagRegistry:
    """Register dan manage feature flags."""

    def __init__(self):
        self._flags: Dict[str, FeatureFlag] = {}
        self._change_log: List[Dict[str, Any]] = []

    def register(self, flag: FeatureFlag) -> FeatureFlag:
        self._flags[flag.flag_id] = flag
        self._log_change("register", flag.flag_id, flag.to_dict())
        return flag

    def get(self, flag_id: str) -> Optional[FeatureFlag]:
        return self._flags.get(flag_id)

    def toggle(self, flag_id: str, state: FlagState) -> Optional[FeatureFlag]:
        flag = self._flags.get(flag_id)
        if not flag:
            return None
        flag.state = state
        flag.updated_at = time.time()
        self._log_change("toggle", flag_id, {"state": state.name})
        return flag

    def set_rollout(self, flag_id: str, percent: float) -> Optional[FeatureFlag]:
        flag = self._flags.get(flag_id)
        if not flag:
            return None
        flag.rollout_percent = max(0.0, min(100.0, percent))
        flag.state = FlagState.ROLLOUT
        flag.updated_at = time.time()
        self._log_change("rollout", flag_id, {"percent": flag.rollout_percent})
        return flag

    def add_target(self, flag_id: str, user_id: Optional[str] = None, group: Optional[str] = None) -> Optional[FeatureFlag]:
        flag = self._flags.get(flag_id)
        if not flag:
            return None
        if user_id:
            flag.targeted_users.add(user_id)
        if group:
            flag.targeted_groups.add(group)
        flag.state = FlagState.TARGETED
        flag.updated_at = time.time()
        self._log_change("target", flag_id, {"user": user_id, "group": group})
        return flag

    def check(self, flag_id: str, user_id: Optional[str] = None, user_groups: Optional[List[str]] = None) -> bool:
        flag = self._flags.get(flag_id)
        if not flag:
            return False
        return flag.is_enabled(user_id, user_groups)

    def list_all(self) -> List[FeatureFlag]:
        return list(self._flags.values())

    def list_enabled(self) -> List[str]:
        return [f.flag_id for f in self._flags.values() if f.state == FlagState.ON]

    def _log_change(self, action: str, flag_id: str, details: Dict[str, Any]) -> None:
        self._change_log.append({
            "timestamp": time.time(),
            "action": action,
            "flag_id": flag_id,
            "details": details
        })

    def get_change_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._change_log[-limit:]

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "flags": [f.to_dict() for f in self._flags.values()],
                "change_log": self._change_log[-100:]
            }, f, indent=2)

    def import_from(self, path: str) -> int:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        count = 0
        for fdata in data.get("flags", []):
            flag = FeatureFlag(
                flag_id=fdata.get("flag_id", str(uuid.uuid4())[:12]),
                name=fdata.get("name", "unnamed"),
                description=fdata.get("description", ""),
                state=FlagState[fdata.get("state", "OFF")],
                rollout_percent=fdata.get("rollout_percent", 0.0),
                default_value=fdata.get("default_value", False)
            )
            self.register(flag)
            count += 1
        return count


class ConfigManager:
    """Manage application configuration dengan hot reload."""

    def __init__(self, validator: Optional[ConfigValidator] = None):
        self.validator = validator or ConfigValidator()
        self._configs: Dict[str, ConfigValue] = {}
        self._change_log: List[Dict[str, Any]] = []
        self._reload_hooks: List[Callable[[], None]] = []

    def set(self, key: str, value: Any, value_type: str = "string", description: str = "", mutable: bool = True) -> Tuple[bool, str]:
        valid, result = self.validator.validate(value, value_type)
        if not valid:
            return False, f"Validation failed: {result}"
        existing = self._configs.get(key)
        if existing and not existing.mutable:
            return False, "Config is immutable"
        self._configs[key] = ConfigValue(key, result, value_type, description, mutable, time.time())
        self._log_change("set", key, {"value": str(result)[:100], "type": value_type})
        return True, "OK"

    def get(self, key: str, default: Any = None) -> Any:
        val = self._configs.get(key)
        return val.value if val else default

    def get_typed(self, key: str, value_type: str, default: Any = None) -> Any:
        val = self._configs.get(key)
        if not val:
            return default
        valid, result = self.validator.validate(val.value, value_type)
        return result if valid else default

    def get_all(self) -> Dict[str, Any]:
        return {k: v.value for k, v in self._configs.items()}

    def delete(self, key: str) -> bool:
        val = self._configs.pop(key, None)
        if val:
            self._log_change("delete", key, {})
            return True
        return False

    def load_from_env(self, prefix: str = "MAGNA_") -> int:
        import os
        count = 0
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                # Try to infer type
                if value.lower() in ("true", "false"):
                    self.set(config_key, value, "bool")
                else:
                    try:
                        int(value)
                        self.set(config_key, value, "int")
                    except ValueError:
                        try:
                            float(value)
                            self.set(config_key, value, "float")
                        except ValueError:
                            self.set(config_key, value, "string")
                count += 1
        return count

    def load_from_file(self, path: str) -> int:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        count = 0
        for key, val_data in data.items():
            if isinstance(val_data, dict):
                self.set(key, val_data.get("value"), val_data.get("type", "string"), val_data.get("description", ""))
            else:
                self.set(key, val_data)
            count += 1
        self._run_reload_hooks()
        return count

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                k: {"value": v.value, "type": v.value_type, "description": v.description, "mutable": v.mutable}
                for k, v in self._configs.items()
            }, f, indent=2)

    def on_reload(self, hook: Callable[[], None]) -> None:
        self._reload_hooks.append(hook)

    def _run_reload_hooks(self) -> None:
        for hook in self._reload_hooks:
            try:
                hook()
            except Exception:
                pass

    def _log_change(self, action: str, key: str, details: Dict[str, Any]) -> None:
        self._change_log.append({
            "timestamp": time.time(),
            "action": action,
            "key": key,
            "details": details
        })

    def get_change_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._change_log[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_configs": len(self._configs),
            "mutable": sum(1 for v in self._configs.values() if v.mutable),
            "immutable": sum(1 for v in self._configs.values() if not v.mutable),
            "changes": len(self._change_log)
        }


class FeatureFlagsEngine:
    """Main orchestrator combining flags and config."""

    def __init__(self):
        self.flags = FlagRegistry()
        self.config = ConfigManager()

    def is_enabled(self, flag_id: str, user_id: Optional[str] = None, user_groups: Optional[List[str]] = None) -> bool:
        return self.flags.check(flag_id, user_id, user_groups)

    def get_config(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def get_all_flags(self) -> List[Dict[str, Any]]:
        return [f.to_dict() for f in self.flags.list_all()]

    def get_all_config(self) -> Dict[str, Any]:
        return self.config.get_all()

    def export_all(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "flags": self.get_all_flags(),
                "config": self.config.get_all(),
                "timestamp": time.time()
            }, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("FEATURE FLAGS & CONFIGURATION DEMO")
    print("=" * 70)

    engine = FeatureFlagsEngine()

    # 1. Feature flags
    print("\n[1] Feature Flags")
    engine.flags.register(FeatureFlag("new_ui", "New UI Design", state=FlagState.ON))
    engine.flags.register(FeatureFlag("dark_mode", "Dark Mode", state=FlagState.ROLLOUT, rollout_percent=30.0))
    engine.flags.register(FeatureFlag("beta_api", "Beta API", state=FlagState.TARGETED, targeted_users={"alice"}, targeted_groups={"beta"}))
    engine.flags.register(FeatureFlag("legacy_mode", "Legacy Mode", state=FlagState.OFF, default_value=True))

    users = [("alice", ["beta"]), ("bob", []), ("charlie", ["user"]), ("dave", ["beta", "premium"])]
    for uid, groups in users:
        results = {
            "new_ui": engine.is_enabled("new_ui", uid, groups),
            "dark_mode": engine.is_enabled("dark_mode", uid, groups),
            "beta_api": engine.is_enabled("beta_api", uid, groups),
            "legacy_mode": engine.is_enabled("legacy_mode", uid, groups),
        }
        print(f"  {uid} ({groups}): {results}")

    # 2. Rollout progression
    print("\n[2] Rollout Progression")
    for pct in [0, 25, 50, 75, 100]:
        engine.flags.set_rollout("dark_mode", pct)
        hits = sum(1 for uid, _ in users if engine.is_enabled("dark_mode", uid))
        print(f"  Rollout {pct}%: {hits}/{len(users)} users enabled")

    # 3. Configuration
    print("\n[3] Configuration Management")
    engine.config.set("max_tokens", 4096, "int", "Max tokens per request")
    engine.config.set("temperature", 0.7, "float", "Sampling temperature")
    engine.config.set("model_name", "gpt-4", "string", "Default model")
    engine.config.set("streaming", True, "bool", "Enable streaming")
    print(f"  max_tokens = {engine.get_config('max_tokens')}")
    print(f"  temperature = {engine.get_config('temperature')}")
    print(f"  model_name = {engine.get_config('model_name')}")
    print(f"  streaming = {engine.get_config('streaming')}")

    # 4. Type validation
    print("\n[4] Type Validation")
    ok, msg = engine.config.set("bad_int", "not_a_number", "int")
    print(f"  bad_int validation: ok={ok}, msg={msg}")
    ok, msg = engine.config.set("good_int", "42", "int")
    print(f"  good_int validation: ok={ok}, value={engine.get_config('good_int')}")

    # 5. Immutable config
    print("\n[5] Immutable Config")
    engine.config.set("api_key", "secret123", "string", "API key", mutable=False)
    ok, msg = engine.config.set("api_key", "new_secret", "string")
    print(f"  Override immutable: ok={ok}, msg={msg}")

    # 6. Change log
    print("\n[6] Change Log")
    print(f"  Flag changes: {len(engine.flags.get_change_log())}")
    print(f"  Config changes: {len(engine.config.get_change_log())}")

    # 7. Export
    print("\n[7] Export")
    engine.export_all("/tmp/feature_flags.json")
    print(f"  Exported to /tmp/feature_flags.json")
    engine.flags.export("/tmp/flags_only.json")
    print(f"  Flags exported to /tmp/flags_only.json")

    # 8. Stats
    print("\n[8] Stats")
    print(f"  Flags: {len(engine.flags.list_all())} total, {len(engine.flags.list_enabled())} enabled")
    print(f"  Config: {engine.config.get_stats()}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
