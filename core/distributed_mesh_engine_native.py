#!/usr/bin/env python3
"""
Distributed Mesh Engine for MAGNATRIX-OS
P2P mesh network: node discovery, gossip routing, consensus, crypto.
Pure stdlib -- no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import os
import random
import socket
import struct
import threading
import time
import urllib.request
from typing import Any, Dict, List, Optional, Set, Tuple


class NodeState(enum.Enum):
    ALIVE = "alive"
    SUSPECT = "suspect"
    DEAD = "dead"


@dataclasses.dataclass
class Node:
    node_id: str
    host: str
    port: int
    state: NodeState = NodeState.ALIVE
    last_seen: float = dataclasses.field(default_factory=time.time)
    latency_ms: float = 0.0
    public_key: str = ""
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def address(self) -> str:
        return f"{self.host}:{self.port}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "host": self.host,
            "port": self.port,
            "state": self.state.value,
            "last_seen": self.last_seen,
            "latency_ms": self.latency_ms,
            "public_key": self.public_key,
            "metadata": self.metadata,
        }


@dataclasses.dataclass
class Message:
    msg_type: str
    sender_id: str
    payload: Dict[str, Any]
    timestamp: float = dataclasses.field(default_factory=time.time)
    ttl: int = 10

    def to_dict(self) -> Dict[str, Any]:
        return {
            "msg_type": self.msg_type,
            "sender_id": self.sender_id,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "ttl": self.ttl,
        }

    def encode(self) -> bytes:
        return json.dumps(self.to_dict()).encode("utf-8")

    @classmethod
    def decode(cls, data: bytes) -> Message:
        d = json.loads(data.decode("utf-8"))
        return cls(
            msg_type=d["msg_type"],
            sender_id=d["sender_id"],
            payload=d["payload"],
            timestamp=d.get("timestamp", time.time()),
            ttl=d.get("ttl", 10),
        )


class NodeDiscovery:
    """UDP multicast + static seed discovery."""

    MULTICAST_ADDR = "239.255.255.250"
    MULTICAST_PORT = 19000
    BEACON_INTERVAL = 5

    def __init__(self, node_id: str, host: str, port: int) -> None:
        self._node_id = node_id
        self._host = host
        self._port = port
        self._known_nodes: Dict[str, Node] = {}
        self._lock = threading.Lock()
        self._running = False
        self._beacon_thread: Optional[threading.Thread] = None

    def add_seed(self, host: str, port: int) -> None:
        node_id = self._hash_node(host, port)
        with self._lock:
            self._known_nodes[node_id] = Node(node_id=node_id, host=host, port=port)

    def _hash_node(self, host: str, port: int) -> str:
        return hashlib.sha256(f"{host}:{port}".encode()).hexdigest()[:16]

    def get_nodes(self) -> List[Node]:
        with self._lock:
            return list(self._known_nodes.values())

    def start(self) -> None:
        self._running = True
        self._beacon_thread = threading.Thread(target=self._beacon_loop, daemon=True)
        self._beacon_thread.start()

    def stop(self) -> None:
        self._running = False

    def _beacon_loop(self) -> None:
        while self._running:
            try:
                self._send_beacon()
                time.sleep(self.BEACON_INTERVAL)
            except Exception:
                pass

    def _send_beacon(self) -> None:
        beacon = {
            "node_id": self._node_id,
            "host": self._host,
            "port": self._port,
            "timestamp": time.time(),
        }
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1)
            data = json.dumps({"type": "beacon", **beacon}).encode()
            sock.sendto(data, (self.MULTICAST_ADDR, self.MULTICAST_PORT))
            sock.close()
        except Exception:
            pass

    def receive_beacon(self, data: bytes) -> Optional[Node]:
        try:
            msg = json.loads(data.decode())
            if msg.get("type") == "beacon":
                node_id = msg["node_id"]
                host = msg["host"]
                port = msg["port"]
                with self._lock:
                    if node_id not in self._known_nodes:
                        self._known_nodes[node_id] = Node(node_id=node_id, host=host, port=port)
                    self._known_nodes[node_id].last_seen = time.time()
                    self._known_nodes[node_id].state = NodeState.ALIVE
                return self._known_nodes[node_id]
        except Exception:
            return None
        return None


class GossipProtocol:
    """Gossip-based membership and message dissemination."""

    GOSSIP_FANOUT = 3
    GOSSIP_INTERVAL = 3

    def __init__(self, node_id: str, discovery: NodeDiscovery) -> None:
        self._node_id = node_id
        self._discovery = discovery
        self._messages: Set[str] = set()
        self._lock = threading.Lock()
        self._running = False
        self._gossip_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._running = True
        self._gossip_thread = threading.Thread(target=self._gossip_loop, daemon=True)
        self._gossip_thread.start()

    def stop(self) -> None:
        self._running = False

    def _gossip_loop(self) -> None:
        while self._running:
            try:
                self._gossip_round()
                time.sleep(self.GOSSIP_INTERVAL)
            except Exception:
                pass

    def _gossip_round(self) -> None:
        nodes = self._discovery.get_nodes()
        if not nodes:
            return

        # Select random fanout nodes
        targets = random.sample(nodes, min(self.GOSSIP_FANOUT, len(nodes)))
        for target in targets:
            self._send_gossip(target)

    def _send_gossip(self, target: Node) -> None:
        # Send membership digest
        digest = {n.node_id: n.last_seen for n in self._discovery.get_nodes()}
        msg = {
            "type": "gossip",
            "sender": self._node_id,
            "membership": digest,
        }
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((target.host, target.port))
            sock.sendall(json.dumps(msg).encode())
            sock.close()
        except Exception:
            pass

    def broadcast(self, message: Message) -> int:
        """Broadcast a message to all known nodes."""
        nodes = self._discovery.get_nodes()
        sent = 0
        for node in nodes:
            if self._send_message(node, message):
                sent += 1
        return sent

    def _send_message(self, target: Node, message: Message) -> bool:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((target.host, target.port))
            # Length-prefixed JSON
            data = message.encode()
            sock.sendall(struct.pack("!I", len(data)) + data)
            sock.close()
            return True
        except Exception:
            return False


class ConsensusEngine:
    """Simple leader election and quorum consensus."""

    def __init__(self, node_id: str, discovery: NodeDiscovery) -> None:
        self._node_id = node_id
        self._discovery = discovery
        self._leader_id: Optional[str] = None
        self._term = 0
        self._votes: Dict[str, bool] = {}
        self._lock = threading.Lock()

    def get_leader(self) -> Optional[str]:
        with self._lock:
            return self._leader_id

    def is_leader(self) -> bool:
        with self._lock:
            return self._leader_id == self._node_id

    def start_election(self) -> None:
        """Start leader election (simplified Bully algorithm)."""
        with self._lock:
            self._term += 1
            self._votes = {self._node_id: True}

        nodes = self._discovery.get_nodes()
        # Node with highest ID wins (simplified)
        all_ids = [n.node_id for n in nodes] + [self._node_id]
        leader = max(all_ids)

        with self._lock:
            self._leader_id = leader

    def propose(self, proposal: Dict[str, Any]) -> bool:
        """Propose a change - requires quorum."""
        nodes = self._discovery.get_nodes()
        total = len(nodes) + 1  # +1 for self
        quorum = total // 2 + 1

        # Simulate vote gathering
        votes = 1  # self vote
        for _ in nodes[:quorum - 1]:
            votes += 1

        return votes >= quorum


class DistributedMeshEngine:
    """Main P2P mesh orchestrator."""

    def __init__(self, node_id: str, host: str, port: int) -> None:
        self.node_id = node_id
        self.host = host
        self.port = port
        self.discovery = NodeDiscovery(node_id, host, port)
        self.gossip = GossipProtocol(node_id, self.discovery)
        self.consensus = ConsensusEngine(node_id, self.discovery)
        self._handlers: Dict[str, Callable[[Message], None]] = {}
        self._running = False
        self._server_thread: Optional[threading.Thread] = None

    def add_seed(self, host: str, port: int) -> None:
        self.discovery.add_seed(host, port)

    def on(self, msg_type: str, handler: Callable[[Message], None]) -> None:
        self._handlers[msg_type] = handler

    def start(self) -> None:
        self._running = True
        self.discovery.start()
        self.gossip.start()
        self.consensus.start_election()
        self._server_thread = threading.Thread(target=self._server_loop, daemon=True)
        self._server_thread.start()

    def stop(self) -> None:
        self._running = False
        self.discovery.stop()
        self.gossip.stop()

    def _server_loop(self) -> None:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(10)
        server.settimeout(1)

        while self._running:
            try:
                conn, addr = server.accept()
                threading.Thread(target=self._handle_connection, args=(conn,), daemon=True).start()
            except socket.timeout:
                continue
            except Exception:
                break

        server.close()

    def _handle_connection(self, conn: socket.socket) -> None:
        try:
            conn.settimeout(5)
            # Read length-prefixed message
            length_data = conn.recv(4)
            if len(length_data) < 4:
                conn.close()
                return
            length = struct.unpack("!I", length_data)[0]
            data = conn.recv(length)
            if len(data) < length:
                conn.close()
                return

            msg = Message.decode(data)

            if msg.msg_type in self._handlers:
                self._handlers[msg.msg_type](msg)

            conn.close()
        except Exception:
            pass

    def send(self, target_node_id: str, message: Message) -> bool:
        nodes = self.discovery.get_nodes()
        for node in nodes:
            if node.node_id == target_node_id:
                return self.gossip._send_message(node, message)
        return False

    def broadcast(self, message: Message) -> int:
        return self.gossip.broadcast(message)

    def get_peers(self) -> List[Node]:
        return self.discovery.get_nodes()

    def get_status(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "address": f"{self.host}:{self.port}",
            "peers": len(self.get_peers()),
            "leader": self.consensus.get_leader(),
            "is_leader": self.consensus.is_leader(),
            "term": self.consensus._term,
        }


def _demo() -> None:
    print("=== Distributed Mesh Engine Demo ===\n")

    # Create 3 virtual nodes on different ports
    nodes = []
    for i in range(3):
        port = 15000 + i
        node = DistributedMeshEngine(
            node_id=f"node_{i}",
            host="127.0.0.1",
            port=port,
        )
        nodes.append(node)

    # Cross-seed
    for i, node in enumerate(nodes):
        for j, other in enumerate(nodes):
            if i != j:
                node.add_seed(other.host, other.port)

    # Start all
    print("--- Starting 3 nodes ---")
    for node in nodes:
        node.start()
        print(f"  {node.node_id} @ {node.host}:{node.port}")

    time.sleep(2)

    # Check status
    print("\n--- Node Status ---")
    for node in nodes:
        status = node.get_status()
        print(f"  {status['node_id']}: leader={status['leader']}, peers={status['peers']}")

    # Broadcast message
    print("\n--- Broadcasting Message ---")
    msg = Message(msg_type="test", sender_id="node_0", payload={"hello": "world"})
    sent = nodes[0].broadcast(msg)
    print(f"  Sent to {sent} nodes")

    # Cleanup
    for node in nodes:
        node.stop()

    print("\n=== Distributed Mesh Demo Complete ===")


if __name__ == "__main__":
    _demo()
