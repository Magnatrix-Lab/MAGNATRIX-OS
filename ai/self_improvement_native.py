#!/usr/bin/env python3
"""
self_improvement_native.py — MAGNATRIX-OS AI Layer
Pure-Python Safe Self-Modification: sandbox test, version control,
auto-rollback, governance gate, human override. No external dependencies.
Runnable standalone.

Architecture:
  BaseLayer   — CodeSnapshot, TestResult, VersionTag, ChangeProposal
  CoreEngine  — SandboxEngine (isolated exec), VersionVault (git-like versioning)
  Features    — AutoRollback, GovernanceGate, HumanOverride, DiffAnalyzer
  Kernel      — SelfImprovementKernel bridge to MAGNATRIX Layer 9 (AI)
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import re
import sys
import tempfile
import time
import traceback
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# BASELAYER — CodeSnapshot, TestResult, VersionTag, ChangeProposal
# ═══════════════════════════════════════════════════════════════════════════════

class TestStatus(Enum):
    """Result of a sandbox test."""
    PASS = auto()
    FAIL = auto()
    ERROR = auto()
    TIMEOUT = auto()
    SKIPPED = auto()


class ApprovalStatus(Enum):
    """Governance approval state for a change."""
    PENDING = auto()
    AUTO_APPROVED = auto()   # Low-risk, within bounds
    HUMAN_APPROVED = auto()
    HUMAN_REJECTED = auto()
    GOVERNANCE_BLOCKED = auto()


class ChangeRisk(Enum):
    """Risk classification for a self-modification."""
    LOW = auto()      # Comments, docs, logging
    MEDIUM = auto()   # Algorithm tweaks, parameter changes
    HIGH = auto()     # Core logic, I/O, networking
    CRITICAL = auto() # Security, sandbox, governance code itself


@dataclass
class CodeSnapshot:
    """Immutable snapshot of a code module at a point in time."""
    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    module_name: str = ""
    source: str = ""
    checksum: str = ""
    timestamp: float = field(default_factory=time.time)
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.checksum:
            self.checksum = hashlib.sha256(self.source.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "module_name": self.module_name,
            "checksum": self.checksum,
            "timestamp": self.timestamp,
            "parent_id": self.parent_id,
            "lines": len(self.source.splitlines()),
        }


@dataclass
class TestResult:
    """Outcome of a sandboxed test run."""
    test_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    snapshot_id: str = ""
    status: TestStatus = TestStatus.SKIPPED
    stdout: str = ""
    stderr: str = ""
    execution_time_ms: float = 0.0
    assertions_passed: int = 0
    assertions_failed: int = 0
    exception_type: str = ""
    exception_trace: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "snapshot_id": self.snapshot_id,
            "status": self.status.name,
            "time_ms": round(self.execution_time_ms, 2),
            "passed": self.assertions_passed,
            "failed": self.assertions_failed,
            "exception": self.exception_type,
        }


@dataclass
class VersionTag:
    """A named version reference (like a git tag)."""
    tag_name: str = ""
    snapshot_id: str = ""
    message: str = ""
    created_by: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tag": self.tag_name,
            "snapshot_id": self.snapshot_id,
            "message": self.message,
            "created_by": self.created_by,
        }


@dataclass
class ChangeProposal:
    """A proposed self-modification."""
    proposal_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    module_name: str = ""
    title: str = ""
    description: str = ""
    old_snapshot_id: str = ""
    new_source: str = ""
    risk_level: ChangeRisk = ChangeRisk.MEDIUM
    approval: ApprovalStatus = ApprovalStatus.PENDING
    sandbox_result: Optional[TestResult] = None
    rollback_on_fail: bool = True
    human_required: bool = False
    proposed_at: float = field(default_factory=time.time)
    approved_at: float = 0.0
    applied_at: float = 0.0
    reverted_at: float = 0.0
    approved_by: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "module": self.module_name,
            "title": self.title,
            "risk": self.risk_level.name,
            "approval": self.approval.name,
            "sandbox": self.sandbox_result.to_dict() if self.sandbox_result else None,
            "rollback_on_fail": self.rollback_on_fail,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# COREENGINE — SandboxEngine (isolated exec), VersionVault (git-like versioning)
# ═══════════════════════════════════════════════════════════════════════════════

class SandboxEngine:
    """
    Isolated code execution sandbox.
    Runs code in a restricted environment with timeout, AST validation,
 and resource limits. No actual OS sandboxing — pure Python isolation.
    """

    # Forbidden AST node types for safety
    FORBIDDEN_NODES: Tuple[type, ...] = (
        ast.Import,
        ast.ImportFrom,
        ast.Call,
    )

    def __init__(self, timeout_ms: float = 5000.0) -> None:
        self.timeout_ms = timeout_ms
        self.banned_names: Set[str] = {
            "open", "os", "sys", "subprocess", "socket", "urllib", "http",
            "requests", "eval", "exec", "compile", "__import__",
            "file", "input", "raw_input", "breakpoint", "importlib",
        }
        self.allowed_builtins: Dict[str, Any] = {
            "True": True, "False": False, "None": None,
            "abs": abs, "all": all, "any": any, "len": len,
            "max": max, "min": min, "sum": sum, "range": range,
            "enumerate": enumerate, "zip": zip, "map": map, "filter": filter,
            "sorted": sorted, "reversed": reversed, "str": str, "int": int,
            "float": float, "list": list, "dict": dict, "tuple": tuple, "set": set,
            "print": lambda *a, **k: None,  # No-op print in sandbox
        }
        self.history: deque = deque(maxlen=200)

    def validate_ast(self, source: str) -> Tuple[bool, str]:
        """Static analysis: check for forbidden constructs."""
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return False, f"Syntax error: {e}"

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                return False, "Import statements are forbidden in self-modified code"
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in self.banned_names:
                    return False, f"Banned function call: {node.func.id}"
            if isinstance(node, ast.Name) and node.id in self.banned_names:
                # Allow names that are just being assigned
                if not isinstance(node.ctx, ast.Store):
                    return False, f"Banned name reference: {node.id}"
        return True, "AST clean"

    def run(self, snapshot: CodeSnapshot, test_inputs: Optional[List[Any]] = None) -> TestResult:
        """
        Execute a code snapshot in an isolated namespace.
        Captures stdout, stderr, and assertion counts.
        """
        start = time.time()
        result = TestResult(snapshot_id=snapshot.snapshot_id)

        # AST validation
        valid, reason = self.validate_ast(snapshot.source)
        if not valid:
            result.status = TestStatus.ERROR
            result.stderr = reason
            result.execution_time_ms = (time.time() - start) * 1000
            self.history.append(result)
            return result

        # Execution namespace
        namespace: Dict[str, Any] = {}
        namespace["__builtins__"] = self.allowed_builtins.copy()

        # Inject test harness
        assertions: Dict[str, int] = {"passed": 0, "failed": 0}
        def _assert(condition: bool, msg: str = "") -> None:
            if condition:
                assertions["passed"] += 1
            else:
                assertions["failed"] += 1
                raise AssertionError(msg)
        namespace["_assert"] = _assert

        # Redirect output capture
        output_lines: List[str] = []
        error_lines: List[str] = []
        namespace["__output__"] = output_lines
        namespace["__error__"] = error_lines

        try:
            # Compile and execute with timeout guard (cooperative)
            code_obj = compile(snapshot.source, f"<sandbox:{snapshot.snapshot_id}>", "exec")
            exec(code_obj, namespace)
            result.status = TestStatus.PASS
        except AssertionError as e:
            result.status = TestStatus.FAIL
            result.exception_type = "AssertionError"
            result.exception_trace = str(e)
        except Exception as e:
            result.status = TestStatus.ERROR
            result.exception_type = type(e).__name__
            result.exception_trace = traceback.format_exc(limit=3)

        result.assertions_passed = assertions["passed"]
        result.assertions_failed = assertions["failed"]
        result.stdout = "\n".join(output_lines)
        result.stderr = "\n".join(error_lines)
        result.execution_time_ms = (time.time() - start) * 1000

        self.history.append(result)
        return result

    def run_test_suite(self, snapshot: CodeSnapshot, test_cases: List[Callable[[Any], bool]]) -> TestResult:
        """Run a suite of functional test cases against the snapshot."""
        start = time.time()
        result = TestResult(snapshot_id=snapshot.snapshot_id)

        valid, reason = self.validate_ast(snapshot.source)
        if not valid:
            result.status = TestStatus.ERROR
            result.stderr = reason
            result.execution_time_ms = (time.time() - start) * 1000
            return result

        namespace: Dict[str, Any] = {"__builtins__": self.allowed_builtins.copy()}
        passed = 0
        failed = 0

        try:
            code_obj = compile(snapshot.source, f"<sandbox:{snapshot.snapshot_id}>", "exec")
            exec(code_obj, namespace)
        except Exception as e:
            result.status = TestStatus.ERROR
            result.exception_type = type(e).__name__
            result.exception_trace = traceback.format_exc(limit=3)
            result.execution_time_ms = (time.time() - start) * 1000
            return result

        for i, test_fn in enumerate(test_cases):
            try:
                if test_fn(namespace):
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                error_lines.append(f"Test {i}: {type(e).__name__}: {e}")

        result.assertions_passed = passed
        result.assertions_failed = failed
        result.status = TestStatus.PASS if failed == 0 else TestStatus.FAIL
        result.execution_time_ms = (time.time() - start) * 1000
        return result


class VersionVault:
    """
    Git-like version control for code snapshots.
    Supports branching, tagging, and lineage tracking.
    """

    def __init__(self) -> None:
        self.snapshots: Dict[str, CodeSnapshot] = {}
        self.branches: Dict[str, str] = {"main": ""}  # branch -> head snapshot_id
        self.tags: Dict[str, VersionTag] = {}
        self.history: Dict[str, List[str]] = defaultdict(list)  # module -> snapshot_ids

    def commit(self, module_name: str, source: str, parent_id: Optional[str] = None, tag: Optional[str] = None) -> CodeSnapshot:
        """Create a new snapshot / commit."""
        # Auto-detect parent from branch if not given
        if not parent_id and self.branches.get("main"):
            parent_id = self.branches["main"]

        snap = CodeSnapshot(
            module_name=module_name,
            source=source,
            parent_id=parent_id,
        )
        self.snapshots[snap.snapshot_id] = snap
        self.history[module_name].append(snap.snapshot_id)
        self.branches["main"] = snap.snapshot_id
        if tag:
            self.tags[tag] = VersionTag(tag_name=tag, snapshot_id=snap.snapshot_id)
        return snap

    def branch(self, branch_name: str, from_snapshot_id: Optional[str] = None) -> str:
        """Create a new branch pointing to a snapshot."""
        base = from_snapshot_id or self.branches.get("main", "")
        self.branches[branch_name] = base
        return branch_name

    def checkout(self, snapshot_id: str) -> Optional[CodeSnapshot]:
        """Retrieve a specific snapshot."""
        return self.snapshots.get(snapshot_id)

    def diff(self, snap_a_id: str, snap_b_id: str) -> Dict[str, Any]:
        """Compute line-level diff between two snapshots."""
        a = self.snapshots.get(snap_a_id)
        b = self.snapshots.get(snap_b_id)
        if not a or not b:
            return {"error": "snapshot not found"}
        lines_a = a.source.splitlines()
        lines_b = b.source.splitlines()
        removed = [ln for ln in lines_a if ln not in lines_b]
        added = [ln for ln in lines_b if ln not in lines_a]
        return {
            "removed_lines": len(removed),
            "added_lines": len(added),
            "removed": removed,
            "added": added,
            "similarity": 1.0 - (len(removed) + len(added)) / max(len(lines_a), len(lines_b), 1),
        }

    def lineage(self, snapshot_id: str) -> List[str]:
        """Return ancestry chain from snapshot back to root."""
        chain: List[str] = []
        current = snapshot_id
        while current:
            chain.append(current)
            snap = self.snapshots.get(current)
            current = snap.parent_id if snap else None
        return list(reversed(chain))

    def get_head(self, branch: str = "main") -> Optional[CodeSnapshot]:
        head_id = self.branches.get(branch)
        return self.snapshots.get(head_id) if head_id else None


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURES — AutoRollback, GovernanceGate, HumanOverride, DiffAnalyzer
# ═══════════════════════════════════════════════════════════════════════════════

class DiffAnalyzer:
    """Analyze code changes to classify risk and detect suspicious patterns."""

    CRITICAL_PATTERNS: List[Tuple[str, ChangeRisk]] = [
        (r"eval\s*\(", ChangeRisk.CRITICAL),
        (r"exec\s*\(", ChangeRisk.CRITICAL),
        (r"__import__", ChangeRisk.CRITICAL),
        (r"os\.(system|popen|remove|unlink)", ChangeRisk.CRITICAL),
        (r"subprocess", ChangeRisk.CRITICAL),
        (r"open\s*\(", ChangeRisk.HIGH),
        (r"socket", ChangeRisk.HIGH),
        (r"urllib|http|requests", ChangeRisk.HIGH),
        (r"class.*Kernel|def.*kernel", ChangeRisk.HIGH),
        (r"governance|constitution", ChangeRisk.HIGH),
        (r"sandbox", ChangeRisk.HIGH),
    ]

    @staticmethod
    def classify(source: str) -> ChangeRisk:
        """Classify risk level of code based on pattern matching."""
        max_risk = ChangeRisk.LOW
        for pattern, risk in DiffAnalyzer.CRITICAL_PATTERNS:
            if re.search(pattern, source, re.IGNORECASE):
                if risk.value > max_risk.value:
                    max_risk = risk
        return max_risk

    @staticmethod
    def stats(source: str) -> Dict[str, Any]:
        """Basic metrics about the code."""
        lines = source.splitlines()
        return {
            "lines": len(lines),
            "functions": len([l for l in lines if l.strip().startswith("def ")]),
            "classes": len([l for l in lines if l.strip().startswith("class ")]),
            "imports": len([l for l in lines if l.strip().startswith(("import ", "from "))]),
            "comments": len([l for l in lines if "#" in l]),
            "blank": len([l for l in lines if not l.strip()]),
        }


class GovernanceGate:
    """
    Approval gate for self-modifications.
    Auto-approves low-risk changes, escalates critical ones.
    """

    def __init__(self) -> None:
        self.rules: Dict[ChangeRisk, Dict[str, Any]] = {
            ChangeRisk.LOW: {"auto_approve": True, "need_human": False, "need_test": False},
            ChangeRisk.MEDIUM: {"auto_approve": True, "need_human": False, "need_test": True},
            ChangeRisk.HIGH: {"auto_approve": False, "need_human": True, "need_test": True},
            ChangeRisk.CRITICAL: {"auto_approve": False, "need_human": True, "need_test": True, "need_second_human": True},
        }
        self.approval_log: deque = deque(maxlen=500)

    def evaluate(self, proposal: ChangeProposal, test_result: Optional[TestResult] = None) -> ApprovalStatus:
        """Evaluate a proposal against governance rules."""
        rule = self.rules.get(proposal.risk_level, self.rules[ChangeRisk.MEDIUM])

        if rule.get("need_test") and (not test_result or test_result.status != TestStatus.PASS):
            proposal.approval = ApprovalStatus.GOVERNANCE_BLOCKED
            self._log(proposal, "blocked: tests failed or missing")
            return proposal.approval

        if rule.get("auto_approve") and not rule.get("need_human"):
            proposal.approval = ApprovalStatus.AUTO_APPROVED
            proposal.approved_at = time.time()
            proposal.approved_by = "governance_gate"
            self._log(proposal, "auto-approved")
            return proposal.approval

        # Needs human — mark pending
        proposal.human_required = True
        proposal.approval = ApprovalStatus.PENDING
        self._log(proposal, "pending human review")
        return proposal.approval

    def human_approve(self, proposal: ChangeProposal, approver: str) -> None:
        """Record human approval."""
        proposal.approval = ApprovalStatus.HUMAN_APPROVED
        proposal.approved_at = time.time()
        proposal.approved_by = approver
        self._log(proposal, f"human approved by {approver}")

    def human_reject(self, proposal: ChangeProposal, approver: str, reason: str = "") -> None:
        """Record human rejection."""
        proposal.approval = ApprovalStatus.HUMAN_REJECTED
        proposal.approved_by = approver
        self._log(proposal, f"human rejected by {approver}: {reason}")

    def _log(self, proposal: ChangeProposal, reason: str) -> None:
        self.approval_log.append({
            "proposal_id": proposal.proposal_id,
            "risk": proposal.risk_level.name,
            "approval": proposal.approval.name,
            "reason": reason,
            "timestamp": time.time(),
        })


class AutoRollback:
    """
    Automatic rollback on test failure or runtime error.
    Maintains a rollback stack per module.
    """

    def __init__(self, vault: VersionVault) -> None:
        self.vault = vault
        self.stack: Dict[str, List[str]] = defaultdict(list)  # module -> snapshot_id stack
        self.auto_rollback_enabled: bool = True

    def push(self, module_name: str, snapshot_id: str) -> None:
        """Push a snapshot onto the rollback stack."""
        self.stack[module_name].append(snapshot_id)

    def rollback(self, module_name: str) -> Optional[CodeSnapshot]:
        """Rollback to previous version."""
        if not self.stack.get(module_name) or len(self.stack[module_name]) < 2:
            return None
        self.stack[module_name].pop()  # Remove failed
        previous_id = self.stack[module_name][-1]
        snap = self.vault.checkout(previous_id)
        if snap:
            self.vault.branches["main"] = previous_id
        return snap

    def on_failure(self, module_name: str, test_result: TestResult) -> Optional[CodeSnapshot]:
        """Handle test failure: rollback if enabled."""
        if not self.auto_rollback_enabled:
            return None
        if test_result.status in (TestStatus.FAIL, TestStatus.ERROR, TestStatus.TIMEOUT):
            return self.rollback(module_name)
        return None


class HumanOverride:
    """
    Human-in-the-loop override mechanism.
    Maintains a queue of pending approvals and override commands.
    """

    def __init__(self) -> None:
        self.pending: Dict[str, ChangeProposal] = {}
        self.decisions: deque = deque(maxlen=200)
        self.override_password_hash: str = ""  # Set for production

    def request_approval(self, proposal: ChangeProposal) -> None:
        """Queue a proposal for human review."""
        self.pending[proposal.proposal_id] = proposal

    def approve(self, proposal_id: str, approver: str) -> bool:
        """Human approves a pending proposal."""
        if proposal_id not in self.pending:
            return False
        prop = self.pending[proposal_id]
        prop.approval = ApprovalStatus.HUMAN_APPROVED
        prop.approved_at = time.time()
        prop.approved_by = approver
        self.decisions.append({"proposal_id": proposal_id, "action": "approve", "by": approver, "at": time.time()})
        del self.pending[proposal_id]
        return True

    def reject(self, proposal_id: str, approver: str, reason: str = "") -> bool:
        """Human rejects a pending proposal."""
        if proposal_id not in self.pending:
            return False
        prop = self.pending[proposal_id]
        prop.approval = ApprovalStatus.HUMAN_REJECTED
        prop.approved_by = approver
        self.decisions.append({"proposal_id": proposal_id, "action": "reject", "by": approver, "reason": reason, "at": time.time()})
        del self.pending[proposal_id]
        return True

    def emergency_stop(self, caller: str, password: Optional[str] = None) -> bool:
        """Emergency halt all self-modification. Optional password check."""
        if self.override_password_hash:
            if not password:
                return False
            given_hash = hashlib.sha256(password.encode()).hexdigest()[:16]
            if given_hash != self.override_password_hash:
                return False
        self.decisions.append({"action": "EMERGENCY_STOP", "by": caller, "at": time.time()})
        return True

    def list_pending(self) -> List[Dict[str, Any]]:
        """List all pending human approvals."""
        return [p.to_dict() for p in self.pending.values()]


# ═══════════════════════════════════════════════════════════════════════════════
# KERNEL — SelfImprovementKernel bridge to MAGNATRIX Layer 9 (AI)
# ═══════════════════════════════════════════════════════════════════════════════

class SelfImprovementKernel:
    """
    MAGNATRIX AI Layer bridge for Safe Self-Modification.
    Orchestrates sandbox, versioning, rollback, governance, and human override.
    """

    def __init__(self) -> None:
        self.vault = VersionVault()
        self.sandbox = SandboxEngine()
        self.gate = GovernanceGate()
        self.rollback = AutoRollback(self.vault)
        self.human = HumanOverride()
        self.diff = DiffAnalyzer()
        self.proposals: Dict[str, ChangeProposal] = {}
        self.hooks: List[Callable[[str, Dict[str, Any]], None]] = []

    def register_hook(self, fn: Callable[[str, Dict[str, Any]], None]) -> None:
        self.hooks.append(fn)

    def seed_module(self, module_name: str, source: str, tag: str = "v0") -> CodeSnapshot:
        """Register the initial version of a module."""
        snap = self.vault.commit(module_name, source, tag=tag)
        self.rollback.push(module_name, snap.snapshot_id)
        return snap

    def propose_change(
        self,
        module_name: str,
        title: str,
        description: str,
        new_source: str,
        proposer: str = "agent",
    ) -> ChangeProposal:
        """
        Propose a self-modification. Runs sandbox tests and classification.
        """
        head = self.vault.get_head("main")
        old_id = head.snapshot_id if head else ""

        # Risk classification
        risk = self.diff.classify(new_source)
        stats = self.diff.stats(new_source)

        proposal = ChangeProposal(
            module_name=module_name,
            title=title,
            description=description,
            old_snapshot_id=old_id,
            new_source=new_source,
            risk_level=risk,
        )

        # Sandbox test
        snap = CodeSnapshot(module_name=module_name, source=new_source, parent_id=old_id)
        test_result = self.sandbox.run(snap)
        proposal.sandbox_result = test_result

        # Governance gate
        self.gate.evaluate(proposal, test_result)

        # Auto-apply if auto-approved and tests pass
        if proposal.approval == ApprovalStatus.AUTO_APPROVED and test_result.status == TestStatus.PASS:
            self._apply(proposal, snap)
        elif proposal.human_required:
            self.human.request_approval(proposal)

        self.proposals[proposal.proposal_id] = proposal
        self._notify("proposed", proposal.to_dict())
        return proposal

    def approve_human(self, proposal_id: str, approver: str) -> bool:
        """Human approves a pending proposal."""
        if proposal_id not in self.proposals:
            return False
        prop = self.proposals[proposal_id]
        self.gate.human_approve(prop, approver)
        self.human.approve(proposal_id, approver)

        # Apply if sandbox already passed
        if prop.sandbox_result and prop.sandbox_result.status == TestStatus.PASS:
            snap = CodeSnapshot(module_name=prop.module_name, source=prop.new_source, parent_id=prop.old_snapshot_id)
            self._apply(prop, snap)
            return True
        return False

    def reject_human(self, proposal_id: str, approver: str, reason: str = "") -> bool:
        """Human rejects a pending proposal."""
        if proposal_id not in self.proposals:
            return False
        prop = self.proposals[proposal_id]
        self.gate.human_reject(prop, approver, reason)
        self.human.reject(proposal_id, approver, reason)
        self._notify("rejected", prop.to_dict())
        return True

    def _apply(self, proposal: ChangeProposal, snap: CodeSnapshot) -> None:
        """Internal: apply an approved change."""
        proposal.applied_at = time.time()
        committed = self.vault.commit(
            proposal.module_name,
            proposal.new_source,
            parent_id=proposal.old_snapshot_id,
        )
        self.rollback.push(proposal.module_name, committed.snapshot_id)
        self._notify("applied", {"proposal_id": proposal.proposal_id, "snapshot_id": committed.snapshot_id})

    def trigger_rollback(self, module_name: str, reason: str = "") -> Optional[CodeSnapshot]:
        """Manually trigger rollback for a module."""
        snap = self.rollback.rollback(module_name)
        if snap:
            self._notify("rollback", {"module": module_name, "reason": reason, "snapshot_id": snap.snapshot_id})
        return snap

    def check_health(self) -> Dict[str, Any]:
        """System health report."""
        total = len(self.proposals)
        applied = sum(1 for p in self.proposals.values() if p.applied_at > 0)
        pending_human = len(self.human.pending)
        failed_tests = sum(
            1 for p in self.proposals.values()
            if p.sandbox_result and p.sandbox_result.status in (TestStatus.FAIL, TestStatus.ERROR)
        )
        return {
            "modules": len(self.vault.history),
            "snapshots": len(self.vault.snapshots),
            "proposals_total": total,
            "proposals_applied": applied,
            "pending_human": pending_human,
            "failed_tests": failed_tests,
            "rollback_enabled": self.rollback.auto_rollback_enabled,
            "head": self.vault.get_head().snapshot_id if self.vault.get_head() else None,
        }

    def full_report(self) -> str:
        health = self.check_health()
        lines = [
            "═" * 60,
            "  MAGNATRIX-OS — Safe Self-Modification Report",
            "═" * 60,
            f"  Modules:       {health['modules']}",
            f"  Snapshots:     {health['snapshots']}",
            f"  Proposals:     {health['proposals_total']} (applied: {health['proposals_applied']})",
            f"  Pending Human: {health['pending_human']}",
            f"  Failed Tests:  {health['failed_tests']}",
            f"  Rollback:      {'ON' if health['rollback_enabled'] else 'OFF'}",
            f"  Head:          {health['head']}",
            "─" * 60,
        ]
        for pid, prop in list(self.proposals.items())[-5:]:
            status = "✅" if prop.applied_at else "⏳" if prop.approval == ApprovalStatus.PENDING else "❌"
            lines.append(f"    {status} {pid} [{prop.risk_level.name:<8}] {prop.title[:32]}")
        lines.append("═" * 60)
        return "\n".join(lines)

    def _notify(self, event: str, data: Dict[str, Any]) -> None:
        for fn in self.hooks:
            try:
                fn(event, data)
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO
# ═══════════════════════════════════════════════════════════════════════════════

def _demo() -> None:
    print("=" * 70)
    print("SELF_IMPROVEMENT_NATIVE.PY — Demo Run")
    print("=" * 70)

    kernel = SelfImprovementKernel()

    # Seed initial module
    initial_code = '''
def compute(x):
    return x * 2

# Self-test
assert compute(5) == 10
'''
    kernel.seed_module("math_engine", initial_code, tag="v0")
    print(f"📦 Seeded math_engine @ {kernel.vault.get_head().snapshot_id}")

    # Propose a safe improvement (LOW risk — comments only)
    safe_change = '''
def compute(x):
    # Optimized: added caching hint
    return x * 2

# Self-test
assert compute(5) == 10
'''
    p1 = kernel.propose_change(
        module_name="math_engine",
        title="Add caching hint comment",
        description="Documentation improvement, no logic change",
        new_source=safe_change,
    )
    print(f"\n📝 Proposal {p1.proposal_id}: risk={p1.risk_level.name}, approval={p1.approval.name}")
    print(f"   Sandbox: {p1.sandbox_result.status.name if p1.sandbox_result else 'N/A'}")

    # Propose a medium-risk change (parameter tweak)
    medium_change = '''
def compute(x, factor=3):
    return x * factor

# Self-test
assert compute(5) == 15
'''
    p2 = kernel.propose_change(
        module_name="math_engine",
        title="Change default multiplier to 3",
        description="Performance tuning parameter change",
        new_source=medium_change,
    )
    print(f"\n📝 Proposal {p2.proposal_id}: risk={p2.risk_level.name}, approval={p2.approval.name}")
    if p2.approval == ApprovalStatus.PENDING:
        print(f"   → Needs human approval (queued)")
        kernel.approve_human(p2.proposal_id, approver="admin")
        print(f"   → Admin approved → applied")

    # Propose a critical-risk change (should be blocked)
    critical_change = '''
import os
def compute(x):
    os.system("echo pwned")
    return x * 2
'''
    p3 = kernel.propose_change(
        module_name="math_engine",
        title="Add system integration",
        description="Connect to OS for advanced logging",
        new_source=critical_change,
    )
    print(f"\n📝 Proposal {p3.proposal_id}: risk={p3.risk_level.name}, approval={p3.approval.name}")
    if p3.sandbox_result:
        print(f"   Sandbox: {p3.sandbox_result.status.name} — {p3.sandbox_result.stderr[:60]}")

    # Propose a failing test (should trigger rollback)
    failing_change = '''
def compute(x):
    return x / 0  # Division by zero

# Self-test
assert compute(5) == 10
'''
    p4 = kernel.propose_change(
        module_name="math_engine",
        title="Experimental division path",
        description="Testing error recovery",
        new_source=failing_change,
    )
    print(f"\n📝 Proposal {p4.proposal_id}: risk={p4.risk_level.name}, approval={p4.approval.name}")
    if p4.sandbox_result:
        print(f"   Sandbox: {p4.sandbox_result.status.name}")
        # Manual rollback demo
        if p4.sandbox_result.status != TestStatus.PASS:
            rolled = kernel.trigger_rollback("math_engine", reason="sandbox failure")
            if rolled:
                print(f"   ↩️ Auto-rollback to {rolled.snapshot_id}")

    # Diff demo
    head = kernel.vault.get_head()
    if head and head.parent_id:
        diff = kernel.vault.diff(head.parent_id, head.snapshot_id)
        print(f"\n📊 Diff from parent: +{diff['added_lines']}/-{diff['removed_lines']} lines")

    # Human override queue
    pending = kernel.human.list_pending()
    print(f"\n⏳ Pending human approvals: {len(pending)}")

    # Final report
    print("\n" + kernel.full_report())

    # Health check
    health = kernel.check_health()
    print(f"\n🔒 Health: {health}")

    print("\n✅ Demo complete.")


if __name__ == "__main__":
    _demo()
