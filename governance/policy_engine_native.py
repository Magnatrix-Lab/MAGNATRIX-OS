"""governance/policy_engine_native.py — Governance policy engine"""
from __future__ import annotations
import json
import time
from typing import Any, Dict, List, Optional

class PolicyEngine:
    """Evaluate governance policies with rule-based engine."""

    def __init__(self):
        self.policies: Dict[str, Dict[str, Any]] = {}
        self.audit_log: List[Dict[str, Any]] = []

    def add_policy(self, name: str, rules: Dict[str, Any]) -> None:
        self.policies[name] = {
            "rules": rules,
            "version": 1,
            "created": time.time(),
        }

    def evaluate(self, subject: str, action: str, resource: str, context: Optional[Dict] = None) -> str:
        """Evaluate policy. Returns: allow, deny, or ask."""
        for name, policy in self.policies.items():
            rules = policy["rules"]
            if action in rules.get("allow", []):
                self._audit(subject, action, resource, "allow", name)
                return "allow"
            if action in rules.get("deny", []):
                self._audit(subject, action, resource, "deny", name)
                return "deny"

        self._audit(subject, action, resource, "ask", "default")
        return "ask"

    def _audit(self, subject: str, action: str, resource: str, result: str, policy: str) -> None:
        self.audit_log.append({
            "subject": subject,
            "action": action,
            "resource": resource,
            "result": result,
            "policy": policy,
            "timestamp": time.time(),
        })

    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self.audit_log[-limit:]

if __name__ == "__main__":
    print("PolicyEngine self-test")
    pe = PolicyEngine()
    pe.add_policy("access", {"allow": ["read"], "deny": ["delete"]})
    assert pe.evaluate("user", "read", "file") == "allow"
    assert pe.evaluate("user", "delete", "file") == "deny"
    print("All tests pass")
