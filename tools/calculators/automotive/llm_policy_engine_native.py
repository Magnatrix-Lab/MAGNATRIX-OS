"""Policy Engine — rule evaluation, RBAC, ABAC, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable
from enum import Enum, auto
import json

class PolicyEffect(Enum):
    ALLOW = auto()
    DENY = auto()

@dataclass
class PolicyRule:
    rule_id: str
    effect: PolicyEffect
    subjects: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)

class PolicyEngine:
    def __init__(self):
        self.rules: List[PolicyRule] = []
        self.default_effect = PolicyEffect.DENY

    def add_rule(self, rule: PolicyRule):
        self.rules.append(rule)

    def evaluate(self, subject: str, resource: str, action: str, context: Dict = None) -> PolicyEffect:
        context = context or {}
        for rule in self.rules:
            if not self._match(subject, rule.subjects):
                continue
            if not self._match(resource, rule.resources):
                continue
            if not self._match(action, rule.actions):
                continue
            if self._check_conditions(rule.conditions, context):
                return rule.effect
        return self.default_effect

    def _match(self, value: str, patterns: List[str]) -> bool:
        if not patterns:
            return True
        for p in patterns:
            if p == "*" or p == value:
                return True
            if p.endswith("*") and value.startswith(p[:-1]):
                return True
        return False

    def _check_conditions(self, conditions: Dict, context: Dict) -> bool:
        for key, expected in conditions.items():
            actual = context.get(key)
            if actual != expected:
                return False
        return True

    def is_allowed(self, subject: str, resource: str, action: str, context: Dict = None) -> bool:
        return self.evaluate(subject, resource, action, context) == PolicyEffect.ALLOW

    def stats(self) -> Dict:
        return {"rules": len(self.rules), "allow_rules": sum(1 for r in self.rules if r.effect == PolicyEffect.ALLOW), "deny_rules": sum(1 for r in self.rules if r.effect == PolicyEffect.DENY)}

def run():
    engine = PolicyEngine()
    engine.add_rule(PolicyRule("r1", PolicyEffect.ALLOW, ["admin"], ["*"], ["*"]))
    engine.add_rule(PolicyRule("r2", PolicyEffect.ALLOW, ["user"], ["resource_1"], ["read"]))
    engine.add_rule(PolicyRule("r3", PolicyEffect.DENY, ["*"], ["resource_1"], ["delete"]))
    print(engine.is_allowed("admin", "resource_1", "delete"))
    print(engine.is_allowed("user", "resource_1", "read"))
    print(engine.is_allowed("user", "resource_1", "delete"))
    print(engine.stats())

if __name__ == "__main__":
    run()
