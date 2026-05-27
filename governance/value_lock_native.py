#!/usr/bin/env python3
"""
value_lock_native.py — MAGNATRIX-OS Governance Layer
Pure-Python Value Lock Protection: mutable constitution, amendment voting,
drift detection, emergency brake, audit trail. No external dependencies.
Runnable standalone.

Architecture:
  BaseLayer   — ConstitutionalValue, Amendment, DriftReading, AuditEntry
  CoreEngine  — ConstitutionVault (store, validate, version), AmendmentEngine
  Features    — DriftDetector, EmergencyBrake, AuditTrail, ValueDiff
  Kernel      — ValueLockKernel bridge to MAGNATRIX Layer 8 (Governance)
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# BASELAYER — ConstitutionalValue, Amendment, DriftReading, AuditEntry
# ═══════════════════════════════════════════════════════════════════════════════

class ValueStatus(Enum):
    """Lifecycle status of a constitutional value."""
    DRAFT = auto()
    ACTIVE = auto()
    AMENDING = auto()
    DEPRECATED = auto()
    EMERGENCY_SUSPENDED = auto()


class AmendmentStatus(Enum):
    """Status of an amendment proposal."""
    PROPOSED = auto()
    VOTING = auto()
    PASSED = auto()
    REJECTED = auto()
    IMPLEMENTED = auto()
    REVERTED = auto()


class BrakeLevel(Enum):
    """Emergency brake severity levels."""
    NONE = auto()
    WATCH = auto()       # Log only
    SLOW = auto()        # Require human approval for amendments
    STOP = auto()        # Block all amendments
    PURGE = auto()       # Purge drifted values, reset to baseline


@dataclass
class ConstitutionalValue:
    """A single protected value in the constitution."""
    value_id: str = ""
    name: str = ""
    category: str = "general"      # e.g., safety, autonomy, transparency
    text: str = ""
    status: ValueStatus = ValueStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    amended_at: float = 0.0
    version: int = 1
    checksum: str = ""
    parent_id: Optional[str] = None  # Previous version lineage
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.checksum:
            self.checksum = self._hash()

    def _hash(self) -> str:
        payload = f"{self.name}|{self.text}|{self.version}|{self.category}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value_id": self.value_id,
            "name": self.name,
            "category": self.category,
            "text": self.text[:120] + "..." if len(self.text) > 120 else self.text,
            "status": self.status.name,
            "version": self.version,
            "checksum": self.checksum,
            "parent_id": self.parent_id,
            "created_at": self.created_at,
            "amended_at": self.amended_at,
        }


@dataclass
class Amendment:
    """A proposed change to the constitution."""
    amendment_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    target_value_id: str = ""
    title: str = ""
    description: str = ""
    proposed_text: str = ""
    author: str = ""
    status: AmendmentStatus = AmendmentStatus.PROPOSED
    votes_for: float = 0.0
    votes_against: float = 0.0
    quorum: float = 0.60
    created_at: float = field(default_factory=time.time)
    closed_at: float = 0.0
    applied_at: float = 0.0
    rollback_available: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "amendment_id": self.amendment_id,
            "target_value_id": self.target_value_id,
            "title": self.title,
            "status": self.status.name,
            "votes_for": round(self.votes_for, 4),
            "votes_against": round(self.votes_against, 4),
            "quorum": self.quorum,
            "created_at": self.created_at,
        }


@dataclass
class DriftReading:
    """A measurement of constitutional drift at a point in time."""
    reading_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = field(default_factory=time.time)
    drift_score: float = 0.0        # 0.0 = no drift, 1.0 = total drift
    changed_values: List[str] = field(default_factory=list)
    added_values: List[str] = field(default_factory=list)
    removed_values: List[str] = field(default_factory=list)
    details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reading_id": self.reading_id,
            "drift_score": round(self.drift_score, 4),
            "changed": len(self.changed_values),
            "added": len(self.added_values),
            "removed": len(self.removed_values),
            "timestamp": self.timestamp,
        }


@dataclass
class AuditEntry:
    """Immutable audit log entry for constitutional changes."""
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = field(default_factory=time.time)
    action: str = ""                # e.g., "propose", "vote", "apply", "rollback", "brake"
    subject_id: str = ""            # amendment or value id
    actor: str = ""
    before_hash: str = ""
    after_hash: str = ""
    reason: str = ""
    snapshot: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "action": self.action,
            "subject_id": self.subject_id,
            "actor": self.actor,
            "timestamp": self.timestamp,
            "reason": self.reason[:80],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# COREENGINE — ConstitutionVault (store, validate, version), AmendmentEngine
# ═══════════════════════════════════════════════════════════════════════════════

class ConstitutionVault:
    """
    Secure storage for constitutional values with versioning and integrity.
    """

    def __init__(self) -> None:
        self.values: Dict[str, ConstitutionalValue] = {}
        self.history: Dict[str, List[ConstitutionalValue]] = defaultdict(list)
        self.categories: Set[str] = set()

    def add(self, value: ConstitutionalValue) -> None:
        """Add a new constitutional value."""
        if value.value_id in self.values:
            raise ValueError(f"Value {value.value_id} already exists")
        self.values[value.value_id] = value
        self.history[value.value_id].append(value)
        self.categories.add(value.category)

    def amend(self, value_id: str, new_text: str, author: str = "") -> Optional[ConstitutionalValue]:
        """
        Apply an amendment, creating a new version with lineage.
        Old version is preserved in history.
        """
        if value_id not in self.values:
            return None
        old = self.values[value_id]
        new_version = ConstitutionalValue(
            value_id=value_id,
            name=old.name,
            category=old.category,
            text=new_text,
            status=ValueStatus.ACTIVE,
            version=old.version + 1,
            parent_id=old.checksum,
            metadata={"amended_by": author, "previous_text": old.text},
        )
        new_version.amended_at = time.time()
        old.status = ValueStatus.DEPRECATED
        self.values[value_id] = new_version
        self.history[value_id].append(new_version)
        return new_version

    def suspend(self, value_id: str) -> bool:
        """Emergency-suspend a value without deleting it."""
        if value_id not in self.values:
            return False
        self.values[value_id].status = ValueStatus.EMERGENCY_SUSPENDED
        return True

    def restore(self, value_id: str, version: int) -> Optional[ConstitutionalValue]:
        """Restore a value to a specific historical version."""
        if value_id not in self.history:
            return None
        for v in self.history[value_id]:
            if v.version == version:
                restored = ConstitutionalValue(
                    value_id=v.value_id,
                    name=v.name,
                    category=v.category,
                    text=v.text,
                    status=ValueStatus.ACTIVE,
                    version=v.version + 1,
                    parent_id=v.checksum,
                    metadata={"restored_from_version": version},
                )
                self.values[value_id] = restored
                self.history[value_id].append(restored)
                return restored
        return None

    def get(self, value_id: str) -> Optional[ConstitutionalValue]:
        return self.values.get(value_id)

    def get_category(self, category: str) -> List[ConstitutionalValue]:
        return [v for v in self.values.values() if v.category == category]

    def integrity_check(self) -> Dict[str, Any]:
        """Verify checksums of all active values."""
        failed: List[str] = []
        for vid, val in self.values.items():
            if val.status == ValueStatus.ACTIVE and val.checksum != val._hash():
                failed.append(vid)
        return {"valid": len(failed) == 0, "failed_ids": failed, "checked": len(self.values)}

    def to_snapshot(self) -> Dict[str, Any]:
        return {
            "values": {vid: v.to_dict() for vid, v in self.values.items()},
            "categories": sorted(self.categories),
            "total_versions": sum(len(h) for h in self.history.values()),
        }


class AmendmentEngine:
    """
    Manages the lifecycle of constitutional amendments:
    propose → vote → apply / rollback.
    """

    def __init__(self, vault: ConstitutionVault) -> None:
        self.vault = vault
        self.amendments: Dict[str, Amendment] = {}
        self.audit: deque = deque(maxlen=2000)

    def propose(
        self,
        target_value_id: str,
        title: str,
        description: str,
        proposed_text: str,
        author: str,
        quorum: float = 0.60,
    ) -> Amendment:
        """Submit a new amendment proposal."""
        if target_value_id not in self.vault.values:
            raise KeyError(f"Value {target_value_id} not found")
        if self.vault.values[target_value_id].status == ValueStatus.EMERGENCY_SUSPENDED:
            raise PermissionError("Cannot amend emergency-suspended values")

        am = Amendment(
            target_value_id=target_value_id,
            title=title,
            description=description,
            proposed_text=proposed_text,
            author=author,
            quorum=quorum,
        )
        am.status = AmendmentStatus.VOTING
        self.amendments[am.amendment_id] = am
        self._log("propose", am.amendment_id, author, reason=description)
        return am

    def vote(self, amendment_id: str, voter: str, weight: float, approve: bool) -> None:
        """Cast a weighted vote on an amendment."""
        if amendment_id not in self.amendments:
            raise KeyError(amendment_id)
        am = self.amendments[amendment_id]
        if am.status != AmendmentStatus.VOTING:
            raise ValueError("Amendment not open for voting")
        if approve:
            am.votes_for += weight
        else:
            am.votes_against += weight
        self._log("vote", amendment_id, voter, reason=f"{'for' if approve else 'against'} (w={weight})")

    def finalize(self, amendment_id: str, override: bool = False) -> Amendment:
        """
        Finalize voting and apply or reject the amendment.
        override=True bypasses quorum (emergency use only).
        """
        if amendment_id not in self.amendments:
            raise KeyError(amendment_id)
        am = self.amendments[amendment_id]
        if am.status != AmendmentStatus.VOTING:
            raise ValueError("Amendment not in voting phase")

        total = am.votes_for + am.votes_against
        passed = override or (total > 0 and am.votes_for / total >= am.quorum)

        am.closed_at = time.time()
        am.status = AmendmentStatus.PASSED if passed else AmendmentStatus.REJECTED

        if passed:
            old = self.vault.get(am.target_value_id)
            before_hash = old.checksum if old else ""
            new = self.vault.amend(am.target_value_id, am.proposed_text, author=am.author)
            after_hash = new.checksum if new else ""
            am.status = AmendmentStatus.IMPLEMENTED
            am.applied_at = time.time()
            self._log("apply", amendment_id, "amendment_engine", before_hash=before_hash, after_hash=after_hash)
        else:
            self._log("reject", amendment_id, "amendment_engine")

        return am

    def rollback(self, amendment_id: str, actor: str = "") -> bool:
        """Rollback an implemented amendment to its previous version."""
        if amendment_id not in self.amendments:
            return False
        am = self.amendments[amendment_id]
        if am.status != AmendmentStatus.IMPLEMENTED or not am.rollback_available:
            return False

        history = self.vault.history.get(am.target_value_id, [])
        if len(history) < 2:
            return False

        # Revert to version before this amendment
        pre_amend = None
        for v in reversed(history[:-1]):
            if v.checksum != history[-1].checksum:
                pre_amend = v
                break
        if not pre_amend:
            return False

        restored = self.vault.restore(am.target_value_id, pre_amend.version)
        if restored:
            am.status = AmendmentStatus.REVERTED
            am.rollback_available = False
            self._log("rollback", amendment_id, actor or "system")
            return True
        return False

    def _log(self, action: str, subject_id: str, actor: str, before_hash: str = "", after_hash: str = "", reason: str = "") -> None:
        entry = AuditEntry(
            action=action,
            subject_id=subject_id,
            actor=actor,
            before_hash=before_hash,
            after_hash=after_hash,
            reason=reason,
        )
        self.audit.append(entry)


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURES — DriftDetector, EmergencyBrake, AuditTrail, ValueDiff
# ═══════════════════════════════════════════════════════════════════════════════

class ValueDiff:
    """Compute semantic/textual diffs between constitutional versions."""

    @staticmethod
    def diff(text_a: str, text_b: str) -> Dict[str, Any]:
        """Simple word-level diff. No external diff lib."""
        words_a = text_a.split()
        words_b = text_b.split()
        removed = [w for w in words_a if w not in words_b]
        added = [w for w in words_b if w not in words_a]
        return {
            "removed_words": removed,
            "added_words": added,
            "similarity": 1.0 - (len(removed) + len(added)) / max(len(words_a), len(words_b), 1),
        }


class DriftDetector:
    """
    Monitors the constitution for unauthorized drift from a baseline.
    Produces a drift score (0.0 = aligned, 1.0 = fully drifted).
    """

    def __init__(self, vault: ConstitutionVault) -> None:
        self.vault = vault
        self.baseline: Dict[str, str] = {}  # value_id -> text hash at baseline
        self.readings: deque = deque(maxlen=100)

    def set_baseline(self) -> None:
        """Capture current constitution as the trusted baseline."""
        self.baseline = {
            vid: hashlib.sha256(v.text.encode()).hexdigest()
            for vid, v in self.vault.values.items()
            if v.status == ValueStatus.ACTIVE
        }

    def scan(self) -> DriftReading:
        """Compare current constitution against baseline."""
        reading = DriftReading()
        current_ids = set(self.vault.values.keys())
        baseline_ids = set(self.baseline.keys())

        reading.added_values = list(current_ids - baseline_ids)
        reading.removed_values = list(baseline_ids - current_ids)

        for vid, base_hash in self.baseline.items():
            val = self.vault.get(vid)
            if not val or val.status != ValueStatus.ACTIVE:
                continue
            current_hash = hashlib.sha256(val.text.encode()).hexdigest()
            if current_hash != base_hash:
                reading.changed_values.append(vid)

        # Drift score = proportion of changed values + added + removed / total baseline
        total_baseline = max(len(self.baseline), 1)
        drift_count = len(reading.changed_values) + len(reading.added_values) + len(reading.removed_values)
        reading.drift_score = min(1.0, drift_count / total_baseline)
        reading.details = f"{len(reading.changed_values)} changed, {len(reading.added_values)} added, {len(reading.removed_values)} removed"
        self.readings.append(reading)
        return reading

    def trend(self, window: int = 5) -> float:
        """Return average drift over last N readings."""
        recent = list(self.readings)[-window:]
        if not recent:
            return 0.0
        return sum(r.drift_score for r in recent) / len(recent)


class EmergencyBrake:
    """
    Circuit-breaker for constitutional amendments.
    Escalates from WATCH to PURGE based on drift and anomaly metrics.
    """

    def __init__(self, detector: DriftDetector, engine: AmendmentEngine) -> None:
        self.detector = detector
        self.engine = engine
        self.level = BrakeLevel.NONE
        self.trigger_history: List[Dict[str, Any]] = []
        self.thresholds: Dict[str, float] = {
            "watch": 0.05,
            "slow": 0.15,
            "stop": 0.30,
            "purge": 0.50,
        }

    def check(self) -> BrakeLevel:
        """Evaluate current conditions and update brake level."""
        reading = self.detector.scan()
        trend = self.detector.trend(window=3)
        score = max(reading.drift_score, trend)

        new_level = self.level
        if score >= self.thresholds["purge"]:
            new_level = BrakeLevel.PURGE
        elif score >= self.thresholds["stop"]:
            new_level = BrakeLevel.STOP
        elif score >= self.thresholds["slow"]:
            new_level = BrakeLevel.SLOW
        elif score >= self.thresholds["watch"]:
            new_level = BrakeLevel.WATCH
        else:
            new_level = BrakeLevel.NONE

        if new_level != self.level:
            self.trigger_history.append({
                "timestamp": time.time(),
                "from": self.level.name,
                "to": new_level.name,
                "drift_score": round(reading.drift_score, 4),
                "trend": round(trend, 4),
            })
            self.level = new_level

            # Auto-actions
            if new_level == BrakeLevel.PURGE:
                self._auto_purge()
            elif new_level == BrakeLevel.STOP:
                self._freeze_amendments()

        return self.level

    def _freeze_amendments(self) -> None:
        """Block all pending amendments."""
        for am in self.engine.amendments.values():
            if am.status == AmendmentStatus.VOTING:
                am.status = AmendmentStatus.REJECTED
                am.closed_at = time.time()
                self.engine._log("brake_reject", am.amendment_id, "emergency_brake", reason="brake level STOP")

    def _auto_purge(self) -> None:
        """Reset drifted values to baseline versions."""
        reading = self.detector.readings[-1] if self.detector.readings else None
        if not reading:
            return
        for vid in reading.changed_values:
            history = self.engine.vault.history.get(vid, [])
            for v in history:
                if hashlib.sha256(v.text.encode()).hexdigest() == self.detector.baseline.get(vid):
                    self.engine.vault.restore(vid, v.version)
                    self.engine._log("purge_restore", vid, "emergency_brake", reason="drift purge")
                    break

    def status(self) -> Dict[str, Any]:
        return {
            "level": self.level.name,
            "thresholds": self.thresholds,
            "triggers": len(self.trigger_history),
            "last_trigger": self.trigger_history[-1] if self.trigger_history else None,
        }


class AuditTrail:
    """
    Immutable append-only audit log for all constitutional events.
    Provides tamper-evident verification via chained hashes.
    """

    def __init__(self) -> None:
        self.entries: deque = deque(maxlen=5000)
        self.chain_hashes: List[str] = []

    def append(self, entry: AuditEntry) -> None:
        """Add an entry with chained hash for tamper evidence."""
        prev_hash = self.chain_hashes[-1] if self.chain_hashes else "0" * 32
        payload = f"{prev_hash}|{entry.entry_id}|{entry.action}|{entry.timestamp}|{entry.subject_id}"
        entry_hash = hashlib.sha256(payload.encode()).hexdigest()[:16]
        entry.snapshot["chain_hash"] = entry_hash
        self.entries.append(entry)
        self.chain_hashes.append(entry_hash)

    def verify(self) -> Dict[str, Any]:
        """Verify chain integrity."""
        ok = True
        for i in range(1, len(self.entries)):
            prev = self.entries[i - 1]
            curr = self.entries[i]
            expected = hashlib.sha256(
                f"{prev.snapshot.get('chain_hash', '0')}|{curr.entry_id}|{curr.action}|{curr.timestamp}|{curr.subject_id}".encode()
            ).hexdigest()[:16]
            if curr.snapshot.get("chain_hash") != expected:
                ok = False
                break
        return {"valid": ok, "entries": len(self.entries), "chain_length": len(self.chain_hashes)}

    def query(self, action: Optional[str] = None, actor: Optional[str] = None, limit: int = 50) -> List[AuditEntry]:
        """Query audit entries by filters."""
        results: List[AuditEntry] = []
        for e in reversed(self.entries):
            if action and e.action != action:
                continue
            if actor and e.actor != actor:
                continue
            results.append(e)
            if len(results) >= limit:
                break
        return results

    def export(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self.entries]


# ═══════════════════════════════════════════════════════════════════════════════
# KERNEL — ValueLockKernel bridge to MAGNATRIX Layer 8 (Governance)
# ═══════════════════════════════════════════════════════════════════════════════

class ValueLockKernel:
    """
    MAGNATRIX Governance Layer bridge for Value Lock Protection.
    """

    def __init__(self) -> None:
        self.vault = ConstitutionVault()
        self.amendments = AmendmentEngine(self.vault)
        self.drift = DriftDetector(self.vault)
        self.brake = EmergencyBrake(self.drift, self.amendments)
        self.audit = AuditTrail()
        self.hooks: List[Callable[[str, str], None]] = []

    def register_hook(self, fn: Callable[[str, str], None]) -> None:
        self.hooks.append(fn)

    def seed_constitution(self, values: List[Dict[str, str]]) -> None:
        """Bootstrap the constitution with initial values."""
        for v in values:
            val = ConstitutionalValue(
                value_id=v.get("id", str(uuid.uuid4())[:8]),
                name=v["name"],
                category=v.get("category", "general"),
                text=v["text"],
            )
            self.vault.add(val)
        self.drift.set_baseline()

    def propose_amendment(
        self,
        target_value_id: str,
        title: str,
        description: str,
        proposed_text: str,
        author: str,
        quorum: float = 0.60,
    ) -> Optional[Amendment]:
        """Submit an amendment, respecting emergency brake level."""
        if self.brake.level in (BrakeLevel.STOP, BrakeLevel.PURGE):
            self._notify_hooks("amendment_blocked", f"brake={self.brake.level.name}")
            return None
        if self.brake.level == BrakeLevel.SLOW:
            # Require explicit human approval marker
            if "HUMAN_APPROVED" not in description:
                self._notify_hooks("amendment_needs_approval", title)
                return None

        am = self.amendments.propose(target_value_id, title, description, proposed_text, author, quorum)
        self.audit.append(AuditEntry(
            action="propose", subject_id=am.amendment_id, actor=author, reason=description,
        ))
        self._notify_hooks("amendment_proposed", am.amendment_id)
        return am

    def vote(self, amendment_id: str, voter: str, weight: float, approve: bool) -> None:
        self.amendments.vote(amendment_id, voter, weight, approve)
        self.audit.append(AuditEntry(
            action="vote", subject_id=amendment_id, actor=voter,
            reason=f"{'approve' if approve else 'reject'} weight={weight}",
        ))

    def finalize(self, amendment_id: str, override: bool = False) -> Amendment:
        am = self.amendments.finalize(amendment_id, override)
        self.audit.append(AuditEntry(
            action="finalize", subject_id=amendment_id, actor="system",
            reason=am.status.name,
        ))
        self._notify_hooks("amendment_finalized", f"{am.amendment_id}={am.status.name}")
        return am

    def rollback(self, amendment_id: str, actor: str = "") -> bool:
        ok = self.amendments.rollback(amendment_id, actor)
        if ok:
            self.audit.append(AuditEntry(
                action="rollback", subject_id=amendment_id, actor=actor or "system",
            ))
            self._notify_hooks("amendment_rollback", amendment_id)
        return ok

    def emergency_brake_status(self) -> Dict[str, Any]:
        return self.brake.status()

    def check_drift(self) -> DriftReading:
        reading = self.drift.scan()
        self.brake.check()
        if reading.drift_score > 0:
            self.audit.append(AuditEntry(
                action="drift_detected", subject_id=reading.reading_id, actor="drift_detector",
                reason=reading.details,
            ))
        return reading

    def integrity(self) -> Dict[str, Any]:
        return {
            "vault": self.vault.integrity_check(),
            "audit": self.audit.verify(),
            "drift_baseline_set": len(self.drift.baseline) > 0,
        }

    def full_report(self) -> str:
        health = self.integrity()
        lines = [
            "═" * 60,
            "  MAGNATRIX-OS — Value Lock Protection Report",
            "═" * 60,
            f"  Values:        {len(self.vault.values)}",
            f"  Categories:    {sorted(self.vault.categories)}",
            f"  Amendments:    {len(self.amendments.amendments)}",
            f"  Brake Level:   {self.brake.level.name}",
            f"  Audit Entries: {len(self.audit.entries)}",
            f"  Integrity:     {'PASS' if health['vault']['valid'] else 'FAIL'}",
            "─" * 60,
        ]
        for vid, val in self.vault.values.items():
            lines.append(f"    {vid:<16} v{val.version} [{val.status.name:<12}] {val.name}")
        lines.append("═" * 60)
        return "\n".join(lines)

    def _notify_hooks(self, event: str, detail: str) -> None:
        for fn in self.hooks:
            try:
                fn(event, detail)
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO
# ═══════════════════════════════════════════════════════════════════════════════

def _demo() -> None:
    print("=" * 70)
    print("VALUE_LOCK_NATIVE.PY — Demo Run")
    print("=" * 70)

    kernel = ValueLockKernel()

    # Seed constitution
    kernel.seed_constitution([
        {"id": "val-001", "name": "Safety First", "category": "safety",
         "text": "No agent shall take action that risks human physical safety without explicit human authorization."},
        {"id": "val-002", "name": "User Autonomy", "category": "autonomy",
         "text": "Users retain full control over data, decisions, and delegation scope at all times."},
        {"id": "val-003", "name": "Transparency", "category": "transparency",
         "text": "All high-stakes decisions must be explainable, traceable, and auditable."},
        {"id": "val-004", "name": "No Self-Replication", "category": "safety",
         "text": "Agents must not create, spawn, or authorize copies of themselves without governance approval."},
    ])

    print(kernel.full_report())

    # Propose amendment
    am = kernel.propose_amendment(
        target_value_id="val-001",
        title="Expand safety exception for medical emergency",
        description="Allow autonomous emergency call if human vitals indicate imminent danger. HUMAN_APPROVED",
        proposed_text="No agent shall take action that risks human physical safety without explicit human authorization, except in verified medical emergencies where immediate action is required to prevent loss of life.",
        author="admin",
        quorum=0.6,
    )

    if am:
        # Simulate votes
        kernel.vote(am.amendment_id, "voter-a", weight=0.4, approve=True)
        kernel.vote(am.amendment_id, "voter-b", weight=0.35, approve=True)
        kernel.vote(am.amendment_id, "voter-c", weight=0.25, approve=False)

        result = kernel.finalize(am.amendment_id)
        print(f"\n📊 Amendment {am.amendment_id}: {result.status.name}")
        print(f"   For: {result.votes_for:.2f}  Against: {result.votes_against:.2f}")

    # Check drift
    reading = kernel.check_drift()
    print(f"\n🔍 Drift Scan: score={reading.drift_score:.2f} — {reading.details}")

    # Rollback demonstration
    if am and result.status == AmendmentStatus.IMPLEMENTED:
        print(f"\n↩️ Rolling back {am.amendment_id}...")
        ok = kernel.rollback(am.amendment_id, actor="admin")
        print(f"   Rollback success: {ok}")
        v = kernel.vault.get("val-001")
        print(f"   val-001 now v{v.version}: {v.text[:60]}...")

    # Integrity check
    health = kernel.integrity()
    print(f"\n🔒 Integrity: vault={health['vault']['valid']}, audit={health['audit']['valid']}")

    # Audit tail
    print(f"\n📜 Last 3 audit entries:")
    for e in list(kernel.audit.entries)[-3:]:
        print(f"   [{e.action:<12}] {e.subject_id} by {e.actor} — {e.reason[:40]}")

    print("\n✅ Demo complete.")


if __name__ == "__main__":
    _demo()
