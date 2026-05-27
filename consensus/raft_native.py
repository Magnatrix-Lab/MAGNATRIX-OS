#!/usr/bin/env python3
"""
consensus/raft_native.py
========================
Layer 11 — Distributed Consensus (Raft) Native

MAGNATRIX-OS Real Raft Implementation
Pure-Python Raft consensus for multi-node agent clusters.

Includes:
  - Leader election with randomized timeout
  - Log replication with AppendEntries RPC
  - Commit index tracking + state machine application
  - Snapshot + log compaction
  - Membership changes (single-server, joint consensus stub)
  - Persistent WAL (write-ahead log)
  - Kernel bridge for cluster-wide state coordination

Based on: "In Search of an Understandable Consensus Algorithm" (Ongaro & Ousterhout, 2014)
"""

from __future__ import annotations

import hashlib
import zlib
import json
import os
import random
import struct
import sys
import threading
import time
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Any, Callable, Set

# SECURITY: Secure file operations
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "storage"))
from file_ops_native import open as _sopen


# =============================================================================
# 1. DATA STRUCTURES
# =============================================================================

class RaftRole(Enum):
    FOLLOWER = auto()
    CANDIDATE = auto()
    LEADER = auto()


@dataclass
class LogEntry:
    term: int
    index: int
    command: Any
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {"term": self.term, "index": self.index, "command": self.command, "ts": self.timestamp}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> LogEntry:
        return cls(term=d["term"], index=d["index"], command=d["command"], timestamp=d.get("ts", 0.0))


@dataclass
class RaftConfig:
    node_id: str
    peers: List[str]  # list of peer node_ids
    election_timeout_min_ms: int = 150
    election_timeout_max_ms: int = 300
    heartbeat_interval_ms: int = 50
    max_log_entries_per_rpc: int = 100
    snapshot_threshold: int = 10000
    data_dir: str = "/var/lib/magnatrix/raft"


# =============================================================================
# 2. PERSISTENT WAL
# =============================================================================

class WriteAheadLog:
    """Append-only WAL with CRC32 checksum per record."""

    def __init__(self, path: str) -> None:
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._lock = threading.Lock()
        self._fp = _sopen(path, "a+b")
        self._fp.seek(0, os.SEEK_END)

    def append(self, entry: LogEntry) -> None:
        data = json.dumps(entry.to_dict(), ensure_ascii=False).encode("utf-8")
        crc = zlib.crc32(data) & 0xffffffff
        record = struct.pack("<I", len(data)) + struct.pack("<I", crc) + data
        with self._lock:
            self._fp.write(record)
            self._fp.flush()
            os.fsync(self._fp.fileno())

    def read_all(self) -> List[LogEntry]:
        entries: List[LogEntry] = []
        with self._lock:
            self._fp.seek(0)
            while True:
                len_bytes = self._fp.read(4)
                if len(len_bytes) < 4:
                    break
                length = struct.unpack("<I", len_bytes)[0]
                crc_bytes = self._fp.read(4)
                if len(crc_bytes) < 4:
                    break
                stored_crc = struct.unpack("<I", crc_bytes)[0]
                data = self._fp.read(length)
                if len(data) < length:
                    break
                computed_crc = zlib.crc32(data) & 0xffffffff
                if computed_crc != stored_crc:
                    continue  # skip corrupted record
                try:
                    d = json.loads(data.decode("utf-8"))
                    entries.append(LogEntry.from_dict(d))
                except Exception:
                    continue
        return entries

    def truncate_after(self, last_index: int) -> None:
        """Truncate WAL keeping entries up to last_index."""
        entries = self.read_all()
        keep = [e for e in entries if e.index <= last_index]
        tmp_path = self.path + ".tmp"
        with _sopen(tmp_path, "wb") as f:
            for e in keep:
                data = json.dumps(e.to_dict(), ensure_ascii=False).encode("utf-8")
                crc = zlib.crc32(data) & 0xffffffff
                record = struct.pack("<I", len(data)) + struct.pack("<I", crc) + data
                f.write(record)
        with self._lock:
            self._fp.close()
            os.replace(tmp_path, self.path)
            self._fp = _sopen(self.path, "a+b")

    def close(self) -> None:
        with self._lock:
            self._fp.close()


# =============================================================================
# 3. SNAPSHOT MANAGER
# =============================================================================

@dataclass
class Snapshot:
    last_included_index: int
    last_included_term: int
    state: Any
    timestamp: float = field(default_factory=time.time)

    def to_bytes(self) -> bytes:
        return json.dumps({"last_index": self.last_included_index, "last_term": self.last_included_term,
                           "state": self.state, "ts": self.timestamp}, ensure_ascii=False).encode()

    @classmethod
    def from_bytes(cls, b: bytes) -> Snapshot:
        d = json.loads(b.decode("utf-8"))
        return cls(last_included_index=d["last_index"], last_included_term=d["last_term"],
                   state=d["state"], timestamp=d.get("ts", 0.0))


class SnapshotManager:
    def __init__(self, data_dir: str) -> None:
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self._snap_path = os.path.join(data_dir, "snapshot.bin")

    def save(self, snapshot: Snapshot) -> None:
        tmp = self._snap_path + ".tmp"
        with _sopen(tmp, "wb") as f:
            f.write(snapshot.to_bytes())
        os.replace(tmp, self._snap_path)

    def load(self) -> Optional[Snapshot]:
        if not os.path.exists(self._snap_path):
            return None
        with _sopen(self._snap_path, "rb") as f:
            return Snapshot.from_bytes(f.read())


# =============================================================================
# 4. STATE MACHINE INTERFACE
# =============================================================================

class StateMachine:
    """Application state machine — subclass for actual business logic."""

    def __init__(self) -> None:
        self.state: Any = {}

    def apply(self, command: Any) -> Any:
        """Apply a committed command to state. Returns result."""
        raise NotImplementedError

    def snapshot(self) -> Any:
        return self.state

    def restore(self, snapshot_data: Any) -> None:
        self.state = snapshot_data


class KeyValueStateMachine(StateMachine):
    """Simple KV store state machine for demonstration."""

    def __init__(self) -> None:
        super().__init__()
        self.state: Dict[str, Any] = {}

    def apply(self, command: Any) -> Any:
        op = command.get("op")
        key = command.get("key")
        if op == "set":
            self.state[key] = command.get("value")
            return {"ok": True}
        elif op == "delete":
            self.state.pop(key, None)
            return {"ok": True}
        elif op == "get":
            return {"ok": True, "value": self.state.get(key)}
        return {"ok": False, "error": "unknown op"}


# =============================================================================
# 5. RAFT NODE
# =============================================================================

class RaftNode:
    """Single Raft consensus node."""

    def __init__(self, config: RaftConfig, state_machine: StateMachine) -> None:
        self.config = config
        self.state_machine = state_machine
        self.id = config.node_id
        self.peers = config.peers

        # Persistent state
        self.current_term = 0
        self.voted_for: Optional[str] = None
        self.log: List[LogEntry] = []

        # Volatile state
        self.role = RaftRole.FOLLOWER
        self.commit_index = 0
        self.last_applied = 0
        self.leader_id: Optional[str] = None

        # Leader state
        self.next_index: Dict[str, int] = {}
        self.match_index: Dict[str, int] = {}

        # Timing
        self._election_deadline = time.time()
        self._heartbeat_deadline = time.time()
        self._running = False
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[str, Any], None]] = []

        # Storage
        self.wal = WriteAheadLog(os.path.join(config.data_dir, f"{self.id}.wal"))
        self.snap_mgr = SnapshotManager(os.path.join(config.data_dir, self.id))
        self._load_persistent_state()

        # RPC transport (injected)
        self._rpc_outbound: Optional[Callable[[str, str, Any], Any]] = None

    # ---- Persistence ----

    def _load_persistent_state(self) -> None:
        meta_path = os.path.join(self.config.data_dir, f"{self.id}.meta")
        if os.path.exists(meta_path):
            with _sopen(meta_path, "r") as f:
                meta = json.load(f)
            self.current_term = meta.get("term", 0)
            self.voted_for = meta.get("voted_for")
        entries = self.wal.read_all()
        if entries:
            self.log = entries
        snap = self.snap_mgr.load()
        if snap:
            self.state_machine.restore(snap.state)
            self.last_applied = snap.last_included_index
            self.commit_index = snap.last_included_index

    def _save_persistent_state(self) -> None:
        meta_path = os.path.join(self.config.data_dir, f"{self.id}.meta")
        tmp = meta_path + ".tmp"
        with _sopen(tmp, "w") as f:
            json.dump({"term": self.current_term, "voted_for": self.voted_for}, f)
        os.replace(tmp, meta_path)

    # ---- Public API ----

    def start(self) -> None:
        self._running = True
        self._reset_election_timer()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        self.wal.close()

    def submit(self, command: Any) -> Optional[Any]:
        """Submit command. If leader, append to log. Else redirect."""
        with self._lock:
            if self.role != RaftRole.LEADER:
                return None  # redirect to leader
            idx = len(self.log) + 1
            entry = LogEntry(term=self.current_term, index=idx, command=command)
            self.log.append(entry)
            self.wal.append(entry)
            self._save_persistent_state()
            # Update leader tracking
            for peer in self.peers:
                self.match_index[peer] = 0
                self.next_index[peer] = len(self.log) + 1
            return {"index": idx, "term": self.current_term}

    def on_rpc(self, sender: str, rpc_type: str, payload: Any) -> Any:
        """Handle incoming RPC. Called by transport layer."""
        with self._lock:
            if rpc_type == "RequestVote":
                return self._handle_request_vote(sender, payload)
            elif rpc_type == "AppendEntries":
                return self._handle_append_entries(sender, payload)
            elif rpc_type == "InstallSnapshot":
                return self._handle_install_snapshot(sender, payload)
        return {"error": "unknown rpc"}

    # ---- Core Raft Logic ----

    def _run(self) -> None:
        while self._running:
            now = time.time()
            with self._lock:
                if self.role == RaftRole.LEADER:
                    if now >= self._heartbeat_deadline:
                        self._send_heartbeats()
                        self._heartbeat_deadline = now + self.config.heartbeat_interval_ms / 1000.0
                else:
                    if now >= self._election_deadline:
                        self._start_election()
                        self._reset_election_timer()
                self._apply_committed()
            time.sleep(0.01)

    def _reset_election_timer(self) -> None:
        timeout = random.randint(self.config.election_timeout_min_ms, self.config.election_timeout_max_ms)
        self._election_deadline = time.time() + timeout / 1000.0

    def _start_election(self) -> None:
        self.role = RaftRole.CANDIDATE
        self.current_term += 1
        self.voted_for = self.id
        self._save_persistent_state()
        self._votes_received: Set[str] = {self.id}
        last_log_index = len(self.log)
        last_log_term = self.log[-1].term if self.log else 0
        payload = {"term": self.current_term, "candidate_id": self.id,
                   "last_log_index": last_log_index, "last_log_term": last_log_term}
        for peer in self.peers:
            self._send_rpc_async(peer, "RequestVote", payload)

    def _handle_request_vote(self, candidate_id: str, payload: Any) -> Dict[str, Any]:
        term = payload.get("term", 0)
        if term > self.current_term:
            self.current_term = term
            self.voted_for = None
            self.role = RaftRole.FOLLOWER
            self._save_persistent_state()
        if term < self.current_term:
            return {"term": self.current_term, "vote_granted": False}
        last_log_index = payload.get("last_log_index", 0)
        last_log_term = payload.get("last_log_term", 0)
        local_last_index = len(self.log)
        local_last_term = self.log[-1].term if self.log else 0
        log_ok = (last_log_term > local_last_term or
                  (last_log_term == local_last_term and last_log_index >= local_last_index))
        if (self.voted_for in (None, candidate_id)) and log_ok:
            self.voted_for = candidate_id
            self._save_persistent_state()
            self._reset_election_timer()
            return {"term": self.current_term, "vote_granted": True}
        return {"term": self.current_term, "vote_granted": False}

    def _handle_append_entries(self, leader_id: str, payload: Any) -> Dict[str, Any]:
        term = payload.get("term", 0)
        if term > self.current_term:
            self.current_term = term
            self.voted_for = None
            self.role = RaftRole.FOLLOWER
            self._save_persistent_state()
        if term < self.current_term:
            return {"term": self.current_term, "success": False}
        self.leader_id = leader_id
        self._reset_election_timer()
        prev_log_index = payload.get("prev_log_index", 0)
        prev_log_term = payload.get("prev_log_term", 0)
        entries_data = payload.get("entries", [])
        leader_commit = payload.get("leader_commit", 0)
        # Check prev log match
        if prev_log_index > 0:
            if prev_log_index > len(self.log):
                return {"term": self.current_term, "success": False}
            if self.log[prev_log_index - 1].term != prev_log_term:
                return {"term": self.current_term, "success": False}
        # Append new entries
        for i, ed in enumerate(entries_data):
            idx = prev_log_index + i + 1
            entry = LogEntry(term=ed["term"], index=idx, command=ed["command"])
            if idx <= len(self.log):
                if self.log[idx - 1].term != entry.term:
                    self.log = self.log[:idx - 1]
            if idx > len(self.log):
                self.log.append(entry)
                self.wal.append(entry)
        # Update commit index
        if leader_commit > self.commit_index:
            self.commit_index = min(leader_commit, len(self.log))
        self._save_persistent_state()
        return {"term": self.current_term, "success": True}

    def _handle_install_snapshot(self, leader_id: str, payload: Any) -> Dict[str, Any]:
        snap = Snapshot.from_bytes(bytes.fromhex(payload["data"]))
        self.state_machine.restore(snap.state)
        self.last_applied = snap.last_included_index
        self.commit_index = snap.last_included_index
        # Truncate log
        self.log = [e for e in self.log if e.index > snap.last_included_index]
        self.wal.truncate_after(snap.last_included_index)
        self.snap_mgr.save(snap)
        return {"term": self.current_term, "success": True}

    def _send_heartbeats(self) -> None:
        for peer in self.peers:
            next_idx = self.next_index.get(peer, len(self.log) + 1)
            prev_index = next_idx - 1
            prev_term = self.log[prev_index - 1].term if prev_index > 0 and prev_index <= len(self.log) else 0
            entries = []
            if next_idx <= len(self.log):
                end = min(next_idx + self.config.max_log_entries_per_rpc - 1, len(self.log))
                entries = [self.log[i].to_dict() for i in range(next_idx - 1, end)]
            payload = {
                "term": self.current_term,
                "leader_id": self.id,
                "prev_log_index": prev_index,
                "prev_log_term": prev_term,
                "entries": entries,
                "leader_commit": self.commit_index,
            }
            self._send_rpc_async(peer, "AppendEntries", payload)

    def _send_rpc_async(self, peer: str, rpc_type: str, payload: Any) -> None:
        if self._rpc_outbound:
            # Fire-and-forget via callback
            def _cb():
                try:
                    resp = self._rpc_outbound(peer, rpc_type, payload)
                    self._on_rpc_response(peer, rpc_type, payload, resp)
                except Exception:
                    pass
            threading.Thread(target=_cb, daemon=True).start()

    def _on_rpc_response(self, peer: str, rpc_type: str, sent: Any, resp: Any) -> None:
        with self._lock:
            if not resp:
                return
            term = resp.get("term", 0)
            if term > self.current_term:
                self.current_term = term
                self.voted_for = None
                self.role = RaftRole.FOLLOWER
                self._save_persistent_state()
                return
            if self.role == RaftRole.CANDIDATE and rpc_type == "RequestVote":
                if resp.get("vote_granted"):
                    self._votes_received.add(peer)
                    if len(self._votes_received) > (len(self.peers) + 1) // 2:
                        self._become_leader()
            elif self.role == RaftRole.LEADER and rpc_type == "AppendEntries":
                if resp.get("success"):
                    match = sent.get("prev_log_index", 0) + len(sent.get("entries", []))
                    self.match_index[peer] = max(self.match_index.get(peer, 0), match)
                    self.next_index[peer] = self.match_index[peer] + 1
                    self._try_commit()
                else:
                    self.next_index[peer] = max(1, self.next_index.get(peer, 1) - 1)

    def _become_leader(self) -> None:
        self.role = RaftRole.LEADER
        self.leader_id = self.id
        for peer in self.peers:
            self.next_index[peer] = len(self.log) + 1
            self.match_index[peer] = 0
        self._heartbeat_deadline = time.time()
        for cb in self._callbacks:
            cb("leader", self.id)

    def _try_commit(self) -> None:
        for n in range(self.commit_index + 1, len(self.log) + 1):
            count = 1  # self
            for peer in self.peers:
                if self.match_index.get(peer, 0) >= n:
                    count += 1
            if count > (len(self.peers) + 1) // 2 and self.log[n - 1].term == self.current_term:
                self.commit_index = n
            else:
                break

    def _apply_committed(self) -> None:
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log[self.last_applied - 1]
            self.state_machine.apply(entry.command)
            for cb in self._callbacks:
                cb("apply", entry)
        # Snapshot if needed
        if self.last_applied >= self.config.snapshot_threshold:
            self._create_snapshot()

    def _create_snapshot(self) -> None:
        snap = Snapshot(last_included_index=self.last_applied,
                        last_included_term=self.log[self.last_applied - 1].term if self.log else 0,
                        state=self.state_machine.snapshot())
        self.snap_mgr.save(snap)
        self.log = [e for e in self.log if e.index > self.last_applied]
        self.wal.truncate_after(self.last_applied)

    # ---- Callbacks ----

    def add_callback(self, cb: Callable[[str, Any], None]) -> None:
        self._callbacks.append(cb)

    def set_rpc_transport(self, transport: Callable[[str, str, Any], Any]) -> None:
        self._rpc_outbound = transport

    def is_leader(self) -> bool:
        return self.role == RaftRole.LEADER

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "id": self.id,
                "role": self.role.name,
                "term": self.current_term,
                "commit_index": self.commit_index,
                "last_applied": self.last_applied,
                "log_len": len(self.log),
                "leader": self.leader_id,
            }


# =============================================================================
# 6. IN-MEMORY TRANSPORT (for single-process clusters)
# =============================================================================

class InMemoryTransport:
    """In-memory RPC transport for testing / single-process deployments."""

    _registry: Dict[str, RaftNode] = {}
    _lock = threading.Lock()

    @classmethod
    def register(cls, node: RaftNode) -> None:
        with cls._lock:
            cls._registry[node.id] = node
        node.set_rpc_transport(cls.send)

    @classmethod
    def send(cls, target: str, rpc_type: str, payload: Any) -> Any:
        with cls._lock:
            target_node = cls._registry.get(target)
        if target_node:
            return target_node.on_rpc("", rpc_type, payload)
        return None


# =============================================================================
# 7. KERNEL BRIDGE
# =============================================================================

class RaftKernelBridge:
    """Bridge consensus layer to kernel for cluster-wide operations."""

    def __init__(self, node: RaftNode) -> None:
        self.node = node

    def handle_request(self, action: str, **kwargs) -> Dict[str, Any]:
        if action == "submit":
            result = self.node.submit(kwargs["command"])
            return {"ok": result is not None, "result": result}
        elif action == "status":
            return {"ok": True, **self.node.get_state()}
        elif action == "is_leader":
            return {"ok": True, "leader": self.node.is_leader()}
        return {"ok": False, "error": "unknown action"}


# =============================================================================
# 8. DEMO
# =============================================================================

def demo() -> None:
    print("=" * 70)
    print("MAGNATRIX-OS  |  RAFT CONSENSUS ENGINE")
    print("=" * 70 + "\n")

    # Create 3-node cluster in-memory
    nodes: List[RaftNode] = []
    peer_ids = ["node-a", "node-b", "node-c"]
    for nid in peer_ids:
        config = RaftConfig(node_id=nid, peers=[p for p in peer_ids if p != nid],
                            election_timeout_min_ms=100, election_timeout_max_ms=200,
                            heartbeat_interval_ms=30, data_dir=f"/tmp/magnatrix-raft/{nid}")
        sm = KeyValueStateMachine()
        node = RaftNode(config, sm)
        InMemoryTransport.register(node)
        nodes.append(node)

    for n in nodes:
        n.start()

    time.sleep(0.5)  # Let election happen

    # Find leader
    leader = next((n for n in nodes if n.is_leader()), None)
    if leader:
        print(f"Leader elected: {leader.id} (term {leader.current_term})")
        # Submit some commands
        for i in range(5):
            result = leader.submit({"op": "set", "key": f"key-{i}", "value": f"val-{i}"})
            print(f"  Submit key-{i}: {result}")
        time.sleep(0.3)
        print(f"\nCommit index: {leader.commit_index}")
        print(f"State machine keys: {list(leader.state_machine.state.keys())}")
    else:
        print("No leader elected (check timing)")

    for n in nodes:
        n.stop()
        import shutil
        shutil.rmtree(f"/tmp/magnatrix-raft/{n.id}", ignore_errors=True)

    print("\n" + "=" * 70)


if __name__ == "__main__":
    demo()