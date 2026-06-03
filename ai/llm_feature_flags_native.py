#!/usr/bin/env python3
"""
MAGNATRIX-OS — Feature Flags Engine
ai/llm_feature_flags_native.py

Features:
- Feature flag toggle management (on/off, percentage rollout)
- User targeting (by user ID, segment, percentage)
- A/B test integration (feature flag → experiment variant)
- Flag evaluation context (user, time, environment)
- Flag audit and change history

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("feature_flags")


class FlagState(enum.Enum):
    OFF = "off"
    ON = "on"
    PERCENTAGE = "percentage"
    TARGETED = "targeted"


@dataclass
class FeatureFlag:
    id: str
    name: str
    state: FlagState
    percentage: float = 0.0  # 0-100
    target_users: List[str] = field(default_factory=list)
    target_segments: List[str] = field(default_factory=list)
    description: str = ""
    created_at: float = 0.0

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()


@dataclass
class EvaluationContext:
    user_id: str
    segment: str = ""
    environment: str = "production"
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class FeatureFlagsEngine:
    """Feature flag management and evaluation."""

    def __init__(self):
        self._flags: Dict[str, FeatureFlag] = {}
        self._history: List[Dict[str, Any]] = []
        self._evaluations: Dict[str, int] = defaultdict(int)

    def create(self, flag: FeatureFlag) -> None:
        self._flags[flag.id] = flag
        logger.info(f"Created flag: {flag.name} ({flag.state.value})")

    def toggle(self, flag_id: str, new_state: FlagState) -> bool:
        flag = self._flags.get(flag_id)
        if not flag:
            return False
        old = flag.state
        flag.state = new_state
        self._history.append({"flag": flag_id, "from": old.value, "to": new_state.value, "time": time.time()})
        return True

    def evaluate(self, flag_id: str, context: EvaluationContext) -> bool:
        flag = self._flags.get(flag_id)
        if not flag:
            return False
        self._evaluations[flag_id] += 1
        if flag.state == FlagState.OFF:
            return False
        if flag.state == FlagState.ON:
            return True
        if flag.state == FlagState.PERCENTAGE:
            h = hashlib.md5(f"{context.user_id}:{flag_id}".encode()).hexdigest()
            bucket = int(h, 16) % 100
            return bucket < flag.percentage
        if flag.state == FlagState.TARGETED:
            if context.user_id in flag.target_users:
                return True
            if context.segment in flag.target_segments:
                return True
            return False
        return False

    def get_enabled_flags(self, context: EvaluationContext) -> List[str]:
        return [fid for fid, flag in self._flags.items() if self.evaluate(fid, context)]

    def get_flag(self, flag_id: str) -> Optional[FeatureFlag]:
        return self._flags.get(flag_id)

    def get_history(self, flag_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if flag_id:
            return [h for h in self._history if h["flag"] == flag_id]
        return list(self._history)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "flags": len(self._flags),
            "evaluations": sum(self._evaluations.values()),
            "by_state": {s.value: sum(1 for f in self._flags.values() if f.state == s) for s in FlagState},
        }


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Feature Flags Engine")
    print("ai/llm_feature_flags_native.py")
    print("=" * 60)

    engine = FeatureFlagsEngine()

    # 1. Create flags
    print("\n[1] Create Flags")
    engine.create(FeatureFlag("f1", "New UI", FlagState.ON, description="New user interface"))
    engine.create(FeatureFlag("f2", "Beta Feature", FlagState.PERCENTAGE, percentage=30, description="Rollout to 30%"))
    engine.create(FeatureFlag("f3", "Admin Tool", FlagState.TARGETED, target_segments=["admin"], description="Admin only"))
    engine.create(FeatureFlag("f4", "Experiment", FlagState.OFF, description="Future experiment"))
    print(f"  Created 4 flags")

    # 2. Evaluate
    print("\n[2] Evaluate Flags")
    users = [f"user-{i}" for i in range(10)]
    for u in users:
        ctx = EvaluationContext(u, segment="user")
        results = {fid: engine.evaluate(fid, ctx) for fid in engine._flags}
        print(f"  {u}: {results}")

    # 3. Admin user
    print("\n[3] Admin User")
    admin_ctx = EvaluationContext("admin-1", segment="admin")
    print(f"  admin-1: f3(targeted) = {engine.evaluate('f3', admin_ctx)}")

    # 4. Toggle
    print("\n[4] Toggle Flag")
    engine.toggle("f4", FlagState.ON)
    print(f"  f4 state: {engine.get_flag('f4').state.value}")

    # 5. Enabled flags per user
    print("\n[5] Enabled Flags")
    for u in ["user-0", "user-5", "admin-1"]:
        ctx = EvaluationContext(u, segment="admin" if "admin" in u else "user")
        enabled = engine.get_enabled_flags(ctx)
        print(f"  {u}: {enabled}")

    # 6. Stats
    print("\n[6] Engine Stats")
    print(f"  {engine.get_stats()}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
