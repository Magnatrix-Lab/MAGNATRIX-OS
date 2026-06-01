#!/usr/bin/env python3
"""Governance Policy Engine — Role-based rule evaluation with audit logging.

Pure-stdlib implementation supporting YAML-like rule parsing, policy versioning,
conflict resolution, and audit trails.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PolicyAction(Enum):
    """Possible policy evaluation outcomes."""
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


@dataclass
class PolicyRule:
    """A single governance rule."""
    name: str
    role: str
    resource: str
    action: str
    decision: PolicyAction
    priority: int = 0
    version: str = "1.0"
    conditions: Dict[str, Any] = field(default_factory=dict)


class PolicyEngine:
    """Parse, evaluate, version, and audit governance policies."""

    def __init__(self) -> None:
        """Initialize an empty policy engine."""
        self.rules: List[PolicyRule] = []
        self.audit_log: List[Dict[str, Any]] = []
        self.policy_version: str = "1.0.0"

    def parse_rule(self, rule_text: str) -> PolicyRule:
        """Parse a simple YAML-like rule into a ``PolicyRule``.

        Supports ``key: value`` pairs. ``conditions`` value is parsed as JSON.
        """
        data: Dict[str, Any] = {}
        for raw in rule_text.strip().splitlines():
            if ":" not in raw:
                continue
            key, val = raw.split(":", 1)
            key = key.strip()
            val = val.strip()
            if key == "priority":
                val = int(val)
            elif key == "decision":
                val = PolicyAction(val)
            elif key == "conditions":
                val = json.loads(val) if val else {}
            data[key] = val
        return PolicyRule(**data)

    def add_rule(self, rule: PolicyRule) -> None:
        """Register a rule in the engine."""
        self.rules.append(rule)

    def load_policy(self, policy_text: str, version: str = "1.0.0") -> None:
        """Load multiple rules separated by ``---`` and set policy version."""
        self.policy_version = version
        for block in policy_text.split("---"):
            block = block.strip()
            if block:
                self.add_rule(self.parse_rule(block))

    def evaluate(self, role: str, resource: str, action: str,
                 context: Optional[Dict[str, Any]] = None) -> PolicyAction:
        """Evaluate a request against all loaded rules.

        Returns the prevailing decision after conflict resolution.
        """
        context = context or {}
        matching = [r for r in self.rules if self._matches(r, role, resource, action, context)]

        if not matching:
            result = PolicyAction.DENY
        else:
            result = self._resolve_conflict(matching).decision

        self._log_audit(role, resource, action, result, context)
        return result

    def _matches(self, rule: PolicyRule, role: str, resource: str,
                 action: str, context: Dict[str, Any]) -> bool:
        """Check whether *rule* applies to the request."""
        if rule.role != "*" and rule.role != role:
            return False
        if rule.action != "*" and rule.action != action:
            return False
        if not self._resource_match(rule.resource, resource):
            return False
        for k, v in rule.conditions.items():
            if context.get(k) != v:
                return False
        return True

    @staticmethod
    def _resource_match(pattern: str, target: str) -> bool:
        """Support exact, prefix, and wildcard (``*``) resource matching."""
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            return target.startswith(pattern[:-1])
        return pattern == target

    def _resolve_conflict(self, rules: List[PolicyRule]) -> PolicyRule:
        """Pick the winning rule.

        Higher ``priority`` wins. On ties: ``DENY > ASK > ALLOW``.
        """
        def _score(r: PolicyRule) -> tuple:
            ds = {PolicyAction.DENY: 3, PolicyAction.ASK: 2, PolicyAction.ALLOW: 1}
            return (r.priority, ds.get(r.decision, 0))
        return max(rules, key=_score)

    def _log_audit(self, role: str, resource: str, action: str,
                   result: PolicyAction, context: Dict[str, Any]) -> None:
        """Record an audit entry with a timestamp."""
        self.audit_log.append({
            "timestamp": time.time(),
            "role": role,
            "resource": resource,
            "action": action,
            "result": result.value,
            "context": context,
            "policy_version": self.policy_version,
        })

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Return the full audit log."""
        return self.audit_log

    def run(self) -> None:
        """Self-test demonstrating all engine features."""
        print("=" * 50)
        print("PolicyEngine Self-Test")
        print("=" * 50)

        policy_yaml = """
name: admin-read
role: admin
resource: *
action: *
decision: allow
priority: 10
version: 1.0
conditions: {}
---
name: user-read
role: user
resource: /docs/*
action: read
decision: allow
priority: 5
version: 1.0
conditions: {}
---
name: user-write-deny
role: user
resource: /docs/secret
action: write
decision: deny
priority: 20
version: 1.0
conditions: {}
---
name: guest-ask
role: guest
resource: /docs/public
action: read
decision: ask
priority: 1
version: 1.0
conditions: {"ip_range": "10.0.0.0/8"}
---
name: user-write-ask
role: user
resource: /docs/secret
action: write
decision: ask
priority: 20
version: 1.0
conditions: {}
"""

        self.load_policy(policy_yaml, version="2.1.0")
        print(f"Loaded {len(self.rules)} rules (policy version {self.policy_version})")

        tests = [
            ("admin", "/docs/secret", "write", {}, PolicyAction.ALLOW),
            ("user", "/docs/report", "read", {}, PolicyAction.ALLOW),
            ("user", "/docs/secret", "write", {}, PolicyAction.DENY),
            ("guest", "/docs/public", "read", {"ip_range": "10.0.0.0/8"}, PolicyAction.ASK),
            ("guest", "/docs/public", "read", {"ip_range": "192.168.0.0/16"}, PolicyAction.DENY),
        ]

        for role, res, act, ctx, expected in tests:
            result = self.evaluate(role, res, act, ctx)
            status = "PASS" if result == expected else "FAIL"
            print(f"[{status}] {role} {act} {res} -> {result.value} (expected {expected.value})")

        print("-" * 50)
        print("Audit Log (last 3 entries):")
        for entry in self.get_audit_log()[-3:]:
            print(f"  {entry['role']} {entry['action']} {entry['resource']} => {entry['result']}")

        print("-" * 50)
        print("Conflict resolution test:")
        # user-write-deny (priority 20, DENY) vs user-write-ask (priority 20, ASK)
        # DENY should win because of tie-breaker
        conflict_result = self.evaluate("user", "/docs/secret", "write")
        print(f"  user write /docs/secret -> {conflict_result.value} (DENY wins tie)")
        print("=" * 50)
        print("Self-test complete.")


if __name__ == "__main__":
    engine = PolicyEngine()
    engine.run()
