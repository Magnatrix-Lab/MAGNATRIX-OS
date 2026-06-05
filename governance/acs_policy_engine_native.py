"""
ACS Policy Engine — MAGNATRIX-OS Governance Layer
Port dari Microsoft Agent Governance Toolkit (AGT) ACS.
Stateless, deterministic, fail-closed policy decision runtime.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Callable


class VerdictType(Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    TRANSFORM = "transform"
    ERROR = "error"


class PolicyType(Enum):
    CUSTOM = "custom"
    REGO = "rego"
    CEDAR = "cedar"


@dataclass
class Verdict:
    """Normalized verdict returned by ACS policy engine."""
    verdict_type: VerdictType
    reason: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    transform_output: Optional[Dict[str, Any]] = None
    policy_id: str = ""
    policy_version: str = ""
    timestamp: float = field(default_factory=time.time)

    def is_allowed(self) -> bool:
        return self.verdict_type == VerdictType.ALLOW

    def is_denied(self) -> bool:
        return self.verdict_type in (VerdictType.DENY, VerdictType.ERROR)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict_type.value,
            "reason": self.reason,
            "evidence": self.evidence,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "timestamp": self.timestamp,
        }


@dataclass
class PolicyRule:
    """Single policy rule within a policy bundle."""
    rule_id: str
    name: str
    description: str = ""
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    action: VerdictType = VerdictType.DENY
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def evaluate(self, snapshot: Dict[str, Any]) -> Optional[Verdict]:
        """Evaluate this rule against a snapshot. Returns verdict if matched, None if not applicable."""
        for condition in self.conditions:
            if not self._check_condition(condition, snapshot):
                return None
        return Verdict(
            verdict_type=self.action,
            reason=f"Rule matched: {self.name}",
            evidence={"matched_rule": self.rule_id, "conditions_met": len(self.conditions)},
            policy_id=self.rule_id,
        )

    def _check_condition(self, condition: Dict[str, Any], snapshot: Dict[str, Any]) -> bool:
        field = condition.get("field", "")
        op = condition.get("operator", "eq")
        value = condition.get("value")
        actual = self._get_field(snapshot, field)

        if op == "eq":
            return actual == value
        elif op == "ne":
            return actual != value
        elif op == "gt":
            return actual is not None and actual > value
        elif op == "gte":
            return actual is not None and actual >= value
        elif op == "lt":
            return actual is not None and actual < value
        elif op == "lte":
            return actual is not None and actual <= value
        elif op == "in":
            return actual in value if isinstance(value, (list, set, tuple)) else False
        elif op == "contains":
            return value in actual if actual and isinstance(actual, str) else False
        elif op == "exists":
            return actual is not None
        elif op == "regex":
            import re
            return bool(re.search(value, str(actual))) if actual else False
        return False

    def _get_field(self, snapshot: Dict[str, Any], path: str) -> Any:
        """Dot-notation field access: $.tool_call.name → snapshot['tool_call']['name']"""
        parts = path.replace("$.", "").split(".")
        current = snapshot
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current


@dataclass
class PolicyBundle:
    """Named policy bundle containing one or more rules."""
    bundle_id: str
    name: str
    policy_type: PolicyType = PolicyType.CUSTOM
    version: str = "1.0.0"
    rules: List[PolicyRule] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def evaluate(self, snapshot: Dict[str, Any]) -> Verdict:
        """Evaluate all rules in priority order. Return first match or default DENY."""
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)
        for rule in sorted_rules:
            result = rule.evaluate(snapshot)
            if result:
                result.policy_id = self.bundle_id
                result.policy_version = self.version
                return result
        return Verdict(
            verdict_type=VerdictType.DENY,
            reason="No policy rules matched — fail closed",
            evidence={"bundle_id": self.bundle_id, "rules_evaluated": len(self.rules)},
            policy_id=self.bundle_id,
            policy_version=self.version,
        )


class ACSPolicyEngine:
    """
    ACS Policy Engine — Stateless, Deterministic, Fail-Closed.

    Core contract (from Microsoft AGT):
    - Stateless: No mutable state between calls. Host supplies complete snapshot.
    - Deterministic: Same manifest + snapshot + mode = same verdict.
    - Fail-Closed: Runtime errors return DENY with reserved error reason.
    """

    def __init__(self) -> None:
        self._bundles: Dict[str, PolicyBundle] = {}
        self._default_verdict = VerdictType.DENY

    def load_bundle(self, bundle: PolicyBundle) -> None:
        """Load a policy bundle. Bundles are versioned and replaceable."""
        self._bundles[bundle.bundle_id] = bundle

    def unload_bundle(self, bundle_id: str) -> bool:
        return self._bundles.pop(bundle_id, None) is not None

    def evaluate(self, bundle_id: str, snapshot: Dict[str, Any]) -> Verdict:
        """
        Evaluate a snapshot against a loaded policy bundle.
        Stateless: snapshot is complete, no prior context needed.
        Deterministic: same inputs produce same output.
        Fail-closed: any error returns DENY.
        """
        try:
            bundle = self._bundles.get(bundle_id)
            if not bundle:
                return Verdict(
                    verdict_type=VerdictType.ERROR,
                    reason=f"Policy bundle '{bundle_id}' not found",
                    evidence={"error_type": "bundle_not_found", "available": list(self._bundles.keys())},
                )
            return bundle.evaluate(snapshot)
        except Exception as e:
            return Verdict(
                verdict_type=VerdictType.DENY,
                reason=f"Runtime error: {str(e)}",
                evidence={"error_type": "runtime_exception", "exception": str(e)},
            )

    def evaluate_all(self, snapshot: Dict[str, Any]) -> Dict[str, Verdict]:
        """Evaluate snapshot against all loaded bundles."""
        return {bid: self.evaluate(bid, snapshot) for bid in self._bundles}

    def compose_verdicts(self, verdicts: List[Verdict], composition: str = "all_allow") -> Verdict:
        """Compose multiple verdicts into a single verdict."""
        if composition == "all_allow":
            if all(v.is_allowed() for v in verdicts):
                return Verdict(verdict_type=VerdictType.ALLOW, reason="All policies allowed", evidence={"composition": "all_allow", "count": len(verdicts)})
            for v in verdicts:
                if not v.is_allowed():
                    return v
        elif composition == "any_allow":
            if any(v.is_allowed() for v in verdicts):
                return Verdict(verdict_type=VerdictType.ALLOW, reason="At least one policy allowed", evidence={"composition": "any_allow"})
            return Verdict(verdict_type=VerdictType.DENY, reason="All policies denied", evidence={"composition": "any_allow"})
        elif composition == "priority":
            if not verdicts:
                return Verdict(verdict_type=VerdictType.DENY, reason="No verdicts to compose")
            return verdicts[0]
        return Verdict(verdict_type=VerdictType.DENY, reason="Unknown composition strategy")

    def list_bundles(self) -> List[str]:
        return list(self._bundles.keys())

    def stats(self) -> Dict[str, Any]:
        return {
            "bundles_loaded": len(self._bundles),
            "total_rules": sum(len(b.rules) for b in self._bundles.values()),
            "engine_type": "ACS_PolicyEngine",
            "properties": ["stateless", "deterministic", "fail_closed"],
        }


def run():
    print("=" * 60)
    print("ACS Policy Engine — Demo")
    print("=" * 60)

    engine = ACSPolicyEngine()

    # Create a policy bundle for email tool
    email_bundle = PolicyBundle(
        bundle_id="email_policy",
        name="Email Agent Policy",
        version="1.0.0",
        rules=[
            PolicyRule(
                rule_id="r1",
                name="block_external_recipients",
                conditions=[{"field": "$.tool_call.args.recipient_domain", "operator": "ne", "value": "internal.corp"}],
                action=VerdictType.DENY,
                priority=100,
            ),
            PolicyRule(
                rule_id="r2",
                name="allow_internal_email",
                conditions=[{"field": "$.tool_call.args.recipient_domain", "operator": "eq", "value": "internal.corp"}],
                action=VerdictType.ALLOW,
                priority=50,
            ),
            PolicyRule(
                rule_id="r3",
                name="require_approval_for_mass_email",
                conditions=[{"field": "$.tool_call.args.recipient_count", "operator": "gt", "value": 10}],
                action=VerdictType.REQUIRE_APPROVAL,
                priority=90,
            ),
            PolicyRule(
                rule_id="r4",
                name="redact_pii_in_subject",
                conditions=[{"field": "$.tool_call.args.subject", "operator": "regex", "value": "SSN|\d{3}-\d{2}-\d{4}"}],
                action=VerdictType.TRANSFORM,
                priority=80,
            ),
        ],
    )

    engine.load_bundle(email_bundle)

    # Test snapshots
    snapshots = [
        {"tool_call": {"name": "send_email", "args": {"recipient_domain": "internal.corp", "recipient_count": 3, "subject": "Hello team"}}},
        {"tool_call": {"name": "send_email", "args": {"recipient_domain": "gmail.com", "recipient_count": 3, "subject": "Hello"}}},
        {"tool_call": {"name": "send_email", "args": {"recipient_domain": "internal.corp", "recipient_count": 50, "subject": "All-hands"}}},
        {"tool_call": {"name": "send_email", "args": {"recipient_domain": "internal.corp", "recipient_count": 3, "subject": "My SSN is 123-45-6789"}}},
    ]

    for i, snap in enumerate(snapshots, 1):
        result = engine.evaluate("email_policy", snap)
        print(f"\nCase {i}: {result.verdict_type.value} — {result.reason}")
        print(f"  Evidence: {result.evidence}")

    print(f"\nEngine stats: {engine.stats()}")
    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
