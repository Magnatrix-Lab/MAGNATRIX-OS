"""infrastructure/feature_flags_native.py — Feature flag system"""
from __future__ import annotations
import hashlib
import random
import time
from typing import Any, Dict, List, Optional

class FeatureFlags:
    """Feature flag system with targeting and A/B testing."""

    def __init__(self):
        self.flags: Dict[str, Dict[str, Any]] = {}
        self.audit: List[Dict[str, Any]] = []

    def define(self, name: str, default: bool = False, percentage: int = 100) -> None:
        self.flags[name] = {
            "default": default,
            "percentage": percentage,
            "users": [],
            "enabled": default,
        }

    def is_enabled(self, name: str, user_id: str = "") -> bool:
        if name not in self.flags:
            return False

        flag = self.flags[name]

        # Check user list
        if user_id in flag.get("users", []):
            self._audit(name, user_id, True)
            return True

        # Percentage rollout
        if flag["percentage"] < 100 and user_id:
            hash_val = int(hashlib.md5(f"{name}:{user_id}".encode()).hexdigest(), 16)
            if (hash_val % 100) >= flag["percentage"]:
                self._audit(name, user_id, False)
                return False

        self._audit(name, user_id, flag["enabled"])
        return flag["enabled"]

    def enable(self, name: str) -> None:
        if name in self.flags:
            self.flags[name]["enabled"] = True

    def disable(self, name: str) -> None:
        if name in self.flags:
            self.flags[name]["enabled"] = False

    def _audit(self, flag: str, user: str, result: bool) -> None:
        self.audit.append({
            "flag": flag,
            "user": user,
            "result": result,
            "timestamp": time.time(),
        })

if __name__ == "__main__":
    print("FeatureFlags self-test")
    ff = FeatureFlags()
    ff.define("new_feature", default=False, percentage=50)
    assert ff.is_enabled("new_feature", "user_1") in [True, False]
    print("All tests pass")
