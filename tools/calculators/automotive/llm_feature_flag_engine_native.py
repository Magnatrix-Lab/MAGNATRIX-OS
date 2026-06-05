"""Feature Flag Engine — toggle management, rollout, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any
from enum import Enum, auto
import random
import hashlib
import time

class RolloutType(Enum):
    BOOLEAN = auto()
    PERCENTAGE = auto()
    USER_TARGET = auto()

@dataclass
class FeatureFlag:
    flag_id: str
    enabled: bool
    rollout_type: RolloutType
    percentage: float = 0.0
    target_users: List[str] = field(default_factory=list)
    rules: List[Dict] = field(default_factory=list)

class FeatureFlagEngine:
    def __init__(self):
        self.flags: Dict[str, FeatureFlag] = {}
        self.evaluations: List[Dict] = []

    def create_flag(self, flag_id: str, enabled: bool, rollout_type: RolloutType = RolloutType.BOOLEAN, percentage: float = 0.0, target_users: List[str] = None):
        self.flags[flag_id] = FeatureFlag(flag_id, enabled, rollout_type, percentage, target_users or [])

    def is_enabled(self, flag_id: str, user_id: str = None, context: Dict = None) -> bool:
        flag = self.flags.get(flag_id)
        if not flag:
            return False
        if not flag.enabled:
            self.evaluations.append({"flag": flag_id, "user": user_id, "result": False})
            return False
        if flag.rollout_type == RolloutType.BOOLEAN:
            result = True
        elif flag.rollout_type == RolloutType.PERCENTAGE:
            h = hashlib.md5((flag_id + (user_id or "")).encode()).hexdigest()
            bucket = int(h, 16) % 100
            result = bucket < flag.percentage
        elif flag.rollout_type == RolloutType.USER_TARGET:
            result = user_id in flag.target_users if user_id else False
        else:
            result = False
        self.evaluations.append({"flag": flag_id, "user": user_id, "result": result})
        return result

    def toggle(self, flag_id: str):
        flag = self.flags.get(flag_id)
        if flag:
            flag.enabled = not flag.enabled

    def set_percentage(self, flag_id: str, pct: float):
        flag = self.flags.get(flag_id)
        if flag:
            flag.percentage = max(0, min(100, pct))

    def stats(self) -> Dict:
        enabled_count = sum(1 for f in self.flags.values() if f.enabled)
        return {"flags": len(self.flags), "enabled": enabled_count, "evaluations": len(self.evaluations)}

def run():
    engine = FeatureFlagEngine()
    engine.create_flag("new_ui", True, RolloutType.PERCENTAGE, 50)
    engine.create_flag("beta_api", True, RolloutType.USER_TARGET, target_users=["user1", "user2"])
    for i in range(10):
        print(f"user{i}: new_ui={engine.is_enabled('new_ui', f'user{i}')}")
    print("user1 beta:", engine.is_enabled("beta_api", "user1"))
    print(engine.stats())

if __name__ == "__main__":
    run()
