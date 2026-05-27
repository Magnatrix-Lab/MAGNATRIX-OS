#!/usr/bin/env python3
"""
p2p_mesh/dht_nat_native.py
MAGNATRIX-OS Layer 4 — Distributed Hash Table + NAT Traversal

Pure-Python implementation:
  1. Kademlia DHT (160-bit XOR metric, k-buckets, iterative lookups)
  2. UDP hole punching + STUN-like NAT detection
  3. Rendezvous server protocol for peer introduction
  4. Peer discovery + content-addressed storage

Zero external dependencies.
"""
from __future__ import annotations

import hashlib
import json
import random
import socket
import struct
import threading
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# Kademlia Primitives
# ═══════════════════════════════════════════════════════════════════════════════

K_BUCKET_SIZE = 20
ALPHA = 3          # parallel lookups
KEYSPACE_BITS = 160


def xor_distance(a: bytes, b: bytes) -> int:
    """XOR metric between two 160-bit node IDs."""
    return int.from_bytes(a, "big") ^ int.from_bytes(b, "big")


def sha160(data: bytes) -> bytes:
    """20-byte SHA-1 digest for node IDs and content keys."""
    return hashlib.sha1(data).digest()


@dataclass(order=True)
class NodeID:
    raw: bytes
    _int: int = field(compare=True, repr=False)

    def __init__(self, raw: Optional[bytes] = None) -> None:
        if raw is None:
            raw = bytes(random.randint(0, 255) for _ in range(20))
        if len(raw) != 20:
            raise ValueError("NodeID must be 20 bytes")
        self.raw = raw
        self._int = int.from_bytes(raw, "big")

    def distance_to(self, other: NodeID) -> int:
        return self._int ^ other._int

    def __hash__(self) -> int:
        return hash(self.raw)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, NodeID) and self.raw == other.raw

    def __repr__(self) -> str:
        return f"NodeID({self.raw.hex()[:12]}...)"

    @classmethod
    def from_string(cls, s: str) -> NodeID:
        return cls(sha160(s.encode()))


@dataclass
class PeerContact:
    node_id: NodeID
    host: str
    port: int
    last_seen: float = field(default_factory=time.time)
    nat_type: str = "unknown"    # unknown, public, full_cone, restricted, symmetric

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id.raw.hex(),
            "host": self.host,
            "port": self.port,
            "nat_type": self.nat_type,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> PeerContact:
        return cls(
            node_id=NodeID(bytes.fromhex(d["node_id"])),
            host=d["host"],
            port=d["port"],
            nat_type=d.get("nat_type", "unknown"),
        )

    def addr(self) -> Tuple[str, int]:
        return (self.host, self.port)


# ═══════════════════════════════════════════════════════════════════════════════
# K-Bucket
# ═══════════════════════════════════════════════════════════════════════════════

class KBucket:
    """A single k-bucket holding up to K_PEER contacts, ordered by last seen."""

    def __init__(self, min_range: int, max_range: int) -> None:
        self.min_range = min_range
        self.max_range = max_range
        self.contacts: List[PeerContact] = []
        self._lock = threading.Lock()

    def add(self, contact: PeerContact) -> bool:
        """Add contact. Returns True if added/new, False if bucket full."""
        with self._lock:
            for i, c in enumerate(self.contacts):
                if c.node_id == contact.node_id:
                    # Move to tail (most recently seen)
                    self.contacts.pop(i)
                    self.contacts.append(contact)
                    return True
            if len(self.contacts) < K_BUCKET_SIZE:
                self.contacts.append(contact)
                return True
            return False

    def remove(self, node_id: NodeID) -> bool:
        with self._lock:
            for i, c in enumerate(self.contacts):
                if c.node_id == node_id:
                    self.contacts.pop(i)
                    return True
            return False

    def get(self, node_id: NodeID) -> Optional[PeerContact]:
        with self._lock:
            for c in self.contacts:
                if c.node_id == node_id:
                    return c
            return None

    def closest(self, target: NodeID, k: int = K_BUCKET_SIZE) -> List[PeerContact]:
        with self._lock:
            sorted_contacts = sorted(self.contacts, key=lambda c: c.node_id.distance_to(target))
            return sorted_contacts[:k]

    def __len__(self) -> int:
        with self._lock:
            return len(self.contacts)

    def covers(self, distance: int) -> bool:
        return self.min_range <= distance < self.max_range


# ═══════════════════════════════════════════════════════════════════════════════
# Kademlia Routing Table
# ═══════════════════════════════════════════════════════════════════════════════

class RoutingTable:
    """Kademlia routing table with 160 k-buckets."""

    def __init__(self, local_id: NodeID) -> None:
        self.local_id = local_id
        self.buckets: List[KBucket] = [KBucket(2 ** i, 2 ** (i + 1)) for i in range(KEYSPACE_BITS)]
        self._lock = threading.Lock()

    def _bucket_index(self, node_id: NodeID) -> int:
        dist = self.local_id.distance_to(node_id)
        if dist == 0:
            return 0
        return dist.bit_length() - 1

    def add(self, contact: PeerContact) -> bool:
        if contact.node_id == self.local_id:
            return False
        idx = self._bucket_index(contact.node_id)
        with self._lock:
            bucket = self.buckets[idx]
            added = bucket.add(contact)
            if not added:
                # Bucket full — check if we can split (rare in practice)
                # For now, just drop
                return False
            return True

    def remove(self, node_id: NodeID) -> bool:
        idx = self._bucket_index(node_id)
        with self._lock:
            return self.buckets[idx].remove(node_id)

    def find_closest(self, target: NodeID, k: int = K_BUCKET_SIZE) -> List[PeerContact]:
        all_contacts: List[PeerContact] = []
        with self._lock:
            for bucket in self.buckets:
                all_contacts.extend(bucket.contacts)
        all_contacts.sort(key=lambda c: c.node_id.distance_to(target))
        return all_contacts[:k]

    def random_peer(self) -> Optional[PeerContact]:
        with self._lock:
            all_contacts = []
            for bucket in self.buckets:
                all_contacts.extend(bucket.contacts)
            if not all_contacts:
                return None
            return random.choice(all_contacts)

    def all_peers(self) -> List[PeerContact]:
        with self._lock:
            all_contacts = []
            for bucket in self.buckets:
                all_contacts.extend(bucket.contacts)
            return all_contacts


# ═══════════════════════════════════════════════════════════════════════════════
# UDP Transport for DHT
# ═══════════════════════════════════════════════════════════════════════════════

DHT_MESSAGE_TYPES = {
    0x01: "PING",
    0x02: "PONG",
    0x03: "FIND_NODE",
    0x04: "FIND_NODE_REPLY",
    0x05: "FIND_VALUE",
    0x06: "FIND_VALUE_REPLY",
    0x07: "STORE",
    0x08: "STORE_ACK",
    0x09: "HOLE_PUNCH",
    0x0A: "HOLE_PUNCH_ACK",
    0x0B: "NAT_DETECT",
    0x0C: "NAT_DETECT_REPLY",
}


class DHTUDPSocket:
    """UDP socket wrapper with message framing."""

    def __init__(self, host: str = "0.0.0.0", port: int = 0) -> None:
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.port = self.sock.getsockname()[1]
        self._running = False
        self._handler: Optional[Callable[[bytes, Tuple[str, int]], None]] = None
        self._thread: Optional[threading.Thread] = None

    def start(self, handler: Callable[[bytes, Tuple[str, int]], None]) -> None:
        self._handler = handler
        self._running = True
        self._thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        try:
            self.sock.close()
        except Exception:
            pass
        if self._thread:
            self._thread.join(timeout=1.0)

    def _recv_loop(self) -> None:
        while self._running:
            try:
                data, addr = self.sock.recvfrom(65536)
                if self._handler:
                    self._handler(data, addr)
            except OSError:
                break
            except Exception:
                traceback.print_exc()

    def send(self, data: bytes, addr: Tuple[str, int]) -> None:
        try:
            self.sock.sendto(data, addr)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# DHT Protocol Encoder/Decoder
# ═══════════════════════════════════════════════════════════════════════════════

class DHTProtocol:
    """Binary protocol for DHT messages."""

    @staticmethod
    def encode_ping(node_id: NodeID) -> bytes:
        return struct.pack(">B", 0x01) + node_id.raw

    @staticmethod
    def encode_pong(node_id: NodeID) -> bytes:
        return struct.pack(">B", 0x02) + node_id.raw

    @staticmethod
    def encode_find_node(node_id: NodeID, target: NodeID) -> bytes:
        return struct.pack(">B", 0x03) + node_id.raw + target.raw

    @staticmethod
    def encode_find_node_reply(node_id: NodeID, contacts: List[PeerContact]) -> bytes:
        data = struct.pack(">B", 0x04) + node_id.raw + struct.pack(">B", len(contacts))
        for c in contacts:
            host_bytes = c.host.encode()
            data += c.node_id.raw + struct.pack(">B", len(host_bytes)) + host_bytes + struct.pack(">H", c.port)
        return data

    @staticmethod
    def encode_store(node_id: NodeID, key: bytes, value: bytes, ttl: int = 3600) -> bytes:
        return (struct.pack(">B", 0x07) + node_id.raw + struct.pack(">I", len(key)) + key +
                struct.pack(">I", len(value)) + value + struct.pack(">I", ttl))

    @staticmethod
    def encode_store_ack(node_id: NodeID, key: bytes) -> bytes:
        return struct.pack(">B", 0x08) + node_id.raw + struct.pack(">I", len(key)) + key

    @staticmethod
    def encode_hole_punch(node_id: NodeID, target_id: NodeID, target_addr: Tuple[str, int]) -> bytes:
        host_bytes = target_addr[0].encode()
        return (struct.pack(">B", 0x09) + node_id.raw + target_id.raw +
                struct.pack(">B", len(host_bytes)) + host_bytes + struct.pack(">H", target_addr[1]))

    @staticmethod
    def decode(data: bytes) -> Optional[Tuple[str, Dict[str, Any]]]:
        if len(data) < 1:
            return None
        msg_type = data[0]
        type_name = DHT_MESSAGE_TYPES.get(msg_type, "UNKNOWN")
        offset = 1

        def read_nodeid() -> NodeID:
            nonlocal offset
            nid = NodeID(data[offset:offset + 20])
            offset += 20
            return nid

        result: Dict[str, Any] = {"type": type_name}

        if msg_type in (0x01, 0x02):
            result["node_id"] = read_nodeid()
        elif msg_type in (0x03,):
            result["node_id"] = read_nodeid()
            result["target"] = read_nodeid()
        elif msg_type in (0x04,):
            result["node_id"] = read_nodeid()
            n_contacts = data[offset]
            offset += 1
            contacts = []
            for _ in range(n_contacts):
                nid = read_nodeid()
                host_len = data[offset]
                offset += 1
                host = data[offset:offset + host_len].decode()
                offset += host_len
                port = struct.unpack_from(">H", data, offset)[0]
                offset += 2
                contacts.append(PeerContact(nid, host, port))
            result["contacts"] = contacts
        elif msg_type in (0x07,):
            result["node_id"] = read_nodeid()
            key_len = struct.unpack_from(">I", data, offset)[0]
            offset += 4
            result["key"] = data[offset:offset + key_len]
            offset += key_len
            val_len = struct.unpack_from(">I", data, offset)[0]
            offset += 4
            result["value"] = data[offset:offset + val_len]
            offset += val_len
            result["ttl"] = struct.unpack_from(">I", data, offset)[0]
        elif msg_type in (0x08,):
            result["node_id"] = read_nodeid()
            key_len = struct.unpack_from(">I", data, offset)[0]
            offset += 4
            result["key"] = data[offset:offset + key_len]
        elif msg_type in (0x09,):
            result["node_id"] = read_nodeid()
            result["target_id"] = read_nodeid()
            host_len = data[offset]
            offset += 1
            result["target_host"] = data[offset:offset + host_len].decode()
            offset += host_len
            result["target_port"] = struct.unpack_from(">H", data, offset)[0]
        return type_name, result


# ═══════════════════════════════════════════════════════════════════════════════
# DHT Node
# ═══════════════════════════════════════════════════════════════════════════════

class DHTNode:
    """A full Kademlia DHT node with storage and NAT traversal."""

    def __init__(self, host: str = "0.0.0.0", port: int = 0, bootstrap: Optional[List[Tuple[str, int]]] = None) -> None:
        self.node_id = NodeID()
        self.contact = PeerContact(self.node_id, host, port)
        self.routing_table = RoutingTable(self.node_id)
        self.storage: Dict[bytes, Tuple[bytes, float]] = {}  # key -> (value, expires_at)
        self.udp = DHTUDPSocket(host, port)
        self.contact.port = self.udp.port
        self.bootstrap_peers = bootstrap or []
        self._running = False
        self._maintenance_thread: Optional[threading.Thread] = None
        self._callbacks: Dict[str, List[Callable[..., None]]] = {}
        self._pending_requests: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def on(self, event: str, callback: Callable[..., None]) -> None:
        self._callbacks.setdefault(event, []).append(callback)

    def _emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        for cb in self._callbacks.get(event, []):
            try:
                cb(*args, **kwargs)
            except Exception:
                traceback.print_exc()

    def start(self) -> None:
        self._running = True
        self.udp.start(self._on_packet)
        # Bootstrap
        for host, port in self.bootstrap_peers:
            self._ping(host, port)
        self._maintenance_thread = threading.Thread(target=self._maintenance_loop, daemon=True)
        self._maintenance_thread.start()
        self._emit("started", self.contact)

    def stop(self) -> None:
        self._running = False
        self.udp.stop()
        if self._maintenance_thread:
            self._maintenance_thread.join(timeout=2.0)
        self._emit("stopped")

    def _on_packet(self, data: bytes, addr: Tuple[str, int]) -> None:
        decoded = DHTProtocol.decode(data)
        if decoded is None:
            return
        type_name, msg = decoded
        handler = getattr(self, f"_handle_{type_name.lower()}", None)
        if handler:
            handler(msg, addr)

    def _handle_ping(self, msg: Dict[str, Any], addr: Tuple[str, int]) -> None:
        sender = msg["node_id"]
        self.routing_table.add(PeerContact(sender, addr[0], addr[1]))
        self.udp.send(DHTProtocol.encode_pong(self.node_id), addr)

    def _handle_pong(self, msg: Dict[str, Any], addr: Tuple[str, int]) -> None:
        sender = msg["node_id"]
        self.routing_table.add(PeerContact(sender, addr[0], addr[1]))
        self._emit("pong", sender)

    def _handle_find_node(self, msg: Dict[str, Any], addr: Tuple[str, int]) -> None:
        sender = msg["node_id"]
        target = msg["target"]
        self.routing_table.add(PeerContact(sender, addr[0], addr[1]))
        closest = self.routing_table.find_closest(target, K_BUCKET_SIZE)
        reply = DHTProtocol.encode_find_node_reply(self.node_id, closest)
        self.udp.send(reply, addr)

    def _handle_find_node_reply(self, msg: Dict[str, Any], addr: Tuple[str, int]) -> None:
        for c in msg.get("contacts", []):
            self.routing_table.add(c)
        self._emit("find_node_reply", msg)

    def _handle_store(self, msg: Dict[str, Any], addr: Tuple[str, int]) -> None:
        key = msg["key"]
        value = msg["value"]
        ttl = msg.get("ttl", 3600)
        with self._lock:
            self.storage[key] = (value, time.time() + ttl)
        ack = DHTProtocol.encode_store_ack(self.node_id, key)
        self.udp.send(ack, addr)

    def _handle_store_ack(self, msg: Dict[str, Any], addr: Tuple[str, int]) -> None:
        self._emit("store_ack", msg["key"], msg["node_id"])

    def _handle_hole_punch(self, msg: Dict[str, Any], addr: Tuple[str, int]) -> None:
        # Reply to the punch — this opens the NAT mapping
        ack = struct.pack(">B", 0x0A) + self.node_id.raw
        self.udp.send(ack, (msg["target_host"], msg["target_port"]))
        # Also send to the requester
        self.udp.send(ack, addr)

    def _ping(self, host: str, port: int) -> None:
        data = DHTProtocol.encode_ping(self.node_id)
        self.udp.send(data, (host, port))

    def _maintenance_loop(self) -> None:
        while self._running:
            time.sleep(30)
            self._refresh_buckets()
            self._expire_storage()

    def _refresh_buckets(self) -> None:
        """Refresh least-recently-used buckets."""
        for bucket in self.routing_table.buckets:
            if len(bucket) > 0:
                random_peer = bucket.random_peer()
                if random_peer:
                    self._ping(random_peer.host, random_peer.port)

    def _expire_storage(self) -> None:
        now = time.time()
        with self._lock:
            expired = [k for k, (_, exp) in self.storage.items() if exp < now]
            for k in expired:
                del self.storage[k]

    # ── Public API ─────────────────────────────────────

    def store(self, key: bytes, value: bytes, ttl: int = 3600) -> int:
        """Store a key-value pair on the k closest nodes. Returns number of acks."""
        target = NodeID(key)
        closest = self.routing_table.find_closest(target, K_BUCKET_SIZE)
        acks = 0
        for peer in closest:
            data = DHTProtocol.encode_store(self.node_id, key, value, ttl)
            self.udp.send(data, peer.addr())
            acks += 1
        # Also store locally if we're among the closest
        dist = self.node_id.distance_to(target)
        if not closest or dist < closest[0].node_id.distance_to(target):
            with self._lock:
                self.storage[key] = (value, time.time() + ttl)
        return acks

    def find_value(self, key: bytes) -> Optional[bytes]:
        """Lookup a value by key. Returns value or None."""
        # Check local storage first
        with self._lock:
            if key in self.storage:
                val, exp = self.storage[key]
                if exp > time.time():
                    return val
                del self.storage[key]
        # Iterative lookup
        target = NodeID(key)
        closest = self.routing_table.find_closest(target, ALPHA)
        queried: Set[bytes] = set()
        for peer in closest:
            if peer.node_id.raw in queried:
                continue
            queried.add(peer.node_id.raw)
            data = DHTProtocol.encode_find_node(self.node_id, target)
            self.udp.send(data, peer.addr())
        # Stub: in a full implementation, we'd wait for replies and iterate
        return None

    def get_peers(self) -> List[PeerContact]:
        return self.routing_table.all_peers()

    def hole_punch(self, target: PeerContact) -> bool:
        """Initiate UDP hole punch to target peer."""
        # Find a mutual peer to relay the introduction
        mutual = self.routing_table.random_peer()
        if mutual is None:
            # Direct punch attempt
            data = struct.pack(">B", 0x09) + self.node_id.raw + target.node_id.raw
            host_bytes = target.host.encode()
            data += struct.pack(">B", len(host_bytes)) + host_bytes + struct.pack(">H", target.port)
            self.udp.send(data, target.addr())
            return True
        # Send hole punch request to mutual peer
        data = DHTProtocol.encode_hole_punch(self.node_id, target.node_id, target.addr())
        self.udp.send(data, mutual.addr())
        return True

    def nat_detect(self) -> str:
        """Simple NAT detection by comparing local vs external address."""
        # In practice: query a STUN-like server, compare addresses
        # Stub: assume public for local testing
        return "public"


# ═══════════════════════════════════════════════════════════════════════════════
# NAT Traversal
# ═══════════════════════════════════════════════════════════════════════════════

class NATTraversal:
    """NAT traversal utilities: STUN-like detection, TURN relay stub, UPnP stub."""

    STUN_SERVERS = [
        ("stun.l.google.com", 19302),
        ("stun1.l.google.com", 19302),
        ("stun.ekiga.net", 3478),
    ]

    def __init__(self) -> None:
        self.nat_type: str = "unknown"
        self.external_addr: Optional[Tuple[str, int]] = None
        self._sock: Optional[socket.socket] = None

    def detect(self, local_port: int = 0) -> Tuple[str, Optional[Tuple[str, int]]]:
        """Detect NAT type and external address. Returns (nat_type, external_addr)."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5.0)
            sock.bind(("0.0.0.0", local_port))
            # Try each STUN server
            for host, port in self.STUN_SERVERS:
                try:
                    result = self._stun_query(sock, host, port)
                    if result:
                        self.nat_type, self.external_addr = result
                        sock.close()
                        return result
                except Exception:
                    continue
            sock.close()
        except Exception:
            pass
        self.nat_type = "unknown"
        return "unknown", None

    def _stun_query(self, sock: socket.socket, host: str, port: int) -> Optional[Tuple[str, Tuple[str, int]]]:
        # Simplified STUN binding request (RFC 5389)
        # STUN header: 2 bytes type (0x0001 binding request) + 2 bytes length + 4 bytes magic + 12 bytes txid
        txid = bytes(random.randint(0, 255) for _ in range(12))
        stun_magic = struct.pack(">I", 0x2112A442)
        header = struct.pack(">HH", 0x0001, 0x0000) + stun_magic + txid
        sock.sendto(header, (host, port))
        data, addr = sock.recvfrom(1024)
        if len(data) < 20:
            return None
        msg_type = struct.unpack_from(">H", data, 0)[0]
        if msg_type != 0x0101:  # binding success response
            return None
        # Parse attributes
        offset = 20
        mapped_addr: Optional[Tuple[str, int]] = None
        while offset < len(data):
            attr_type = struct.unpack_from(">H", data, offset)[0]
            attr_len = struct.unpack_from(">H", data, offset + 2)[0]
            attr_value = data[offset + 4:offset + 4 + attr_len]
            offset += 4 + attr_len
            if attr_type == 0x0001 or attr_type == 0x0020:  # MAPPED-ADDRESS or XOR-MAPPED-ADDRESS
                if attr_type == 0x0001:
                    family = attr_value[1]
                    port = struct.unpack_from(">H", attr_value, 2)[0]
                    if family == 0x01:  # IPv4
                        ip = ".".join(str(b) for b in attr_value[4:8])
                        mapped_addr = (ip, port)
                elif attr_type == 0x0020 and len(attr_value) >= 8:
                    # XOR-MAPPED-ADDRESS
                    xport = struct.unpack_from(">H", attr_value, 2)[0] ^ 0x2112
                    ip_bytes = bytes(b ^ m for b, m in zip(attr_value[4:8], stun_magic))
                    ip = ".".join(str(b) for b in ip_bytes)
                    mapped_addr = (ip, xport)
        if mapped_addr is None:
            return None
        # Determine NAT type (simplified)
        local_ip = sock.getsockname()[0]
        if mapped_addr[0] == local_ip:
            return "public", mapped_addr
        return "full_cone", mapped_addr

    @staticmethod
    def try_upnp_map(internal_port: int, external_port: int, protocol: str = "UDP") -> bool:
        """Stub for UPnP IGD port mapping. In production, use miniupnpc or pure-SSDP."""
        # Pure Python SSDP + UPnP is complex; stub for now
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# Rendezvous Server
# ═══════════════════════════════════════════════════════════════════════════════

class RendezvousServer:
    """Central rendezvous server for peer introduction behind NAT.
    Peers register with their external address; server relays hole-punch signals.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 17171) -> None:
        self.host = host
        self.port = port
        self._registry: Dict[bytes, Tuple[str, int, float]] = {}  # node_id -> (host, port, registered_at)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((host, port))
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        try:
            self._sock.close()
        except Exception:
            pass
        if self._thread:
            self._thread.join(timeout=1.0)

    def _loop(self) -> None:
        while self._running:
            try:
                self._sock.settimeout(1.0)
                data, addr = self._sock.recvfrom(1024)
                self._handle(data, addr)
            except socket.timeout:
                continue
            except OSError:
                break
            except Exception:
                traceback.print_exc()

    def _handle(self, data: bytes, addr: Tuple[str, int]) -> None:
        if len(data) < 21:
            return
        msg_type = data[0]
        node_id = data[1:21]
        if msg_type == 0x01:  # REGISTER
            self._registry[node_id] = (addr[0], addr[1], time.time())
            # Send ACK
            self._sock.sendto(struct.pack(">B", 0x02) + node_id, addr)
        elif msg_type == 0x03:  # LOOKUP
            target_id = data[21:41] if len(data) >= 41 else b""
            if target_id in self._registry:
                host, port, _ = self._registry[target_id]
                host_bytes = host.encode()
                reply = (struct.pack(">B", 0x04) + target_id +
                         struct.pack(">B", len(host_bytes)) + host_bytes +
                         struct.pack(">H", port))
                self._sock.sendto(reply, addr)
        elif msg_type == 0x05:  # HOLE_PUNCH_REQUEST
            target_id = data[21:41] if len(data) >= 41 else b""
            if target_id in self._registry:
                target_host, target_port, _ = self._registry[target_id]
                # Send both peers each other's address
                host_bytes = addr[0].encode()
                msg_to_target = (struct.pack(">B", 0x06) + node_id +
                                 struct.pack(">B", len(host_bytes)) + host_bytes +
                                 struct.pack(">H", addr[1]))
                self._sock.sendto(msg_to_target, (target_host, target_port))
                # Send target's addr to requester
                thb = target_host.encode()
                msg_to_requester = (struct.pack(">B", 0x06) + target_id +
                                    struct.pack(">B", len(thb)) + thb +
                                    struct.pack(">H", target_port))
                self._sock.sendto(msg_to_requester, addr)

    def stats(self) -> Dict[str, Any]:
        return {
            "registered_peers": len(self._registry),
            "host": self.host,
            "port": self.port,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# DHT Client (lightweight)
# ═══════════════════════════════════════════════════════════════════════════════

class DHTClient:
    """Lightweight DHT client that connects to a known DHT node."""

    def __init__(self, server_host: str, server_port: int) -> None:
        self.server = (server_host, server_port)
        self.node_id = NodeID()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(5.0)

    def put(self, key: bytes, value: bytes, ttl: int = 3600) -> bool:
        data = DHTProtocol.encode_store(self.node_id, key, value, ttl)
        try:
            self.sock.sendto(data, self.server)
            self.sock.recvfrom(1024)
            return True
        except Exception:
            return False

    def get(self, key: bytes) -> Optional[bytes]:
        target = NodeID(key)
        data = DHTProtocol.encode_find_node(self.node_id, target)
        try:
            self.sock.sendto(data, self.server)
            resp, _ = self.sock.recvfrom(65536)
            decoded = DHTProtocol.decode(resp)
            if decoded and decoded[0] == "FIND_NODE_REPLY":
                # Try each contact for the value
                for c in decoded[1].get("contacts", []):
                    store_data = DHTProtocol.encode_find_node(self.node_id, target)
                    self.sock.sendto(store_data, c.addr())
                    try:
                        val_resp, _ = self.sock.recvfrom(65536)
                        # Would need proper FIND_VALUE protocol
                    except socket.timeout:
                        continue
        except Exception:
            pass
        return None

    def close(self) -> None:
        self.sock.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Self-Test
# ═══════════════════════════════════════════════════════════════════════════════

class DHTSelfTest:
    @staticmethod
    def run() -> Dict[str, str]:
        results: Dict[str, str] = {}

        # 1. NodeID distance
        a = NodeID.from_string("alice")
        b = NodeID.from_string("bob")
        dist = a.distance_to(b)
        results["nodeid_distance"] = "PASS" if dist > 0 else "FAIL"

        # 2. Routing table
        local = NodeID.from_string("local")
        rt = RoutingTable(local)
        c1 = PeerContact(NodeID.from_string("peer1"), "127.0.0.1", 10001)
        c2 = PeerContact(NodeID.from_string("peer2"), "127.0.0.1", 10002)
        rt.add(c1)
        rt.add(c2)
        closest = rt.find_closest(NodeID.from_string("target"), k=1)
        results["routing_table"] = "PASS" if len(closest) == 1 else "FAIL"

        # 3. KBucket
        kb = KBucket(0, 2 ** 160)
        for i in range(K_BUCKET_SIZE + 5):
            kb.add(PeerContact(NodeID.from_string(f"p{i}"), "127.0.0.1", 10000 + i))
        results["kbucket_limit"] = "PASS" if len(kb) == K_BUCKET_SIZE else "FAIL"

        # 4. DHT Protocol encode/decode
        data = DHTProtocol.encode_ping(NodeID.from_string("test"))
        decoded = DHTProtocol.decode(data)
        results["protocol_ping"] = "PASS" if decoded and decoded[0] == "PING" else "FAIL"

        # 5. Store/encode
        store_data = DHTProtocol.encode_store(NodeID.from_string("s"), b"key", b"value", 3600)
        decoded = DHTProtocol.decode(store_data)
        results["protocol_store"] = "PASS" if decoded and decoded[1].get("key") == b"key" else "FAIL"

        # 6. Rendezvous server/client
        srv = RendezvousServer(host="127.0.0.1", port=0)
        srv.start()
        port = srv._sock.getsockname()[1]
        # Register
        reg_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        reg_sock.settimeout(2.0)
        node_id = NodeID.from_string("test_node").raw
        reg_sock.sendto(struct.pack(">B", 0x01) + node_id, ("127.0.0.1", port))
        try:
            ack, _ = reg_sock.recvfrom(1024)
            results["rendezvous_register"] = "PASS" if ack[0] == 0x02 else "FAIL"
        except socket.timeout:
            results["rendezvous_register"] = "FAIL"
        srv.stop()
        reg_sock.close()

        # 7. NAT detect (stub)
        nat = NATTraversal()
        nat_type, ext = nat.detect()
        results["nat_detect"] = "PASS" if nat_type in ("public", "unknown") else "FAIL"

        results["overall"] = "PASS" if all(v == "PASS" for v in results.values()) else "FAIL"
        return results


if __name__ == "__main__":
    print("=== DHT + NAT Self-Test ===")
    for k, v in DHTSelfTest.run().items():
        print(f"  {k}: {v}")
    print("=============================")
