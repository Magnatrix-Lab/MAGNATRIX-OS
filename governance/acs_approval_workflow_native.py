"""
ACS Approval Workflow — MAGNATRIX-OS Governance Layer
Human-in-the-loop escalation dengan timeout dan escalation chain.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Callable


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    ESCALATED = "escalated"


@dataclass
class ApprovalRequest:
    request_id: str
    actor: str
    action: Dict[str, Any]
    verdict_reason: str
    requested_at: float
    timeout_at: float
    status: ApprovalStatus = ApprovalStatus.PENDING
    approver: Optional[str] = None
    escalation_level: int = 0
    history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "actor": self.actor,
            "action": self.action,
            "verdict_reason": self.verdict_reason,
            "requested_at": self.requested_at,
            "timeout_at": self.timeout_at,
            "status": self.status.value,
            "approver": self.approver,
            "escalation_level": self.escalation_level,
            "history": self.history,
        }


class ApprovalQueue:
    """Queue dan manager untuk approval requests."""

    ESCALATION_DELAYS = [30.0, 300.0, 1800.0]  # 30s, 5min, 30min

    def __init__(self) -> None:
        self._pending: Dict[str, ApprovalRequest] = {}
        self._approved: Dict[str, ApprovalRequest] = {}
        self._denied: Dict[str, ApprovalRequest] = {}
        self._counter = 0
        self._lock = threading.Lock()
        self._notifiers: List[Callable[[ApprovalRequest], None]] = []

    def add_notifier(self, notifier: Callable[[ApprovalRequest], None]) -> None:
        self._notifiers.append(notifier)

    def request(self, actor: str, action: Dict[str, Any], verdict_reason: str,
                timeout_seconds: float = 300.0, metadata: Optional[Dict[str, Any]] = None) -> str:
        with self._lock:
            self._counter += 1
            req_id = f"req_{self._counter}_{int(time.time())}"
            req = ApprovalRequest(
                request_id=req_id,
                actor=actor,
                action=action,
                verdict_reason=verdict_reason,
                requested_at=time.time(),
                timeout_at=time.time() + timeout_seconds,
                status=ApprovalStatus.PENDING,
                metadata=metadata or {},
                history=[{"event": "created", "at": time.time()}],
            )
            self._pending[req_id] = req
        self._notify(req)
        return req_id

    def approve(self, request_id: str, approver: str) -> bool:
        with self._lock:
            if request_id not in self._pending:
                return False
            req = self._pending.pop(request_id)
            req.status = ApprovalStatus.APPROVED
            req.approver = approver
            req.history.append({"event": "approved", "by": approver, "at": time.time()})
            self._approved[request_id] = req
        return True

    def deny(self, request_id: str, approver: str, reason: str = "") -> bool:
        with self._lock:
            if request_id not in self._pending:
                return False
            req = self._pending.pop(request_id)
            req.status = ApprovalStatus.DENIED
            req.approver = approver
            req.history.append({"event": "denied", "by": approver, "reason": reason, "at": time.time()})
            self._denied[request_id] = req
        return True

    def escalate(self, request_id: str) -> bool:
        with self._lock:
            if request_id not in self._pending:
                return False
            req = self._pending[request_id]
            req.escalation_level += 1
            req.status = ApprovalStatus.ESCALATED
            req.history.append({"event": "escalated", "level": req.escalation_level, "at": time.time()})
            # Extend timeout
            if req.escalation_level < len(self.ESCALATION_DELAYS):
                req.timeout_at = time.time() + self.ESCALATION_DELAYS[req.escalation_level]
            req.history.append({"event": "timeout_extended", "new_timeout": req.timeout_at, "at": time.time()})
        self._notify(req)
        return True

    def check_expired(self) -> List[str]:
        """Check and expire timed-out requests. Returns expired IDs."""
        now = time.time()
        expired = []
        with self._lock:
            for req_id, req in list(self._pending.items()):
                if req.timeout_at < now:
                    req.status = ApprovalStatus.EXPIRED
                    req.history.append({"event": "expired", "at": time.time()})
                    self._denied[req_id] = self._pending.pop(req_id)
                    expired.append(req_id)
        return expired

    def get_pending(self) -> List[Dict[str, Any]]:
        self.check_expired()
        with self._lock:
            return [r.to_dict() for r in self._pending.values()]

    def get_status(self, request_id: str) -> Optional[ApprovalStatus]:
        for bucket in [self._pending, self._approved, self._denied]:
            if request_id in bucket:
                return bucket[request_id].status
        return None

    def _notify(self, req: ApprovalRequest) -> None:
        for notifier in self._notifiers:
            try:
                notifier(req)
            except Exception:
                pass

    def stats(self) -> Dict[str, int]:
        self.check_expired()
        return {
            "pending": len(self._pending),
            "approved": len(self._approved),
            "denied": len(self._denied),
        }


class EscalationBackend:
    """Backend untuk mengirim notifikasi escalation ke human operator."""

    def __init__(self) -> None:
        self._channels: List[Callable[[str, Dict[str, Any]], bool]] = []

    def add_channel(self, channel: Callable[[str, Dict[str, Any]], bool]) -> None:
        self._channels.append(channel)

    def notify(self, message: str, context: Dict[str, Any]) -> bool:
        sent = False
        for channel in self._channels:
            try:
                if channel(message, context):
                    sent = True
            except Exception:
                pass
        return sent

    def default_console_channel(self, message: str, context: Dict[str, Any]) -> bool:
        print(f"[ESCALATION] {message}")
        print(f"  Context: {context}")
        return True


class ApprovalManager:
    """High-level manager: queue + escalation backend."""

    def __init__(self) -> None:
        self.queue = ApprovalQueue()
        self.escalation = EscalationBackend()
        self.escalation.add_channel(self.escalation.default_console_channel)
        self.queue.add_notifier(self._on_new_request)

    def _on_new_request(self, req: ApprovalRequest) -> None:
        self.escalation.notify(
            f"Approval required: {req.request_id} from {req.actor}",
            req.to_dict(),
        )

    def request(self, actor: str, action: Dict[str, Any], reason: str) -> str:
        req_id = self.queue.request(actor, action, reason, timeout_seconds=30.0)
        return req_id

    def approve(self, request_id: str, approver: str) -> bool:
        return self.queue.approve(request_id, approver)

    def deny(self, request_id: str, approver: str, reason: str = "") -> bool:
        return self.queue.deny(request_id, approver, reason)

    def escalate(self, request_id: str) -> bool:
        return self.queue.escalate(request_id)

    def get_pending(self) -> List[Dict[str, Any]]:
        return self.queue.get_pending()

    def stats(self) -> Dict[str, Any]:
        return self.queue.stats()


def run():
    print("=" * 60)
    print("ACS Approval Workflow — Demo")
    print("=" * 60)

    manager = ApprovalManager()

    print("\n[1] Request approval")
    req_id = manager.request("agent_1", {"tool": "delete_database", "args": {}}, "High-risk action")
    print(f"   Request ID: {req_id}")
    print(f"   Pending: {manager.get_pending()}")

    print("\n[2] Approve")
    manager.approve(req_id, "human_admin")
    print(f"   Status: {manager.queue.get_status(req_id)}")

    print("\n[3] Deny another request")
    req_id2 = manager.request("agent_2", {"tool": "modify_kernel", "args": {}}, "Critical system action")
    manager.deny(req_id2, "human_admin", "Too risky")
    print(f"   Status: {manager.queue.get_status(req_id2)}")

    print(f"\n[4] Stats: {manager.stats()}")
    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
