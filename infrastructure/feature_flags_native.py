"""
MAGNATRIX-OS Feature Flags System
Self-contained native feature flag manager with targeting, A/B testing,
rollout, audit, and import/export.
"""

import json, hashlib, random
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field, asdict


@dataclass
class FlagRule:
    """Targeting rule for a feature flag."""
    type: str          # "percent", "list", "attribute"
    value: Any         # 0-100, [user_ids], {attr: value}
    negate: bool = False


@dataclass
class FlagDef:
    """Definition of a feature flag."""
    name: str
    default: bool = False
    rules: List[FlagRule] = field(default_factory=list)
    rollout: int = 0          # 0-100 gradual rollout
    ab_groups: List[str] = field(default_factory=list)  # A/B test group names
    metadata: Dict[str, Any] = field(default_factory=dict)


class FeatureFlags:
    """Feature flag system for MAGNATRIX-OS."""

    def __init__(self):
        self._flags: Dict[str, FlagDef] = {}
        self._audit: List[Dict] = []
        self._eval_cache: Dict[str, Dict[str, bool]] = {}

    # ── flag definition ───────────────────────────────────────

    def define(self, name: str, default: bool = False, rules: List[Dict] = None,
               rollout: int = 0, ab_groups: List[str] = None,
               metadata: Dict = None) -> None:
        self._flags[name] = FlagDef(
            name=name, default=default,
            rules=[FlagRule(**r) for r in (rules or [])],
            rollout=max(0, min(100, rollout)),
            ab_groups=ab_groups or [],
            metadata=metadata or {}
        )
        self._log("define", name=name, default=default)

    def remove(self, name: str) -> None:
        if name in self._flags:
            del self._flags[name]
            self._log("remove", name=name)

    def list_flags(self) -> List[str]:
        return list(self._flags.keys())

    def get_def(self, name: str) -> Optional[Dict]:
        f = self._flags.get(name)
        if not f:
            return None
        return self._flag_to_dict(f)

    def _flag_to_dict(self, f: FlagDef) -> Dict:
        return {
            "name": f.name, "default": f.default,
            "rules": [asdict(r) for r in f.rules],
            "rollout": f.rollout, "ab_groups": f.ab_groups,
            "metadata": f.metadata
        }

    # ── evaluation ────────────────────────────────────────────

    def evaluate(self, flag_name: str, user_id: str = "", user_attrs: Dict = None) -> bool:
        user_attrs = user_attrs or {}
        flag = self._flags.get(flag_name)
        if not flag:
            return False
        result = flag.default
        # rollout check
        if flag.rollout > 0:
            bucket = self._hash_bucket(flag_name, user_id)
            if bucket >= flag.rollout:
                result = False
            else:
                result = True
        # rules evaluation
        for rule in flag.rules:
            match = self._match_rule(rule, user_id, user_attrs)
            if match:
                result = not rule.negate
            elif rule.negate and not match:
                result = True
        self._log("evaluate", flag=flag_name, user=user_id, result=result)
        return result

    def evaluate_all(self, user_id: str = "", user_attrs: Dict = None) -> Dict[str, bool]:
        return {name: self.evaluate(name, user_id, user_attrs) for name in self._flags}

    def _hash_bucket(self, flag_name: str, user_id: str) -> int:
        h = hashlib.md5(f"{flag_name}:{user_id}".encode()).hexdigest()
        return int(h, 16) % 100

    def _match_rule(self, rule: FlagRule, user_id: str, user_attrs: Dict) -> bool:
        if rule.type == "percent":
            return self._hash_bucket(rule.type, user_id) < rule.value
        elif rule.type == "list":
            return user_id in rule.value
        elif rule.type == "attribute":
            for k, v in rule.value.items():
                if user_attrs.get(k) == v:
                    return True
            return False
        return False

    # ── A/B testing ──────────────────────────────────────────

    def ab_group(self, flag_name: str, user_id: str) -> Optional[str]:
        flag = self._flags.get(flag_name)
        if not flag or not flag.ab_groups:
            return None
        h = int(hashlib.md5(f"ab:{flag_name}:{user_id}".encode()).hexdigest(), 16)
        return flag.ab_groups[h % len(flag.ab_groups)]

    def ab_test(self, flag_name: str, user_id: str) -> Dict:
        group = self.ab_group(flag_name, user_id)
        enabled = self.evaluate(flag_name, user_id)
        return {"flag": flag_name, "group": group, "enabled": enabled}

    # ── gradual rollout ──────────────────────────────────────

    def set_rollout(self, flag_name: str, percent: int) -> None:
        flag = self._flags.get(flag_name)
        if flag:
            flag.rollout = max(0, min(100, percent))
            self._log("rollout", flag=flag_name, percent=flag.rollout)

    def bump_rollout(self, flag_name: str, step: int = 10) -> None:
        flag = self._flags.get(flag_name)
        if flag:
            flag.rollout = min(100, flag.rollout + step)
            self._log("rollout_bump", flag=flag_name, percent=flag.rollout)

    # ── audit log ────────────────────────────────────────────

    def _log(self, action: str, **kwargs) -> None:
        self._audit.append({"time": datetime.now().isoformat(), "action": action, **kwargs})

    def audit_log(self, flag_name: str = "") -> List[Dict]:
        if flag_name:
            return [e for e in self._audit if e.get("flag") == flag_name or e.get("name") == flag_name]
        return self._audit.copy()

    # ── import/export ─────────────────────────────────────────

    def export_json(self) -> str:
        return json.dumps({name: self._flag_to_dict(f) for name, f in self._flags.items()}, indent=2)

    def import_json(self, data: str) -> None:
        parsed = json.loads(data)
        for name, fd in parsed.items():
            self.define(name, **{k: v for k, v in fd.items() if k != "name"})

    def export_file(self, path: str) -> None:
        with open(path, "w") as f:
            f.write(self.export_json())

    def import_file(self, path: str) -> None:
        with open(path) as f:
            self.import_json(f.read())


# ── self-test ─────────────────────────────────────────────────

def _self_test():
    ff = FeatureFlags()

    # define flag
    ff.define("dark_mode", default=False, rollout=50)
    assert "dark_mode" in ff.list_flags()

    # evaluate with rollout
    on_count = sum(ff.evaluate("dark_mode", f"user_{i}") for i in range(1000))
    assert 400 < on_count < 600  # ~50%

    # user targeting by list
    ff.define("beta_users", default=False, rules=[{"type": "list", "value": ["u1", "u2"], "negate": False}])
    assert ff.evaluate("beta_users", "u1") is True
    assert ff.evaluate("beta_users", "u3") is False

    # attribute targeting
    ff.define("premium", default=False, rules=[{"type": "attribute", "value": {"plan": "pro"}, "negate": False}])
    assert ff.evaluate("premium", "u", {"plan": "pro"}) is True
    assert ff.evaluate("premium", "u", {"plan": "free"}) is False

    # A/B test
    ff.define("new_ui", default=False, ab_groups=["control", "variant_a", "variant_b"])
    groups = {ff.ab_group("new_ui", f"user_{i}") for i in range(100)}
    assert groups == {"control", "variant_a", "variant_b"}

    # gradual rollout bump
    ff.set_rollout("dark_mode", 30)
    assert ff.get_def("dark_mode")["rollout"] == 30
    ff.bump_rollout("dark_mode", 20)
    assert ff.get_def("dark_mode")["rollout"] == 50

    # audit log
    assert len(ff.audit_log()) > 0
    assert len(ff.audit_log("dark_mode")) > 0

    # import/export
    exported = ff.export_json()
    ff2 = FeatureFlags()
    ff2.import_json(exported)
    assert ff2.list_flags() == ff.list_flags()

    print("[feature_flags_native] all tests passed")


if __name__ == "__main__":
    _self_test()
