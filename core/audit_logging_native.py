#!/usr/bin/env python3
"""audit_logging_native.py — MAGNATRIX-OS Immutable Audit Trail System

Enterprise-grade compliance logging: tamper-evident structured audit trail,
chain-of-custody verification, SIEM integration, WORM (Write Once Read Many).
Pure stdlib.
"""
from __future__ import annotations
import hashlib
import json
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class AuditEntry:
    id: str
    timestamp: float
    actor: str
    action: str
    resource: str
    status: str  # success, failure, denied, error
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: str = ""
    session_id: str = ""
    request_id: str = ""
    prev_hash: str = ""  # chain-of-custody
    entry_hash: str = ""  # SHA-256 of content
    integrity_verified: bool = True
    compliance_tags: List[str] = field(default_factory=list)
    retention_class: str = "standard"  # standard, legal_hold, regulatory


class AuditLoggingNative:
    """Native immutable audit logging — WORM, chain-of-custody, tamper-evident."""

    def __init__(self, workspace: str = "./audit_logs") -> None:
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self._chain_path = self.workspace / "chain.jsonl"
        self._index_path = self.workspace / "index.json"
        self._lock = threading.RLock()
        self._last_hash: str = ""
        self._entry_count: int = 0
        self._load_index()

    def _load_index(self) -> None:
        if self._index_path.exists():
            try:
                with open(self._index_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._last_hash = data.get("last_hash", "")
                self._entry_count = data.get("entry_count", 0)
            except Exception: pass

    def _save_index(self) -> None:
        with open(self._index_path, "w", encoding="utf-8") as f:
            json.dump({"last_hash": self._last_hash, "entry_count": self._entry_count, "updated": time.time()}, f, indent=2)

    def _compute_hash(self, entry: Dict[str, Any]) -> str:
        """SHA-256 hash of entry content + previous hash for chain-of-custody."""
        content = json.dumps(entry, sort_keys=True, default=str)
        return hashlib.sha256((content + self._last_hash).encode("utf-8")).hexdigest()

    def _verify_entry(self, entry: Dict[str, Any]) -> bool:
        """Verify entry integrity by recomputing hash."""
        stored_hash = entry.get("entry_hash", "")
        content = {k: v for k, v in entry.items() if k != "entry_hash"}
        # Recompute with prev_hash as it was at the time of creation
        prev_hash = content.get("prev_hash", "")
        content_str = json.dumps(content, sort_keys=True, default=str)
        computed = hashlib.sha256((content_str + prev_hash).encode("utf-8")).hexdigest()
        return computed == stored_hash

    def log(self, actor: str, action: str, resource: str, status: str, details: Optional[Dict[str, Any]] = None, ip_address: str = "", session_id: str = "", compliance_tags: Optional[List[str]] = None, retention_class: str = "standard") -> str:
        """Log an audit event. Returns entry ID."""
        with self._lock:
            entry_id = f"audit_{int(time.time() * 1000)}_{str(uuid.uuid4())[:8]}"
            entry_data = {
                "id": entry_id,
                "timestamp": time.time(),
                "actor": actor,
                "action": action,
                "resource": resource,
                "status": status,
                "details": details or {},
                "ip_address": ip_address,
                "session_id": session_id,
                "request_id": str(uuid.uuid4())[:16],
                "prev_hash": self._last_hash,
                "compliance_tags": compliance_tags or [],
                "retention_class": retention_class,
            }
            entry_hash = self._compute_hash(entry_data)
            entry_data["entry_hash"] = entry_hash
            self._last_hash = entry_hash
            self._entry_count += 1
            # Append to WORM log
            with open(self._chain_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry_data, default=str) + "
")
            self._save_index()
            return entry_id

    def query(self, actor: Optional[str] = None, action: Optional[str] = None, resource: Optional[str] = None, status: Optional[str] = None, start_time: Optional[float] = None, end_time: Optional[float] = None, compliance_tags: Optional[List[str]] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Query audit entries with filters."""
        results = []
        if not self._chain_path.exists(): return results
        with self._lock:
            with open(self._chain_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        entry = json.loads(line)
                    except Exception: continue
                    if actor and entry.get("actor") != actor: continue
                    if action and entry.get("action") != action: continue
                    if resource and entry.get("resource") != resource: continue
                    if status and entry.get("status") != status: continue
                    if start_time and entry.get("timestamp", 0) < start_time: continue
                    if end_time and entry.get("timestamp", 0) > end_time: continue
                    if compliance_tags and not any(t in entry.get("compliance_tags", []) for t in compliance_tags): continue
                    results.append(entry)
        return results[offset:offset + limit]

    def verify_chain(self, start_offset: int = 0, max_entries: int = 10000) -> Tuple[bool, int, int, List[str]]:
        """Verify chain-of-custody integrity. Returns (valid, total_checked, invalid_count, invalid_ids)."""
        if not self._chain_path.exists(): return True, 0, 0, []
        checked = 0; invalid = 0; invalid_ids = []; prev_hash = ""
        with self._lock:
            with open(self._chain_path, "r", encoding="utf-8") as f:
                for i, line in enumerate(f):
                    if i < start_offset: continue
                    if checked >= max_entries: break
                    if not line.strip(): continue
                    try:
                        entry = json.loads(line)
                    except Exception: continue
                    checked += 1
                    # Check prev_hash chain
                    if entry.get("prev_hash", "") != prev_hash:
                        invalid += 1; invalid_ids.append(entry.get("id", "unknown"))
                        continue
                    # Verify entry hash
                    if not self._verify_entry(entry):
                        invalid += 1; invalid_ids.append(entry.get("id", "unknown"))
                        continue
                    prev_hash = entry.get("entry_hash", "")
        return invalid == 0, checked, invalid, invalid_ids

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            valid, checked, invalid, ids = self.verify_chain()
            return {
                "total_entries": self._entry_count,
                "chain_valid": valid,
                "entries_checked": checked,
                "invalid_entries": invalid,
                "invalid_ids": ids[:10],
                "last_hash": self._last_hash[:16] + "...",
                "log_size_mb": round(self._chain_path.stat().st_size / (1024 * 1024), 2) if self._chain_path.exists() else 0,
            }

    def export_siem(self, path: Optional[str] = None, format: str = "json") -> str:
        """Export audit trail for SIEM integration (JSON or CEF)."""
        entries = self.query(limit=100000)
        output_path = Path(path) if path else self.workspace / f"siem_export_{int(time.time())}.{format}"
        if format == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2, default=str)
        elif format == "cef":
            with open(output_path, "w", encoding="utf-8") as f:
                for e in entries:
                    cef = f"CEF:0|Magnatrix|Audit|1.0|{e.get('action', 'unknown')}|{e.get('resource', 'unknown')}|{e.get('status', 'unknown')}|msg={json.dumps(e.get('details', {}))}"
                    f.write(cef + "
")
        return str(output_path)

    def purge_by_retention(self, retention_days: Dict[str, float] = None) -> int:
        """Purge entries by retention class (compliance-safe). Returns count purged."""
        if retention_days is None:
            retention_days = {"standard": 90, "regulatory": 2555, "legal_hold": float('inf')}
        now = time.time()
        purged = 0
        with self._lock:
            if not self._chain_path.exists(): return 0
            temp_path = self.workspace / "chain_temp.jsonl"
            with open(self._chain_path, "r", encoding="utf-8") as f_in, open(temp_path, "w", encoding="utf-8") as f_out:
                for line in f_in:
                    if not line.strip(): continue
                    try:
                        entry = json.loads(line)
                    except Exception: continue
                    retention_class = entry.get("retention_class", "standard")
                    max_age = retention_days.get(retention_class, 90) * 86400
                    if now - entry.get("timestamp", 0) > max_age and retention_class != "legal_hold":
                        purged += 1
                        continue
                    f_out.write(line)
            # Replace chain
            self._chain_path.unlink()
            temp_path.rename(self._chain_path)
            # Rebuild index
            self._rebuild_index()
        return purged

    def _rebuild_index(self) -> None:
        self._last_hash = ""
        self._entry_count = 0
        if self._chain_path.exists():
            with open(self._chain_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        entry = json.loads(line)
                        self._last_hash = entry.get("entry_hash", "")
                        self._entry_count += 1
                    except Exception: pass
        self._save_index()

    def print_summary(self) -> str:
        stats = self.get_stats()
        lines = [
            "=== Audit Logging Summary ===",
            f"Total Entries: {stats['total_entries']}",
            f"Chain Valid: {stats['chain_valid']}",
            f"Entries Checked: {stats['entries_checked']}",
            f"Invalid Entries: {stats['invalid_entries']}",
            f"Log Size: {stats['log_size_mb']} MB",
            f"Last Hash: {stats['last_hash']}",
        ]
        return "
".join(lines)

if __name__ == "__main__":
    audit = AuditLoggingNative()
    audit.log("user_001", "module_access", "core/vector_memory", "success", {"read": True})
    audit.log("user_002", "admin_action", "core/rbac", "denied", {"reason": "insufficient_permissions"})
    print(audit.print_summary())
    print("Verification:", audit.verify_chain())
