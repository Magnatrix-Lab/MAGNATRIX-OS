"""
ACS Tamper-Evident Audit Trail — MAGNATRIX-OS Governance Layer
Hash chain + Merkle tree untuk audit integrity.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AuditEntry:
    """Single audit entry dengan hash chain."""
    timestamp: float
    event_type: str
    actor: str
    verdict: str
    evidence: Dict[str, Any]
    prev_hash: str
    entry_hash: str = ""
    sequence: int = 0

    def compute_hash(self) -> str:
        data = json.dumps({
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "actor": self.actor,
            "verdict": self.verdict,
            "evidence": self.evidence,
            "prev_hash": self.prev_hash,
            "sequence": self.sequence,
        }, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "actor": self.actor,
            "verdict": self.verdict,
            "evidence": self.evidence,
            "prev_hash": self.prev_hash,
            "entry_hash": self.entry_hash,
            "sequence": self.sequence,
        }


class TamperEvidentAuditTrail:
    """
    Audit trail dengan hash chain (linked list) dan Merkle tree.
    Setiap entry di-hash dan linked ke entry sebelumnya.
    """

    def __init__(self, log_file: str = ".governance/acs_audit.jsonl") -> None:
        self.log_file = log_file
        self._entries: List[AuditEntry] = []
        self._sequence = 0
        self._last_hash = "0" * 64
        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
        self._load_existing()

    def _load_existing(self) -> None:
        if not os.path.exists(self.log_file):
            return
        with open(self.log_file, "r") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    entry = AuditEntry(
                        timestamp=data["timestamp"],
                        event_type=data["event_type"],
                        actor=data["actor"],
                        verdict=data["verdict"],
                        evidence=data["evidence"],
                        prev_hash=data["prev_hash"],
                        entry_hash=data["entry_hash"],
                        sequence=data["sequence"],
                    )
                    self._entries.append(entry)
                    self._sequence = entry.sequence
                    self._last_hash = entry.entry_hash
                except (json.JSONDecodeError, KeyError):
                    continue

    def record(self, event_type: str, actor: str, verdict: str, evidence: Dict[str, Any]) -> AuditEntry:
        self._sequence += 1
        entry = AuditEntry(
            timestamp=time.time(),
            event_type=event_type,
            actor=actor,
            verdict=verdict,
            evidence=evidence,
            prev_hash=self._last_hash,
            sequence=self._sequence,
        )
        entry.entry_hash = entry.compute_hash()
        self._entries.append(entry)
        self._last_hash = entry.entry_hash
        self._append_to_file(entry)
        return entry

    def _append_to_file(self, entry: AuditEntry) -> None:
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")

    def verify_integrity(self) -> bool:
        """Verify hash chain integrity."""
        for i, entry in enumerate(self._entries):
            expected = entry.compute_hash()
            if entry.entry_hash != expected:
                return False
            if i > 0:
                if entry.prev_hash != self._entries[i - 1].entry_hash:
                    return False
            else:
                if entry.prev_hash != "0" * 64:
                    return False
        return True

    def merkle_root(self, entries: Optional[List[AuditEntry]] = None) -> str:
        """Compute Merkle root hash for a batch of entries."""
        items = entries if entries is not None else self._entries
        if not items:
            return "0" * 64
        hashes = [e.entry_hash for e in items]
        while len(hashes) > 1:
            if len(hashes) % 2 == 1:
                hashes.append(hashes[-1])
            new_hashes = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + hashes[i + 1]
                new_hashes.append(hashlib.sha256(combined.encode()).hexdigest())
            hashes = new_hashes
        return hashes[0]

    def get_entries(self, event_type: Optional[str] = None, actor: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        results = []
        for entry in reversed(self._entries):
            if event_type and entry.event_type != event_type:
                continue
            if actor and entry.actor != actor:
                continue
            results.append(entry.to_dict())
            if len(results) >= limit:
                break
        return results

    def get_chain(self, start: int = 1, end: Optional[int] = None) -> List[Dict[str, Any]]:
        end = end or len(self._entries)
        return [e.to_dict() for e in self._entries[start - 1:end]]

    def stats(self) -> Dict[str, Any]:
        return {
            "total_entries": len(self._entries),
            "last_hash": self._last_hash,
            "integrity": self.verify_integrity(),
            "merkle_root": self.merkle_root(),
        }


def run():
    print("=" * 60)
    print("ACS Tamper-Evident Audit Trail — Demo")
    print("=" * 60)

    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        log_path = f.name

    audit = TamperEvidentAuditTrail(log_path)

    print("\n[1] Recording 5 audit entries")
    for i in range(1, 6):
        entry = audit.record(
            event_type="tool_call",
            actor=f"agent_{i}",
            verdict="allow" if i % 2 == 1 else "deny",
            evidence={"tool": f"tool_{i}", "args": {"x": i}},
        )
        print(f"   Seq {entry.sequence}: {entry.entry_hash[:16]}... prev={entry.prev_hash[:16]}...")

    print("\n[2] Integrity check")
    print(f"   Valid: {audit.verify_integrity()}")

    print("\n[3] Merkle root")
    print(f"   Root: {audit.merkle_root()}")

    print("\n[4] Stats")
    print(f"   {audit.stats()}")

    print("\n[5] Tamper test")
    # Try to detect tampering
    audit2 = TamperEvidentAuditTrail(log_path)
    print(f"   Loaded {len(audit2._entries)} entries, integrity: {audit2.verify_integrity()}")

    os.unlink(log_path)
    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
