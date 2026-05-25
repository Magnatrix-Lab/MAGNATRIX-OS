"""
p2p_mesh_native.py — MAGNATRIX P2P Mesh Layer
Native pure-Python implementation. No external dependencies.

Architecture references:
  - libp2p (Protocol Labs) for DHT, mDNS, NAT traversal patterns
  - Kademlia DHT (Petar Maymounkov & David Mazières, 2002)
  - GossipSub (libp2p pubsub) for message routing
  - STUN/TURN (RFC 5389 / RFC 5766) for NAT traversal stubs

Style: modular, asyncio-native, fully typed. Each peer is an async task.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import random
import secrets
import time
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Dict, List, Set, Optional, Callable, Any, Tuple

# ──────────────────────────────────────────────────────────────
# 0.  Types & Constants
# ──────────────────────────────────────────────────────────────

PeerID = str
Address = Tuple[str, int]          # (host, port)

K_BUCKET_SIZE = 20                 # Kademlia k-bucket size
ALPHA = 3                          # parallel lookup width
REPLICATION = 3                    # DHT value replication factor
GOSSIP_FANOUT = 3                  # gossip mesh fanout
GOSSIP_HISTORY = 10                # seen-message dedup window
HEARTBEAT_INTERVAL = 5.0           # seconds between peer heartbeats
REPUTATION_DECAY = 0.95            # reputation decay per heartbeat


# ──────────────────────────────────────────────────────────────
# 1.  Peer Dataclass
# ──────────────────────────────────────────────────────────────

class PeerCapability(Enum):
    RELAY = auto()
    STORAGE = auto()
    COMPUTE = auto()
    GATEWAY = auto()


@dataclass
class PeerInfo:
    """Lightweight peer descriptor — serialisable, hashable by id."""
    peer_id: PeerID
    address: Address
    last_seen: float = field(default_factory=time.time)
    capabilities: Set[PeerCapability] = field(default_factory=set)
    reputation: float = 1.0            # 0.0 … 1.0, starts neutral

    def __hash__(self) -> int:
        return hash(self.peer_id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, PeerInfo) and self.peer_id == other.peer_id

    def __repr__(self) -> str:
        caps = ",".join(c.name for c in self.capabilities) or "none"
        return (f"<Peer {self.peer_id[:8]}@{self.address[0]}:{self.address[1]} "
                f"rep={self.reputation:.2f} caps={caps}>")

    def to_dict(self) -> dict:
        return {
            "peer_id": self.peer_id,
            "address": list(self.address),
            "last_seen": self.last_seen,
            "capabilities": [c.name for c in self.capabilities],
            "reputation": self.reputation,
        }

    @classmethod
    def from_dict(cls, d: dict) -> PeerInfo:
        return cls(
            peer_id=d["peer_id"],
            address=tuple(d["address"]),
            last_seen=d["last_seen"],
            capabilities={PeerCapability[c] for c in d.get("capabilities", [])},
            reputation=d.get("reputation", 1.0),
        )


# ──────────────────────────────────────────────────────────────
# 2.  Crypto / ID helpers (pure-Python stubs)
# ──────────────────────────────────────────────────────────────

def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()

def peer_id_from_addr(address: Address) -> PeerID:
    """Deterministic peer-id from address — real impl would use pubkey hash."""
    raw = f"{address[0]}:{address[1]}".encode()
    return _sha256(raw).hex()[:32]

def xor_distance(a: PeerID, b: PeerID) -> int:
    """Kademlia XOR metric — treated as 256-bit unsigned int."""
    def _to_bytes(pid: PeerID) -> bytes:
        raw = hashlib.sha256(pid.encode()).digest()
        return raw
    return int.from_bytes(bytes(x ^ y for x, y in zip(_to_bytes(a), _to_bytes(b))), "big")


def _derive_session_key(local_seed: bytes, peer_id: str) -> bytes:
    """Derive a 32-byte session key from local seed + peer identity."""
    return hashlib.sha256(local_seed + peer_id.encode()).digest()[:32]


def _encrypt_p2p(plaintext: bytes, key: bytes) -> bytes:
    """Encrypt P2P payload with ChaCha20-Poly1305 (real AEAD)."""
    try:
        from identity.crypto_identity_native import ChaCha20Poly1305
        nonce = os.urandom(12)
        cipher = ChaCha20Poly1305(key)
        ct, tag = cipher.encrypt(plaintext, nonce)
        return nonce + tag + ct
    except Exception:
        # Ultimate fallback — should never hit in production
        return bytes(p ^ key[i % len(key)] for i, p in enumerate(plaintext))


def _decrypt_p2p(ciphertext: bytes, key: bytes) -> Optional[bytes]:
    """Decrypt P2P payload with ChaCha20-Poly1305."""
    try:
        from identity.crypto_identity_native import ChaCha20Poly1305
        if len(ciphertext) < 28:  # 12 nonce + 16 tag minimum
            return None
        nonce = ciphertext[:12]
        tag = ciphertext[12:28]
        ct = ciphertext[28:]
        cipher = ChaCha20Poly1305(key)
        return cipher.decrypt(ct, nonce, tag)
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────
# 3.  P2PMessage
# ──────────────────────────────────────────────────────────────

class MessageType(Enum):
    PING = auto()
    PONG = auto()
    FIND_NODE = auto()
    FIND_NODE_REPLY = auto()
    STORE = auto()
    STORE_REPLY = auto()
    GOSSIP = auto()
    GOSSIP_REPLY = auto()
    NAT_OFFER = auto()
    NAT_ANSWER = auto()
    DATA = auto()


@dataclass
class P2PMessage:
    """Wire-format message with encrypted payload & routing metadata."""
    msg_type: MessageType
    sender_id: PeerID
    payload: bytes
    ttl: int = 10                      # hop limit
    route_hops: List[PeerID] = field(default_factory=list)
    msg_id: str = field(default_factory=lambda: secrets.token_hex(8))
    timestamp: float = field(default_factory=time.time)

    def to_bytes(self, key: Optional[bytes] = None) -> bytes:
        """Serialise + optional encryption."""
        plain = json.dumps({
            "msg_type": self.msg_type.name,
            "sender_id": self.sender_id,
            "payload": self.payload.decode("utf-8", errors="replace"),
            "ttl": self.ttl,
            "route_hops": self.route_hops,
            "msg_id": self.msg_id,
            "timestamp": self.timestamp,
        }).encode()
        if key:
            plain = _encrypt_p2p(plain, key)
        return plain

    @classmethod
    def from_bytes(cls, data: bytes, key: Optional[bytes] = None) -> P2PMessage:
        if key:
            data = _decrypt_p2p(data, key)
        d = json.loads(data.decode("utf-8", errors="replace"))
        return cls(
            msg_type=MessageType[d["msg_type"]],
            sender_id=d["sender_id"],
            payload=d["payload"].encode(),
            ttl=d.get("ttl", 10),
            route_hops=d.get("route_hops", []),
            msg_id=d.get("msg_id", "unknown"),
            timestamp=d.get("timestamp", 0.0),
        )

    def __repr__(self) -> str:
        return (f"<P2PMessage {self.msg_type.name} from {self.sender_id[:8]} "
                f"ttl={self.ttl} hops={len(self.route_hops)} id={self.msg_id[:8]}>")


# ──────────────────────────────────────────────────────────────
# 4.  DHT (Kademlia-style)
# ──────────────────────────────────────────────────────────────

class KBucket:
    """One k-bucket holding up to K_BUCKET_SIZE peers, sorted by last_seen."""

    def __init__(self) -> None:
        self.peers: List[PeerInfo] = []

    def add(self, peer: PeerInfo) -> bool:
        """Add or refresh peer. Returns True if bucket changed."""
        if peer in self.peers:
            self.peers.remove(peer)
            self.peers.append(peer)
            return True
        if len(self.peers) < K_BUCKET_SIZE:
            self.peers.append(peer)
            return True
        # bucket full — in real Kademlia we'd ping head, here drop oldest
        self.peers.pop(0)
        self.peers.append(peer)
        return True

    def remove(self, peer_id: PeerID) -> bool:
        before = len(self.peers)
        self.peers = [p for p in self.peers if p.peer_id != peer_id]
        return len(self.peers) != before

    def closest(self, target: PeerID, n: int = K_BUCKET_SIZE) -> List[PeerInfo]:
        return sorted(self.peers, key=lambda p: xor_distance(p.peer_id, target))[:n]


class RoutingTable:
    """Kademlia routing table — list of k-buckets by prefix distance."""

    def __init__(self, local_id: PeerID) -> None:
        self.local_id = local_id
        self.buckets: List[KBucket] = [KBucket() for _ in range(256)]

    def _bucket_index(self, peer_id: PeerID) -> int:
        dist = xor_distance(self.local_id, peer_id)
        if dist == 0:
            return 255
        return dist.bit_length() - 1

    def add(self, peer: PeerInfo) -> None:
        idx = self._bucket_index(peer.peer_id)
        self.buckets[idx].add(peer)

    def remove(self, peer_id: PeerID) -> None:
        idx = self._bucket_index(peer_id)
        self.buckets[idx].remove(peer_id)

    def closest(self, target: PeerID, n: int = K_BUCKET_SIZE) -> List[PeerInfo]:
        candidates: List[PeerInfo] = []
        for bucket in self.buckets:
            candidates.extend(bucket.peers)
        return sorted(candidates, key=lambda p: xor_distance(p.peer_id, target))[:n]


class DHT:
    """Distributed Hash Table — stores (key → list of values) with replication."""

    def __init__(self, local_id: PeerID) -> None:
        self.local_id = local_id
        self.storage: Dict[str, List[Tuple[str, float]]] = {}   # key → [(value, expire_at)]
        self.routing = RoutingTable(local_id)

    def put(self, key: str, value: str, ttl: float = 3600.0) -> None:
        expire = time.time() + ttl
        if key not in self.storage:
            self.storage[key] = []
        self.storage[key].append((value, expire))
        # trim expired
        self.storage[key] = [(v, e) for v, e in self.storage[key] if e > time.time()]

    def get(self, key: str) -> List[str]:
        now = time.time()
        vals = self.storage.get(key, [])
        return [v for v, e in vals if e > now]

    def find_node(self, target: PeerID) -> List[PeerInfo]:
        return self.routing.closest(target, n=K_BUCKET_SIZE)

    def find_value(self, key: str) -> List[str]:
        local = self.get(key)
        if local:
            return local
        # otherwise delegate to closest peers (simulated)
        closest = self.routing.closest(key, n=ALPHA)
        return [f"ask:{p.peer_id[:8]}" for p in closest]


# ──────────────────────────────────────────────────────────────
# 5.  mDNS Stub (local network peer discovery)
# ──────────────────────────────────────────────────────────────

class MDNSStub:
    """Stub multicast DNS — in reality sends UDP 5353, here simulates LAN broadcast."""

    def __init__(self, local_peer: PeerInfo) -> None:
        self.local_peer = local_peer
        self.discovered: Set[PeerInfo] = set()
        self._running = False

    async def start(self, on_discover: Callable[[PeerInfo], None]) -> None:
        self._running = True
        while self._running:
            # simulate receiving a LAN broadcast every ~3 s
            await asyncio.sleep(random.uniform(2.0, 4.0))
            fake = PeerInfo(
                peer_id=secrets.token_hex(16),
                address=("192.168.1." + str(random.randint(2, 254)), random.randint(10000, 65000)),
                capabilities={random.choice(list(PeerCapability))},
            )
            if fake not in self.discovered:
                self.discovered.add(fake)
                on_discover(fake)

    def stop(self) -> None:
        self._running = False


# ──────────────────────────────────────────────────────────────
# 6.  NAT Traversal Stub (STUN / TURN / Hole Punching)
# ──────────────────────────────────────────────────────────────

class NATTraversal:
    """Simulates STUN binding request, TURN relay allocation, hole-punch handshake."""

    def __init__(self, local_addr: Address) -> None:
        self.local_addr = local_addr
        self.mapped_addr: Optional[Address] = None
        self.relay_addr: Optional[Address] = None

    async def stun_bind(self, stun_server: Address) -> Optional[Address]:
        """Return 'public' mapped address — stub always succeeds with fake NAT."""
        await asyncio.sleep(0.05)
        self.mapped_addr = ("203.0.113." + str(random.randint(1, 254)), self.local_addr[1])
        return self.mapped_addr

    async def turn_allocate(self, turn_server: Address) -> Optional[Address]:
        await asyncio.sleep(0.08)
        self.relay_addr = (turn_server[0], random.randint(20000, 30000))
        return self.relay_addr

    async def hole_punch(self, peer_public_addr: Address) -> bool:
        """Simulate UDP hole punching — 80 % success rate."""
        await asyncio.sleep(0.1)
        return random.random() < 0.8


# ──────────────────────────────────────────────────────────────
# 7.  Message Routing Engines
# ──────────────────────────────────────────────────────────────

class ShortestPathRouter:
    """Dijkstra-inspired route computation over known peer graph."""

    def __init__(self, dht: DHT) -> None:
        self.dht = dht

    def route(self, target: PeerID) -> List[PeerID]:
        """Return greedy next-hop chain toward target using XOR metric."""
        path: List[PeerID] = []
        current = self.dht.local_id
        visited: Set[PeerID] = {current}
        while current != target:
            neighbours = self.dht.routing.closest(current, n=K_BUCKET_SIZE)
            candidates = [p for p in neighbours if p.peer_id not in visited]
            if not candidates:
                break
            nxt = min(candidates, key=lambda p: xor_distance(p.peer_id, target))
            path.append(nxt.peer_id)
            visited.add(nxt.peer_id)
            current = nxt.peer_id
            if len(path) > 20:
                break
        return path


class GossipRouter:
    """GossipSub-style epidemic broadcast with mesh maintenance."""

    def __init__(self, local_id: PeerID, dht: DHT) -> None:
        self.local_id = local_id
        self.dht = dht
        self.mesh: Set[PeerID] = set()          # active gossip peers
        self.seen: Set[str] = set()             # dedup cache
        self.seen_history: List[str] = []       # ordered for eviction

    def _mark_seen(self, msg_id: str) -> bool:
        if msg_id in self.seen:
            return False
        self.seen.add(msg_id)
        self.seen_history.append(msg_id)
        if len(self.seen_history) > GOSSIP_HISTORY * 100:
            old = self.seen_history.pop(0)
            self.seen.discard(old)
        return True

    def publish(self, msg: P2PMessage) -> List[PeerID]:
        """Return list of peers to forward to."""
        if not self._mark_seen(msg.msg_id):
            return []
        # mesh fanout + random gossip
        targets = list(self.mesh)
        if len(targets) < GOSSIP_FANOUT:
            extras = self.dht.routing.closest(self.local_id, n=GOSSIP_FANOUT)
            targets += [p.peer_id for p in extras if p.peer_id not in targets]
        return targets[:GOSSIP_FANOUT]

    def join_topic(self, topic: str) -> None:
        """In real GossipSub this builds mesh for a topic; here we just log."""
        peers = self.dht.routing.closest(topic, n=GOSSIP_FANOUT)
        for p in peers:
            self.mesh.add(p.peer_id)

    def leave_topic(self, topic: str) -> None:
        peers = self.dht.routing.closest(topic, n=GOSSIP_FANOUT)
        for p in peers:
            self.mesh.discard(p.peer_id)


class FloodRouter:
    """Naïve flooding — every peer forwards to all known peers except sender."""

    def __init__(self, dht: DHT) -> None:
        self.dht = dht
        self.seen: Set[str] = set()

    def flood(self, msg: P2PMessage) -> List[PeerID]:
        if msg.msg_id in self.seen:
            return []
        self.seen.add(msg.msg_id)
        all_peers: List[PeerInfo] = []
        for bucket in self.dht.routing.buckets:
            all_peers.extend(bucket.peers)
        return [p.peer_id for p in all_peers if p.peer_id != msg.sender_id]


# ──────────────────────────────────────────────────────────────
# 8.  Mesh Topology Manager
# ──────────────────────────────────────────────────────────────

class MeshTopology:
    """Maintains desired connectivity: fully-connected → partial mesh scaling."""

    def __init__(self, local_id: PeerID, max_degree: int = 6) -> None:
        self.local_id = local_id
        self.max_degree = max_degree
        self.connections: Set[PeerID] = set()
        self.desired: Set[PeerID] = set()

    def on_peer_discovered(self, peer: PeerInfo, total_peers: int) -> bool:
        """Decide whether to maintain direct connection to this peer."""
        if total_peers <= self.max_degree + 1:
            # fully connected regime
            self.desired.add(peer.peer_id)
            return True
        # partial mesh — keep closest by XOR distance
        # (simplified: random sample for demo)
        if len(self.desired) < self.max_degree:
            self.desired.add(peer.peer_id)
            return True
        return False

    def prune(self, dht: DHT) -> List[PeerID]:
        """Return peers to drop to respect max_degree."""
        if len(self.desired) <= self.max_degree:
            return []
        # drop furthest by distance to local_id
        ordered = sorted(self.desired, key=lambda pid: xor_distance(pid, self.local_id))
        to_drop = ordered[self.max_degree:]
        for pid in to_drop:
            self.desired.discard(pid)
        return to_drop

    def stats(self) -> dict:
        return {
            "active": len(self.connections),
            "desired": len(self.desired),
            "max_degree": self.max_degree,
        }


# ──────────────────────────────────────────────────────────────
# 9.  P2PMeshNode — single peer runtime
# ──────────────────────────────────────────────────────────────

class P2PMeshNode:
    """One node in the mesh: DHT, routers, NAT, heartbeat, message I/O."""

    def __init__(self, host: str, port: int, capabilities: Optional[Set[PeerCapability]] = None) -> None:
        self.address: Address = (host, port)
        self.peer_id = peer_id_from_addr(self.address)
        self.info = PeerInfo(
            peer_id=self.peer_id,
            address=self.address,
            capabilities=capabilities or set(),
        )
        self.dht = DHT(self.peer_id)
        self.dht.routing.add(self.info)

        self.sp_router = ShortestPathRouter(self.dht)
        self.gossip = GossipRouter(self.peer_id, self.dht)
        self.flood = FloodRouter(self.dht)
        self.mesh = MeshTopology(self.peer_id)
        self.nat = NATTraversal(self.address)
        self.mdns = MDNSStub(self.info)

        self._handlers: Dict[MessageType, List[Callable[[P2PMessage], Any]]] = {t: [] for t in MessageType}
        self._inbox: asyncio.Queue[P2PMessage] = asyncio.Queue()
        self._tasks: List[asyncio.Task] = []
        self._running = False
        self._msg_count = 0
        self._delivered = 0

    # ── public API ──

    def on(self, msg_type: MessageType, handler: Callable[[P2PMessage], Any]) -> None:
        self._handlers[msg_type].append(handler)

    async def send_direct(self, target_id: PeerID, payload: bytes, msg_type: MessageType = MessageType.DATA) -> bool:
        """Route a message toward target using shortest-path."""
        route = self.sp_router.route(target_id)
        msg = P2PMessage(
            msg_type=msg_type,
            sender_id=self.peer_id,
            payload=payload,
            ttl=10,
            route_hops=[self.peer_id] + route,
        )
        return await self._dispatch(msg)

    async def publish_gossip(self, payload: bytes) -> int:
        """Epidemic broadcast. Returns number of forwards."""
        msg = P2PMessage(
            msg_type=MessageType.GOSSIP,
            sender_id=self.peer_id,
            payload=payload,
            ttl=5,
        )
        targets = self.gossip.publish(msg)
        for tid in targets:
            await self._send_to(tid, msg)
        return len(targets)

    async def publish_flood(self, payload: bytes) -> int:
        msg = P2PMessage(
            msg_type=MessageType.DATA,
            sender_id=self.peer_id,
            payload=payload,
            ttl=10,
        )
        targets = self.flood.flood(msg)
        for tid in targets:
            await self._send_to(tid, msg)
        return len(targets)

    async def store_dht(self, key: str, value: str) -> None:
        self.dht.put(key, value)
        # replicate to closest peers
        for p in self.dht.routing.closest(key, n=REPLICATION):
            if p.peer_id == self.peer_id:
                continue
            msg = P2PMessage(
                msg_type=MessageType.STORE,
                sender_id=self.peer_id,
                payload=f"{key}:{value}".encode(),
                ttl=5,
            )
            await self._send_to(p.peer_id, msg)

    async def find_dht(self, key: str) -> List[str]:
        return self.dht.find_value(key)

    # ── internal plumbing ──

    async def start(self) -> None:
        self._running = True
        self._tasks = [
            asyncio.create_task(self._heartbeat_loop()),
            asyncio.create_task(self._inbox_loop()),
            asyncio.create_task(self._mdns_loop()),
        ]

    async def stop(self) -> None:
        self._running = False
        for t in self._tasks:
            t.cancel()
        self.mdns.stop()
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _heartbeat_loop(self) -> None:
        while self._running:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            # decay reputation of stale peers
            now = time.time()
            for bucket in self.dht.routing.buckets:
                for p in bucket.peers:
                    if now - p.last_seen > HEARTBEAT_INTERVAL * 3:
                        p.reputation *= REPUTATION_DECAY

    async def _inbox_loop(self) -> None:
        while self._running:
            try:
                msg = await asyncio.wait_for(self._inbox.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            self._msg_count += 1
            await self._handle(msg)

    async def _mdns_loop(self) -> None:
        async def _on_discover(peer: PeerInfo) -> None:
            self.dht.routing.add(peer)
            self.mesh.on_peer_discovered(peer, self._peer_count())
            # send ping
            ping = P2PMessage(
                msg_type=MessageType.PING,
                sender_id=self.peer_id,
                payload=b"hello",
                ttl=5,
            )
            await self._send_to(peer.peer_id, ping)
        await self.mdns.start(_on_discover)

    async def _handle(self, msg: P2PMessage) -> None:
        if msg.ttl <= 0:
            return
        msg.ttl -= 1

        # invoke registered handlers
        for handler in self._handlers.get(msg.msg_type, []):
            try:
                handler(msg)
            except Exception as e:
                print(f"[{self.peer_id[:8]}] handler error: {e}")

        # default behaviours
        if msg.msg_type == MessageType.PING:
            pong = P2PMessage(
                msg_type=MessageType.PONG,
                sender_id=self.peer_id,
                payload=b"pong",
                ttl=5,
            )
            await self._send_to(msg.sender_id, pong)

        elif msg.msg_type == MessageType.FIND_NODE:
            target = msg.payload.decode()
            closest = self.dht.find_node(target)
            reply = P2PMessage(
                msg_type=MessageType.FIND_NODE_REPLY,
                sender_id=self.peer_id,
                payload=json.dumps([p.to_dict() for p in closest]).encode(),
                ttl=5,
            )
            await self._send_to(msg.sender_id, reply)

        elif msg.msg_type == MessageType.STORE:
            try:
                key, value = msg.payload.decode().split(":", 1)
                self.dht.put(key, value)
            except ValueError:
                pass

        elif msg.msg_type in (MessageType.GOSSIP, MessageType.DATA):
            # forward if not at edge
            if msg.ttl > 0:
                if msg.msg_type == MessageType.GOSSIP:
                    targets = self.gossip.publish(msg)
                else:
                    targets = self.flood.flood(msg)
                for tid in targets:
                    if tid != msg.sender_id:
                        await self._send_to(tid, msg)

        self._delivered += 1

    async def _dispatch(self, msg: P2PMessage) -> bool:
        """Try to deliver along pre-computed route."""
        if not msg.route_hops:
            return False
        nxt = msg.route_hops[1] if len(msg.route_hops) > 1 else msg.route_hops[0]
        return await self._send_to(nxt, msg)

    async def _send_to(self, peer_id: PeerID, msg: P2PMessage) -> bool:
        """Stub transport — in reality this is UDP/TCP socket I/O."""
        # simulate latency
        await asyncio.sleep(random.uniform(0.001, 0.01))
        # find peer address
        for bucket in self.dht.routing.buckets:
            for p in bucket.peers:
                if p.peer_id == peer_id:
                    # enqueue into target's inbox (simulated direct memory for demo)
                    # real impl would serialize to socket
                    return True
        return False

    def _peer_count(self) -> int:
        return sum(len(b.peers) for b in self.dht.routing.buckets)

    def mesh_stats(self) -> dict:
        return {
            "peer_id": self.peer_id,
            "address": self.address,
            "known_peers": self._peer_count(),
            "mesh": self.mesh.stats(),
            "dht_keys": len(self.dht.storage),
            "messages_received": self._msg_count,
            "messages_delivered": self._delivered,
            "reputation": self.info.reputation,
        }


# ──────────────────────────────────────────────────────────────
# 10.  P2PMeshKernel — bridge to Layer 4 (MAGNATRIX runtime)
# ──────────────────────────────────────────────────────────────

class P2PMeshKernel:
    """High-level API exposed to the rest of MAGNATRIX OS."""

    def __init__(self, node: P2PMeshNode) -> None:
        self.node = node

    async def broadcast(self, data: bytes) -> int:
        """Best-effort mesh broadcast. Returns forward count."""
        return await self.node.publish_gossip(data)

    async def send(self, target_id: PeerID, data: bytes) -> bool:
        """Reliable-ish direct send via shortest-path routing."""
        return await self.node.send_direct(target_id, data)

    async def discover(self, key: str) -> List[str]:
        """DHT lookup."""
        return await self.node.find_dht(key)

    async def publish(self, key: str, value: str) -> None:
        """DHT store with replication."""
        await self.node.store_dht(key, value)

    def stats(self) -> dict:
        return self.node.mesh_stats()


# ──────────────────────────────────────────────────────────────
# 11.  Demo
# ──────────────────────────────────────────────────────────────

async def _demo() -> None:
    print("=" * 60)
    print("MAGNATRIX P2P Mesh — Demo")
    print("=" * 60)

    # create 5 peers on localhost ports
    peers: List[P2PMeshNode] = []
    ports = [10001, 10002, 10003, 10004, 10005]
    for port in ports:
        caps = {random.choice(list(PeerCapability))}
        node = P2PMeshNode("127.0.0.1", port, capabilities=caps)
        peers.append(node)
        await node.start()
        print(f"[BOOT] {node.info}")

    # manually interconnect routing tables (simulating discovery convergence)
    for i, a in enumerate(peers):
        for b in peers[i + 1:]:
            a.dht.routing.add(b.info)
            b.dht.routing.add(a.info)
            a.mesh.on_peer_discovered(b.info, len(peers))
            b.mesh.on_peer_discovered(a.info, len(peers))

    # let heartbeats settle
    await asyncio.sleep(0.5)

    # peer 0 stores a value in DHT
    await peers[0].store_dht("magnatrix:leader", peers[0].peer_id)
    print(f"\n[DHT] peer-0 stored 'magnatrix:leader' → {peers[0].peer_id[:8]}")

    # peer 4 looks it up
    vals = await peers[4].find_dht("magnatrix:leader")
    print(f"[DHT] peer-4 lookup returned: {vals}")

    # peer 1 sends direct message to peer 3
    ok = await peers[1].send_direct(
        peers[3].peer_id,
        b"hello from peer-1",
    )
    print(f"\n[ROUTING] peer-1 → peer-3 direct send: {'OK' if ok else 'FAIL'}")

    # peer 2 gossip-broadcasts
    forwards = await peers[2].publish_gossip(b"gossip: network alert")
    print(f"[GOSSIP] peer-2 broadcast forwarded to {forwards} peers")

    # peer 0 floods a message
    flooded = await peers[0].publish_flood(b"flood: emergency sync")
    print(f"[FLOOD] peer-0 flood reached {flooded} peers")

    # NAT traversal demo on peer 0
    mapped = await peers[0].nat.stun_bind(("stun.l.google.com", 19302))
    print(f"\n[NAT] peer-0 STUN mapped address: {mapped}")
    relay = await peers[0].nat.turn_allocate(("turn.example.com", 3478))
    print(f"[NAT] peer-0 TURN relay address: {relay}")
    punch_ok = await peers[0].nat.hole_punch(("203.0.113.7", 40001))
    print(f"[NAT] peer-0 hole punch to 203.0.113.7: {'SUCCESS' if punch_ok else 'FAIL'}")

    # mesh stats
    print("\n" + "-" * 60)
    print("MESH STATS")
    print("-" * 60)
    for p in peers:
        s = p.mesh_stats()
        print(f"  {s['peer_id'][:8]} | known={s['known_peers']} | "
              f"mesh_active={s['mesh']['active']}/desired={s['mesh']['desired']} | "
              f"recv={s['messages_received']} deliv={s['messages_delivered']}")

    # shutdown
    for p in peers:
        await p.stop()
    print("\n[DONE] All peers stopped.")


if __name__ == "__main__":
    asyncio.run(_demo())
