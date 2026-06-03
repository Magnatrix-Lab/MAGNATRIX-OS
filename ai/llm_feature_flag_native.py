"""LLM Feature Flag — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class RolloutStrategy(Enum):
    ALL = auto()
    PERCENTAGE = auto()
    USER_LIST = auto()
    TIME_BASED = auto()

@dataclass
class FeatureFlag:
    id: str
    name: str
    enabled: bool = False
    strategy: RolloutStrategy = RolloutStrategy.ALL
    percentage: float = 100.0
    user_list: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class FeatureFlagManager:
    def __init__(self) -> None:
        self._flags: Dict[str, FeatureFlag] = {}

    def register(self, flag: FeatureFlag) -> None:
        self._flags[flag.id] = flag

    def is_enabled(self, flag_id: str, user_id: Optional[str] = None) -> bool:
        flag = self._flags.get(flag_id)
        if not flag:
            return False
        if not flag.enabled:
            return False
        if flag.strategy == RolloutStrategy.ALL:
            return True
        elif flag.strategy == RolloutStrategy.PERCENTAGE:
            import hashlib
            h = hashlib.md5((flag_id + (user_id or "")).encode()).hexdigest()
            return int(h, 16) % 100 < flag.percentage
        elif flag.strategy == RolloutStrategy.USER_LIST:
            return user_id in flag.user_list if user_id else False
        return False

    def toggle(self, flag_id: str) -> bool:
        flag = self._flags.get(flag_id)
        if flag:
            flag.enabled = not flag.enabled
            return flag.enabled
        return False

    def get_stats(self) -> Dict[str, Any]:
        return {"total": len(self._flags), "enabled": sum(1 for f in self._flags.values() if f.enabled)}

def run() -> None:
    print("Feature Flag test")
    e = FeatureFlagManager()
    e.register(FeatureFlag("f1", "new_ui", True, RolloutStrategy.ALL))
    e.register(FeatureFlag("f2", "beta_feature", True, RolloutStrategy.PERCENTAGE, 50.0))
    e.register(FeatureFlag("f3", "admin_only", True, RolloutStrategy.USER_LIST, user_list=["admin1", "admin2"]))
    print("  f1 enabled: " + str(e.is_enabled("f1")))
    print("  f2 for user1: " + str(e.is_enabled("f2", "user1")))
    print("  f3 for admin1: " + str(e.is_enabled("f3", "admin1")))
    e.toggle("f1")
    print("  f1 after toggle: " + str(e.is_enabled("f1")))
    print("  Stats: " + str(e.get_stats()))
    print("Feature Flag test complete.")

if __name__ == "__main__":
    run()
