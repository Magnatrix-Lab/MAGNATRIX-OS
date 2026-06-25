#!/usr/bin/env python3
"""
Federation & Multi-Instance Sync for MAGNATRIX-OS
Multi-node synchronization, conflict resolution, eventual consistency.
Pure stdlib — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import hashlib
import json
import socket
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


@dataclass
class NodeState:
    """State of a remote node in the federation."""
    node_id: str
    address: str
    last_seen: float
    state_hash: str
    modules: List[str] = field(default_factory=list)
    is_active: bool = True


@dataclass
class SyncPayload:
    """Payload for state synchronization."""
    source_node: str
    timestamp: float
    state: Dict[str, Any]
    vector_clock: Dict[str, int]
    checksum: str


@dataclass
class Conflict:
    """A detected conflict between nodes."""
    key: str
    local_value: Any
    remote_value: Any
    local_timestamp: float
    remote_timestamp: float
    resolution: str = "pending"


class VectorClock:
    """Lamport-style vector clock for distributed events."""

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self.clock: Dict[str, int] = {node_id: 0}

    def increment(self) -> None:
        self.clock[self.node_id] = self.clock.get(self.node_id, 0) + 1

    def merge(self, other: Dict[str, int]) -> None:
        for node, count in other.items():
            self.clock[node] = max(self.clock.get(node, 0), count)

    def compare(self, other: Dict[str, int]) -> int:
        """Return -1 if self < other, 1 if self > other, 0 if concurrent."""
        dominates = False
        dominated = False
        all_nodes = set(self.clock.keys()) | set(other.keys())
        for node in all_nodes:
            a = self.clock.get(node, 0)
            b = other.get(node, 0)
            if a > b:
                dominates = True
            elif b > a:
                dominated = True
        if dominates and not dominated:
            return 1
        if dominated and not dominates:
            return -1
        return 0

    def to_dict(self) -> Dict[str, int]:
        return dict(self.clock)


class ConflictResolver:
    """Resolve conflicts between divergent state."""

    STRATEGIES = ["last_write_wins", "first_write_wins", "merge", "manual"]

    def __init__(self, strategy: str = "last_write_wins") -> None:
        self.strategy = strategy

    def resolve(self, conflict: Conflict) -> Any:
        if self.strategy == "last_write_wins":
            return conflict.remote_value if conflict.remote_timestamp > conflict.local_timestamp else conflict.local_value
        elif self.strategy == "first_write_wins":
            return conflict.local_value if conflict.local_timestamp < conflict.remote_timestamp else conflict.remote_value
        elif self.strategy == "merge":
            return self._merge_values(conflict.local_value, conflict.remote_value)
        else:
            return conflict.local_value

    def _merge_values(self, a: Any, b: Any) -> Any:
        if isinstance(a, dict) and isinstance(b, dict):
            merged = dict(a)
            for k, v in b.items():
                if k not in merged:
                    merged[k] = v
                elif merged[k] != v:
                    merged[k] = v  # remote wins in merge
            return merged
        if isinstance(a, list) and isinstance(b, list):
            return list(set(a) | set(b))
        return b  # Default to remote

    def detect_conflicts(self, local_state: Dict[str, Any], remote_state: Dict[str, Any], remote_timestamp: float) -> List[Conflict]:
        conflicts = []
        for key in set(local_state.keys()) | set(remote_state.keys()):
            local_val = local_state.get(key)
            remote_val = remote_state.get(key)
            if local_val != remote_val:
                conflicts.append(Conflict(
                    key=key,
                    local_value=local_val,
                    remote_value=remote_val,
                    local_timestamp=time.time(),
                    remote_timestamp=remote_timestamp,
                ))
        return conflicts


class FederationNode:
    """A single node in the MAGNATRIX-OS federation."""

    def __init__(self, node_id: str, address: str, port: int = 9090, sync_interval: int = 30) -> None:
        self.node_id = node_id
        self.address = address
        self.port = port
        self.sync_interval = sync_interval
        self._vector_clock = VectorClock(node_id)
        self._peers: Dict[str, NodeState] = {}
        self._local_state: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._running = False
        self._sync_thread: Optional[threading.Thread] = None
        self._resolver = ConflictResolver()
        self._on_conflict: Optional[Callable[[Conflict], None]] = None
        self._on_sync: Optional[Callable[[str], None]] = None

    def set_state(self, key: str, value: Any) -> None:
        with self._lock:
            self._vector_clock.increment()
            self._local_state[key] = {
                "value": value,
                "timestamp": time.time(),
                "vector_clock": self._vector_clock.to_dict(),
            }

    def get_state(self, key: str) -> Any:
        with self._lock:
            entry = self._local_state.get(key)
            return entry["value"] if entry else None

    def get_full_state(self) -> Dict[str, Any]:
        with self._lock:
            return {k: v["value"] for k, v in self._local_state.items()}

    def _state_hash(self) -> str:
        state_json = json.dumps(self._local_state, sort_keys=True, default=str)
        return hashlib.sha256(state_json.encode()).hexdigest()[:16]

    def _build_payload(self) -> SyncPayload:
        with self._lock:
            return SyncPayload(
                source_node=self.node_id,
                timestamp=time.time(),
                state=self.get_full_state(),
                vector_clock=self._vector_clock.to_dict(),
                checksum=self._state_hash(),
            )

    def _receive_sync(self, payload: SyncPayload) -> Dict[str, Any]:
        """Process incoming sync from peer."""
        with self._lock:
            # Merge vector clocks
            self._vector_clock.merge(payload.vector_clock)
            self._vector_clock.increment()

            # Detect conflicts
            conflicts = self._resolver.detect_conflicts(self.get_full_state(), payload.state, payload.timestamp)

            resolved = {}
            for conflict in conflicts:
                conflict.resolution = self._resolver.strategy
                resolved_value = self._resolver.resolve(conflict)
                resolved[conflict.key] = resolved_value
                self._local_state[conflict.key] = {
                    "value": resolved_value,
                    "timestamp": time.time(),
                    "vector_clock": self._vector_clock.to_dict(),
                }
                if self._on_conflict:
                    self._on_conflict(conflict)

            # Merge non-conflicting keys
            for key, value in payload.state.items():
                if key not in resolved:
                    if key not in self._local_state:
                        self._local_state[key] = {
                            "value": value,
                            "timestamp": payload.timestamp,
                            "vector_clock": payload.vector_clock,
                        }

            return {"resolved": len(conflicts), "merged": len(payload.state) - len(conflicts)}

    def add_peer(self, node_id: str, address: str) -> None:
        with self._lock:
            self._peers[node_id] = NodeState(node_id=node_id, address=address, last_seen=time.time(), state_hash="")

    def remove_peer(self, node_id: str) -> None:
        with self._lock:
            self._peers.pop(node_id, None)

    def _sync_loop(self) -> None:
        """Background sync loop."""
        while self._running:
            time.sleep(self.sync_interval)
            if not self._running:
                break
            for peer_id, peer in list(self._peers.items()):
                try:
                    payload = self._build_payload()
                    # Simulate network send (in real impl, use UDP/multicast or HTTP)
                    result = self._simulate_peer_sync(peer, payload)
                    if result:
                        peer.last_seen = time.time()
                        peer.state_hash = payload.checksum
                        if self._on_sync:
                            self._on_sync(peer_id)
                except Exception:
                    pass

    def _simulate_peer_sync(self, peer: NodeState, payload: SyncPayload) -> bool:
        """Simulate sending sync to peer. In real impl, this would be network call."""
        return True

    def start(self) -> None:
        self._running = True
        self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True, name="FederationSync")
        self._sync_thread.start()

    def stop(self) -> None:
        self._running = False

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "node_id": self.node_id,
                "peers": len(self._peers),
                "state_keys": len(self._local_state),
                "vector_clock": self._vector_clock.to_dict(),
                "running": self._running,
            }


class FederationManager:
    """Manager for multi-instance federation."""

    def __init__(self, repo_root: str, node_id: Optional[str] = None) -> None:
        self.root = Path(repo_root).resolve()
        self.node_id = node_id or f"node_{uuid.uuid4().hex[:8]}"
        self.node = FederationNode(self.node_id, "0.0.0.0")
        self._synced_keys: Set[str] = set()

    def discover_peers(self, broadcast_addr: str = "255.255.255.255", port: int = 9090) -> List[str]:
        """Discover peers via UDP broadcast."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(2)
            sock.sendto(b"MAGNATRIX_DISCOVER", (broadcast_addr, port))
            peers = []
            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    if data.startswith(b"MAGNATRIX_NODE"):
                        peer_id = data.decode().split(":")[1]
                        peers.append(peer_id)
                        self.node.add_peer(peer_id, addr[0])
                except socket.timeout:
                    break
            sock.close()
            return peers
        except Exception:
            return []

    def sync_key(self, key: str) -> bool:
        """Mark a key for cross-node synchronization."""
        self._synced_keys.add(key)
        return True

    def get_cluster_state(self) -> Dict[str, Any]:
        """Get aggregated state across all known nodes."""
        return {
            "local_node": self.node.stats(),
            "peers": [
                {"node_id": p.node_id, "address": p.address, "active": p.is_active}
                for p in self.node._peers.values()
            ],
            "synced_keys": list(self._synced_keys),
        }

    def start(self) -> None:
        self.node.start()

    def stop(self) -> None:
        self.node.stop()

    def stats(self) -> Dict[str, Any]:
        return {
            "node": self.node.stats(),
            "synced_keys": len(self._synced_keys),
            "cluster_size": len(self.node._peers) + 1,
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== Federation & Multi-Instance Sync Demo ===\n")
    # Create two nodes
    node_a = FederationNode("node_a", "192.168.1.1")
    node_b = FederationNode("node_b", "192.168.1.2")

    node_a.add_peer("node_b", "192.168.1.2")
    node_b.add_peer("node_a", "192.168.1.1")

    # Set state on node A
    node_a.set_state("config.theme", "dark")
    node_a.set_state("config.port", 8080)

    # Simulate sync from A to B
    payload = node_a._build_payload()
    result = node_b._receive_sync(payload)
    print(f"Node B received sync: {result}")
    print(f"Node B state: {node_b.get_full_state()}")

    # Concurrent update on B
    node_b.set_state("config.theme", "light")
    print(f"Node B updated theme: {node_b.get_full_state()}")

    # Sync back to A - conflict detected
    payload_b = node_b._build_payload()
    result_a = node_a._receive_sync(payload_b)
    print(f"Node A received sync (conflict resolved): {result_a}")
    print(f"Node A final state: {node_a.get_full_state()}")

    print(f"\nNode A stats: {node_a.stats()}")
    print(f"Node B stats: {node_b.stats()}")


if __name__ == "__main__":
    _demo()
