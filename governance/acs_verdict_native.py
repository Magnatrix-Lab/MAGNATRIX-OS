"""
ACS Verdict Types — MAGNATRIX-OS Governance Layer
Verdict composition, transform, evidence, dan approval workflow.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Callable


class VerdictType(Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    TRANSFORM = "transform"
    ERROR = "error"


@dataclass
class VerdictEvidence:
    """Structured evidence untuk audit trail."""
    policy_id: str = ""
    matched_rules: List[str] = field(default_factory=list)
    snapshot_hash: str = ""
    context_fields: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "matched_rules": self.matched_rules,
            "snapshot_hash": self.snapshot_hash,
            "context_fields": self.context_fields,
            "timestamp": self.timestamp,
        }


@dataclass
class Verdict:
    """ACS normalized verdict dengan evidence."""
    verdict_type: VerdictType
    reason: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    transform_output: Optional[Dict[str, Any]] = None
    policy_id: str = ""
    policy_version: str = ""
    timestamp: float = field(default_factory=time.time)
    approval_escalation: Optional[Dict[str, Any]] = None

    def is_allowed(self) -> bool:
        return self.verdict_type == VerdictType.ALLOW

    def is_denied(self) -> bool:
        return self.verdict_type in (VerdictType.DENY, VerdictType.ERROR)

    def requires_approval(self) -> bool:
        return self.verdict_type == VerdictType.REQUIRE_APPROVAL

    def requires_transform(self) -> bool:
        return self.verdict_type == VerdictType.TRANSFORM

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict_type.value,
            "reason": self.reason,
            "evidence": self.evidence,
            "transform_output": self.transform_output,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "timestamp": self.timestamp,
            "approval_escalation": self.approval_escalation,
        }


class VerdictComposer:
    """Compose multiple verdicts menjadi single verdict."""

    @staticmethod
    def all_must_allow(verdicts: List[Verdict]) -> Verdict:
        if all(v.is_allowed() for v in verdicts):
            return Verdict(
                verdict_type=VerdictType.ALLOW,
                reason="All policies allowed",
                evidence={"composition": "all_allow", "count": len(verdicts), "verdicts": [v.verdict_type.value for v in verdicts]},
            )
        for v in verdicts:
            if not v.is_allowed():
                return v
        return Verdict(verdict_type=VerdictType.DENY, reason="Unknown composition error")

    @staticmethod
    def any_may_allow(verdicts: List[Verdict]) -> Verdict:
        if any(v.is_allowed() for v in verdicts):
            return Verdict(
                verdict_type=VerdictType.ALLOW,
                reason="At least one policy allowed",
                evidence={"composition": "any_allow", "verdicts": [v.verdict_type.value for v in verdicts]},
            )
        return Verdict(
            verdict_type=VerdictType.DENY,
            reason="All policies denied",
            evidence={"composition": "any_allow", "verdicts": [v.verdict_type.value for v in verdicts]},
        )

    @staticmethod
    def priority_order(verdicts: List[Verdict]) -> Verdict:
        if not verdicts:
            return Verdict(verdict_type=VerdictType.DENY, reason="No verdicts to compose")
        return verdicts[0]

    @staticmethod
    def weighted_majority(verdicts: List[Verdict], weights: List[float]) -> Verdict:
        allow_weight = sum(w for v, w in zip(verdicts, weights) if v.is_allowed())
        deny_weight = sum(w for v, w in zip(verdicts, weights) if not v.is_allowed())
        if allow_weight > deny_weight:
            return Verdict(verdict_type=VerdictType.ALLOW, reason=f"Weighted majority allow ({allow_weight:.1f} vs {deny_weight:.1f})")
        return Verdict(verdict_type=VerdictType.DENY, reason=f"Weighted majority deny ({deny_weight:.1f} vs {allow_weight:.1f})")


class TransformEngine:
    """Engine untuk transform verdict (e.g., redact PII, mask data)."""

    @staticmethod
    def redact_pii(text: str, pii_patterns: Optional[List[str]] = None) -> str:
        import re
        patterns = pii_patterns or [
            (r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED-SSN]"),
            (r"\b\d{4}-\d{4}-\d{4}-\d{4}\b", "[REDACTED-CC]"),
            (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}", "[REDACTED-EMAIL]"),
        ]
        result = text
        for pattern, replacement in patterns:
            result = re.sub(pattern, replacement, result)
        return result

    @staticmethod
    def mask_fields(data: Dict[str, Any], sensitive_fields: List[str]) -> Dict[str, Any]:
        result = {}
        for key, value in data.items():
            if key in sensitive_fields:
                result[key] = "[MASKED]"
            elif isinstance(value, dict):
                result[key] = TransformEngine.mask_fields(value, sensitive_fields)
            else:
                result[key] = value
        return result

    @staticmethod
    def apply_transform(original: Dict[str, Any], transform_spec: Dict[str, Any]) -> Dict[str, Any]:
        action = transform_spec.get("action", "none")
        if action == "redact_pii":
            text = str(original.get("text", ""))
            return {"text": TransformEngine.redact_pii(text)}
        elif action == "mask_fields":
            fields = transform_spec.get("fields", [])
            return TransformEngine.mask_fields(original, fields)
        elif action == "truncate":
            max_len = transform_spec.get("max_length", 100)
            text = str(original.get("text", ""))
            return {"text": text[:max_len] + "..." if len(text) > max_len else text}
        return original


class ApprovalQueue:
    """Queue untuk approval requests (require_approval verdict)."""

    def __init__(self) -> None:
        self._pending: Dict[str, Dict[str, Any]] = {}
        self._approved: Dict[str, Dict[str, Any]] = {}
        self._denied: Dict[str, Dict[str, Any]] = {}
        self._counter = 0

    def request(self, verdict: Verdict, actor: str, action: Dict[str, Any], timeout_seconds: float = 300.0) -> str:
        self._counter += 1
        req_id = f"approval_{self._counter}_{int(time.time())}"
        self._pending[req_id] = {
            "request_id": req_id,
            "verdict": verdict.to_dict(),
            "actor": actor,
            "action": action,
            "requested_at": time.time(),
            "timeout_at": time.time() + timeout_seconds,
            "status": "pending",
        }
        return req_id

    def approve(self, request_id: str, approver: str) -> bool:
        if request_id not in self._pending:
            return False
        req = self._pending.pop(request_id)
        req["status"] = "approved"
        req["approved_by"] = approver
        req["approved_at"] = time.time()
        self._approved[request_id] = req
        return True

    def deny(self, request_id: str, approver: str, reason: str = "") -> bool:
        if request_id not in self._pending:
            return False
        req = self._pending.pop(request_id)
        req["status"] = "denied"
        req["denied_by"] = approver
        req["denied_at"] = time.time()
        req["reason"] = reason
        self._denied[request_id] = req
        return True

    def get_pending(self) -> List[Dict[str, Any]]:
        now = time.time()
        expired = [k for k, v in self._pending.items() if v["timeout_at"] < now]
        for k in expired:
            self._pending[k]["status"] = "expired"
            self._denied[k] = self._pending.pop(k)
        return list(self._pending.values())

    def stats(self) -> Dict[str, int]:
        return {
            "pending": len(self._pending),
            "approved": len(self._approved),
            "denied": len(self._denied),
        }


def run():
    print("=" * 60)
    print("ACS Verdict Types — Demo")
    print("=" * 60)

    # Composition demo
    v1 = Verdict(verdict_type=VerdictType.ALLOW, reason="Rule A passed")
    v2 = Verdict(verdict_type=VerdictType.ALLOW, reason="Rule B passed")
    v3 = Verdict(verdict_type=VerdictType.DENY, reason="Rule C failed")

    print("\n[1] Composition: all_must_allow")
    composed = VerdictComposer.all_must_allow([v1, v2])
    print(f"   Result: {composed.verdict_type.value}")
    composed = VerdictComposer.all_must_allow([v1, v2, v3])
    print(f"   Result: {composed.verdict_type.value} — {composed.reason}")

    print("\n[2] Transform: redact PII")
    text = "Contact me at john@example.com or SSN 123-45-6789"
    redacted = TransformEngine.redact_pii(text)
    print(f"   Original: {text}")
    print(f"   Redacted: {redacted}")

    print("\n[3] Approval queue")
    queue = ApprovalQueue()
    req_id = queue.request(Verdict(verdict_type=VerdictType.REQUIRE_APPROVAL, reason="High risk action"), "agent_1", {"tool": "delete_db"})
    print(f"   Requested: {req_id}")
    print(f"   Pending: {queue.get_pending()}")
    queue.approve(req_id, "human_admin")
    print(f"   Stats: {queue.stats()}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
