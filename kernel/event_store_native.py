#!/usr/bin/env python3
"""
================================================================================
MAGNATRIX-OS — Event Store (Layer 0 Extension)
Append-Only Log with Merkle Tree, WORM Semantics, Snapshot + Delta, Log Compaction
================================================================================
Zero-dependency event sourcing engine with tamper-evident chain verification.
================================================================================
"""
from __future__ import annotations

import hashlib
import json
import os
import struct
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple


# =============================================================================
# Constants
# =============================================================================
DEFAULT_LOG_DIR = "/tmp/magnatrix_eventstore"
MAX_SEGMENT_SIZE = 10 * 1024 * 1024  # 10 MB per segment
SNAPSHOT_INTERVAL = 1000


# =============================================================================
# Data Types
# =============================================================================
class EntryType(Enum):
    COMMAND = "command"
    EVENT = "event"
    SNAPSHOT = "snapshot"
    SYSTEM = "system"


@dataclass
class LogEntry:
    index: int
    term: int
    entry_type: EntryType
    payload: Dict[str, Any]
    timestamp: float
    prev_hash: str
    hash: str = ""
    checksum: str = ""

    def compute_hash(self) -> str:
        data = json.dumps({
            "index": self.index,
            "term": self.term,
            "type": self.entry_type.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "prev": self.prev_hash,
        }, sort_keys=True, default=str)
        return hashlib.sha256(data.encode()).hexdigest()[:32]

    def compute_checksum(self) -> str:
        return hashlib.sha256(self.hash.encode()).hexdigest()[:16]

    def __post_init__(self) -> None:
        if not self.hash:
            self.hash = self.compute_hash()
        if not self.checksum:
            self.checksum = self.compute_checksum()


@dataclass
class MerkleNode:
    hash: str
    left: Optional["MerkleNode"] = None
    right: Optional["MerkleNode"] = None
    start_index: int = 0
    end_index: int = 0


# =============================================================================
# Merkle Tree
# =============================================================================
class MerkleTree:
    """Build Merkle tree over log entries for tamper verification."""

    def __init__(self) -> None:
        self.root: Optional[MerkleNode] = None
        self._leaves: List[str] = []

    def _hash_pair(self, a: str, b: str) -> str:
        return hashlib.sha256((a + b).encode()).hexdigest()[:32]

    def build(self, entry_hashes: List[str]) -> MerkleNode:
        if not entry_hashes:
            return MerkleNode(hash="0" * 32, start_index=0, end_index=0)
        self._leaves = list(entry_hashes)
        nodes = [MerkleNode(hash=h, start_index=i, end_index=i) for i, h in enumerate(entry_hashes)]
        while len(nodes) > 1:
            next_level = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                right = nodes[i + 1] if i + 1 < len(nodes) else left
                h = self._hash_pair(left.hash, right.hash)
                next_level.append(MerkleNode(
                    hash=h,
                    left=left,
                    right=right,
                    start_index=left.start_index,
                    end_index=right.end_index,
                ))
            nodes = next_level
        self.root = nodes[0]
        return self.root

    def verify(self, entry_hash: str, index: int, proof: List[Tuple[str, str]]) -> bool:
        """Verify an entry against root using Merkle proof."""
        current = entry_hash
        for sibling_hash, direction in proof:
            if direction == "left":
                current = self._hash_pair(sibling_hash, current)
            else:
                current = self._hash_pair(current, sibling_hash)
        return self.root is not None and current == self.root.hash

    def get_proof(self, index: int) -> List[Tuple[str, str]]:
        """Generate Merkle proof for an entry."""
        proof = []
        def traverse(node: MerkleNode, idx: int) -> bool:
            if node.left is None and node.right is None:
                return node.start_index == idx
            if node.left and traverse(node.left, idx):
                if node.right:
                    proof.append((node.right.hash, "left"))
                return True
            if node.right and traverse(node.right, idx):
                proof.append((node.left.hash, "right"))
                return True
            return False
        if self.root:
            traverse(self.root, index)
        return proof


# =============================================================================
# Log Segment
# =============================================================================
class LogSegment:
    """Immutable append-only log segment file."""

    def __init__(self, segment_id: int, path: str) -> None:
        self.segment_id = segment_id
        self.path = Path(path)
        self._entries: List[LogEntry] = []
        self._size = 0
        self._closed = False
        self._lock = threading.Lock()

    def append(self, entry: LogEntry) -> bool:
        with self._lock:
            if self._closed or self._size >= MAX_SEGMENT_SIZE:
                return False
            self._entries.append(entry)
            self._size += len(json.dumps(entry.__dict__, default=str).encode())
        return True

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._flush()

    def _flush(self) -> None:
        data = []
        for e in self._entries:
            data.append({
                "i": e.index,
                "t": e.term,
                "ty": e.entry_type.value,
                "p": e.payload,
                "ts": e.timestamp,
                "ph": e.prev_hash,
                "h": e.hash,
                "c": e.checksum,
            })
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"), default=str)

    @classmethod
    def load(cls, path: str) -> "LogSegment":
        segment = cls(0, path)
        if not Path(path).exists():
            return segment
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for raw in data:
            entry = LogEntry(
                index=raw["i"],
                term=raw["t"],
                entry_type=EntryType(raw["ty"]),
                payload=raw["p"],
                timestamp=raw["ts"],
                prev_hash=raw["ph"],
                hash=raw["h"],
                checksum=raw["c"],
            )
            segment._entries.append(entry)
        return segment

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[LogEntry]:
        return iter(self._entries)


# =============================================================================
# Snapshot Manager
# =============================================================================
class SnapshotManager:
    """Manage periodic state snapshots + delta logs."""

    def __init__(self, snapshot_dir: str) -> None:
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def save(self, state: Dict[str, Any], last_index: int, last_term: int) -> str:
        snapshot = {
            "state": state,
            "last_index": last_index,
            "last_term": last_term,
            "timestamp": time.time(),
        }
        path = self.snapshot_dir / f"snapshot_{last_index}_{int(time.time())}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, default=str)
        return str(path)

    def load_latest(self) -> Optional[Tuple[Dict[str, Any], int, int]]:
        snapshots = sorted(self.snapshot_dir.glob("snapshot_*.json"), key=lambda p: p.stat().st_mtime)
        if not snapshots:
            return None
        with open(snapshots[-1], "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["state"], data["last_index"], data["last_term"]

    def list_snapshots(self) -> List[str]:
        return sorted(str(p) for p in self.snapshot_dir.glob("snapshot_*.json"))


# =============================================================================
# Event Store Engine
# =============================================================================
class EventStore:
    """
    Tamper-evident append-only event log with Merkle tree verification,
    log segmentation, and snapshot support.
    """

    def __init__(self, log_dir: str = DEFAULT_LOG_DIR) -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._segments: List[LogSegment] = []
        self._current_segment: Optional[LogSegment] = None
        self._next_index = 1
        self._term = 1
        self._merkle = MerkleTree()
        self._snapshots = SnapshotManager(str(self.log_dir / "snapshots"))
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[LogEntry], None]] = []
        self._state: Dict[str, Any] = {}
        self._load_segments()

    def _load_segments(self) -> None:
        for p in sorted(self.log_dir.glob("segment_*.json")):
            segment = LogSegment.load(str(p))
            self._segments.append(segment)
            for entry in segment:
                self._next_index = max(self._next_index, entry.index + 1)
                self._term = max(self._term, entry.term)
        if self._segments:
            self._rebuild_merkle()
        self._start_new_segment()

    def _start_new_segment(self) -> None:
        seg_id = len(self._segments)
        path = self.log_dir / f"segment_{seg_id:04d}.json"
        self._current_segment = LogSegment(seg_id, str(path))
        self._segments.append(self._current_segment)

    def _rebuild_merkle(self) -> None:
        hashes = []
        for seg in self._segments:
            for entry in seg:
                hashes.append(entry.hash)
        self._merkle.build(hashes)

    def on_append(self, callback: Callable[[LogEntry], None]) -> None:
        self._callbacks.append(callback)

    def append(self, entry_type: EntryType, payload: Dict[str, Any], term: Optional[int] = None) -> LogEntry:
        with self._lock:
            idx = self._next_index
            t = term or self._term
            prev_hash = self._segments[-1]._entries[-1].hash if self._segments and self._segments[-1]._entries else "0" * 32
            entry = LogEntry(
                index=idx,
                term=t,
                entry_type=entry_type,
                payload=payload,
                timestamp=time.time(),
                prev_hash=prev_hash,
            )
            ok = self._current_segment.append(entry)
            if not ok:
                self._current_segment.close()
                self._start_new_segment()
                ok = self._current_segment.append(entry)
            self._next_index += 1
            # Update Merkle tree incrementally
            if self._merkle.root:
                self._merkle._leaves.append(entry.hash)
                self._merkle.build(self._merkle._leaves)
            else:
                self._merkle.build([entry.hash])
        for cb in self._callbacks:
            cb(entry)
        self._apply_to_state(entry)
        return entry

    def _apply_to_state(self, entry: LogEntry) -> None:
        """Apply entry to in-memory state (simplified state machine)."""
        if entry.entry_type == EntryType.COMMAND:
            op = entry.payload.get("op")
            key = entry.payload.get("key")
            val = entry.payload.get("value")
            if op == "set" and key:
                self._state[key] = val
            elif op == "delete" and key:
                self._state.pop(key, None)

    def read(self, index: int) -> Optional[LogEntry]:
        for seg in self._segments:
            for entry in seg:
                if entry.index == index:
                    return entry
        return None

    def read_range(self, start: int, end: int) -> List[LogEntry]:
        result = []
        for seg in self._segments:
            for entry in seg:
                if start <= entry.index <= end:
                    result.append(entry)
        return result

    def get_all(self) -> Iterator[LogEntry]:
        for seg in self._segments:
            for entry in seg:
                yield entry

    def last_entry(self) -> Optional[LogEntry]:
        for seg in reversed(self._segments):
            if seg._entries:
                return seg._entries[-1]
        return None

    def verify_integrity(self) -> bool:
        """Verify hash chain integrity."""
        prev_hash = "0" * 32
        for seg in self._segments:
            for entry in seg:
                if entry.prev_hash != prev_hash:
                    return False
                expected = entry.compute_hash()
                if entry.hash != expected:
                    return False
                prev_hash = entry.hash
        return True

    def verify_merkle(self, index: int) -> bool:
        """Verify entry at index using Merkle proof."""
        entry = self.read(index)
        if not entry:
            return False
        if not self._merkle.root:
            return True
        proof = self._merkle.get_proof(index - 1)
        return self._merkle.verify(entry.hash, index - 1, proof)

    def merkle_root(self) -> str:
        return self._merkle.root.hash if self._merkle.root else "0" * 32

    def snapshot(self) -> str:
        last = self.last_entry()
        if not last:
            return ""
        return self._snapshots.save(self._state, last.index, last.term)

    def restore_snapshot(self) -> bool:
        loaded = self._snapshots.load_latest()
        if not loaded:
            return False
        state, idx, term = loaded
        self._state = state
        self._next_index = idx + 1
        self._term = term
        return True

    def compact(self, before_index: int) -> int:
        """Remove segments before given index (after snapshot)."""
        removed = 0
        with self._lock:
            new_segments = []
            for seg in self._segments:
                if seg._entries and seg._entries[-1].index < before_index:
                    seg.path.unlink(missing_ok=True)
                    removed += len(seg._entries)
                else:
                    new_segments.append(seg)
            self._segments = new_segments
            if not self._current_segment in new_segments:
                self._start_new_segment()
            self._rebuild_merkle()
        return removed

    def state(self) -> Dict[str, Any]:
        return dict(self._state)

    def stats(self) -> Dict[str, Any]:
        total_entries = sum(len(seg) for seg in self._segments)
        return {
            "entries": total_entries,
            "segments": len(self._segments),
            "next_index": self._next_index,
            "term": self._term,
            "merkle_root": self.merkle_root(),
            "state_keys": len(self._state),
        }

    def shutdown(self) -> None:
        if self._current_segment:
            self._current_segment.close()

    def __enter__(self) -> "EventStore":
        return self

    def __exit__(self, *args: Any) -> None:
        self.shutdown()


# =============================================================================
# Event Store Kernel Bridge
# =============================================================================
class EventStoreKernelBridge:
    def __init__(self, store: EventStore, event_bus: Any = None) -> None:
        self.store = store
        self.bus = event_bus
        store.on_append(self._on_append)

    def _on_append(self, entry: LogEntry) -> None:
        if self.bus:
            self.bus.publish("eventstore.append", {
                "index": entry.index,
                "term": entry.term,
                "type": entry.entry_type.value,
            })


# =============================================================================
# Demo
# =============================================================================
def run_demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Event Store Demo")
    print("=" * 60)
    store = EventStore("/tmp/magnatrix_demo_eventstore")

    # Append entries
    for i in range(10):
        store.append(EntryType.COMMAND, {"op": "set", "key": f"var_{i}", "value": i * 10})

    print(f"Stats: {store.stats()}")
    print(f"Integrity check: {store.verify_integrity()}")
    print(f"Merkle root: {store.merkle_root()[:16]}...")

    # Verify specific entry
    ok = store.verify_merkle(5)
    print(f"Merkle verify entry #5: {ok}")

    # Snapshot
    snap = store.snapshot()
    print(f"Snapshot saved: {snap}")

    # Read back
    entry = store.read(3)
    if entry:
        print(f"Entry #3: {entry.payload}")

    # State
    print(f"State keys: {list(store.state().keys())[:5]}...")

    store.shutdown()
    print("Demo complete.")


if __name__ == "__main__":
    run_demo()
