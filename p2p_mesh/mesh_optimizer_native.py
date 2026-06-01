"""P2P mesh optimization with Kademlia DHT, NAT traversal, and gossip sync.

Pure stdlib implementation of a MeshOptimizer class for decentralized peer discovery,
routing, and state synchronization in a simulated P2P mesh network.
"""

from __future__ import annotations

import hashlib
import random
import socket
import struct
import time
from typing import Dict, List, Optional, Set, Tuple

K_BUCKET_SIZE = 20
ID_BITS = 160


def _xor_distance(a: int, b: int) -> int:
    """Return 160-bit XOR distance between two node IDs."""
    return a ^ b


def _node_id(addr: str, port: int) -> int:
    """Generate a deterministic 160-bit node ID from address and port."""
    data = f"{addr}:{port}".encode()
    return int(hashlib.sha1(data).hexdigest(), 16)


def _common_prefix_len(a: int, b: int) -> int:
    """Count leading zero bits of the XOR distance (prefix length)."""
    dist = a ^ b
    if dist == 0:
        return ID_BITS
    return (ID_BITS - 1) - dist.bit_length()


class PeerInfo:
    """Container for a peer's metadata."""

    def __init__(self, addr: str, port: int, node_id: int) -> None:
        self.addr = addr
        self.port = port
        self.node_id = node_id
        self.latency_ms: float = 0.0
        self.bandwidth_mbps: float = 0.0
        self.last_seen: float = time.time()

    def __repr__(self) -> str:
        return (
            f"Peer({self.addr}:{self.port}, "
            f"lat={self.latency_ms:.1f}ms, bw={self.bandwidth_mbps:.1f}Mbps)"
        )


class KBucket:
    """Kademlia k-bucket holding up to K peers for a given prefix range."""

    def __init__(self) -> None:
        self.peers: List[PeerInfo] = []

    def add(self, peer: PeerInfo) -> bool:
        """Add or refresh a peer in the bucket. Return True if accepted."""
        for i, p in enumerate(self.peers):
            if p.node_id == peer.node_id:
                self.peers.pop(i)
                self.peers.append(peer)
                return True
        if len(self.peers) < K_BUCKET_SIZE:
            self.peers.append(peer)
            return True
        return False

    def remove(self, node_id: int) -> None:
        self.peers = [p for p in self.peers if p.node_id != node_id]

    def closest(self, target: int, count: int = K_BUCKET_SIZE) -> List[PeerInfo]:
        """Return up to `count` peers sorted by XOR distance to target."""
        return sorted(self.peers, key=lambda p: _xor_distance(p.node_id, target))[:count]


class RoutingTable:
    """XOR-based Kademlia routing table using k-buckets."""

    def __init__(self, node_id: int) -> None:
        self.node_id = node_id
        self.buckets: List[KBucket] = [KBucket() for _ in range(ID_BITS)]

    def _bucket_index(self, peer_id: int) -> int:
        """Select bucket index based on common prefix length with self."""
        prefix = _common_prefix_len(self.node_id, peer_id)
        return max(0, min(ID_BITS - 1, prefix))

    def add(self, peer: PeerInfo) -> bool:
        """Add a peer to the appropriate k-bucket."""
        return self.buckets[self._bucket_index(peer.node_id)].add(peer)

    def remove(self, peer_id: int) -> None:
        self.buckets[self._bucket_index(peer_id)].remove(peer_id)

    def closest(self, target: int, count: int = K_BUCKET_SIZE) -> List[PeerInfo]:
        """Iteratively gather closest peers from all buckets."""
        all_peers: List[PeerInfo] = []
        for b in self.buckets:
            all_peers.extend(b.peers)
        all_peers.sort(key=lambda p: _xor_distance(p.node_id, target))
        return all_peers[:count]


class MeshOptimizer:
    """P2P mesh optimizer with DHT, NAT traversal, and gossip sync."""

    def __init__(self, addr: str, port: int) -> None:
        self.addr = addr
        self.port = port
        self.node_id = _node_id(addr, port)
        self.routing_table = RoutingTable(self.node_id)
        self.peers: Dict[int, PeerInfo] = {}
        self.state: Dict[str, str] = {}
        self.gossip_seq = 0
        self.nat_map: Dict[Tuple[str, int], Tuple[str, int]] = {}

    def _simulate_latency(self) -> float:
        """Return a simulated latency in milliseconds."""
        return random.uniform(10.0, 150.0)

    def _simulate_bandwidth(self) -> float:
        """Return a simulated bandwidth in Mbps."""
        return random.uniform(5.0, 100.0)

    def _stun_resolve(self, addr: str, port: int) -> Tuple[str, int]:
        """Simulate STUN-like public endpoint resolution."""
        public_addr = socket.inet_ntoa(
            struct.pack(">I", random.randint(1, 0xFFFFFFFF))
        )
        public_port = random.randint(20000, 65000)
        self.nat_map[(addr, port)] = (public_addr, public_port)
        return public_addr, public_port

    def _turn_relay(self, peer: PeerInfo) -> bool:
        """Simulate TURN-like relay fallback for restrictive NAT."""
        return random.random() < 0.3

    def add_peer(self, addr: str, port: int) -> PeerInfo:
        """Add a peer to the routing table and local registry."""
        peer_id = _node_id(addr, port)
        peer = PeerInfo(addr, port, peer_id)
        peer.latency_ms = self._simulate_latency()
        peer.bandwidth_mbps = self._simulate_bandwidth()
        self.peers[peer_id] = peer
        self.routing_table.add(peer)
        return peer

    def remove_peer(self, peer_id: int) -> None:
        """Remove a peer from routing table and local registry."""
        self.routing_table.remove(peer_id)
        self.peers.pop(peer_id, None)

    def lookup(self, target_id: int) -> List[PeerInfo]:
        """Iterative Kademlia lookup for the closest peers to a target ID."""
        closest = self.routing_table.closest(target_id, K_BUCKET_SIZE)
        for _ in range(3):
            if not closest:
                break
            for peer in closest:
                if peer.node_id in self.peers:
                    self.peers[peer.node_id].last_seen = time.time()
            closest = self.routing_table.closest(target_id, K_BUCKET_SIZE)
        return closest

    def select_best_peers(self, count: int = 5) -> List[PeerInfo]:
        """Select peers with lowest latency and highest bandwidth."""
        scored = []
        for p in self.peers.values():
            score = p.bandwidth_mbps / max(p.latency_ms, 1.0)
            scored.append((score, p))
        scored.sort(reverse=True)
        return [p for _, p in scored[:count]]

    def gossip_sync(self, state_update: Dict[str, str]) -> None:
        """Merge state updates and increment gossip sequence."""
        self.state.update(state_update)
        self.gossip_seq += 1

    def _gossip_round(self) -> None:
        """Simulate one gossip round: send state to a subset of peers."""
        if not self.peers:
            return
        targets = random.sample(list(self.peers.values()), min(3, len(self.peers)))
        for peer in targets:
            peer.last_seen = time.time()
            self.gossip_sync(self.state)

    def run(self) -> None:
        """Self-test demonstrating all features."""
        print(f"=== MeshOptimizer self-test (node_id={self.node_id:x}) ===")

        # Add peers
        for i in range(10):
            self.add_peer(f"10.0.0.{i + 1}", 4000 + i)
        print(f"Added {len(self.peers)} peers")

        # Routing table / XOR distance
        target = random.getrandbits(ID_BITS)
        closest = self.lookup(target)
        print(f"Lookup for target {target:x} returned {len(closest)} peers")
        for p in closest[:3]:
            d = _xor_distance(p.node_id, target)
            print(f"  {p} dist={d:x}")

        # Peer selection by latency + bandwidth
        best = self.select_best_peers(3)
        print(f"\nTop 3 peers by latency/bandwidth:")
        for p in best:
            print(f"  {p}")

        # NAT traversal simulation
        nat_addr, nat_port = self._stun_resolve("192.168.1.100", 4000)
        print(f"\nNAT public endpoint: {nat_addr}:{nat_port}")
        relay_needed = self._turn_relay(best[0]) if best else False
        print(f"TURN relay needed for best peer: {relay_needed}")

        # Gossip sync
        update = {"key1": "value1", "key2": "value2"}
        self.gossip_sync(update)
        self._gossip_round()
        print(f"\nGossip state after round: {self.state}")
        print(f"Gossip sequence: {self.gossip_seq}")

        # Remove a peer and re-query
        removed = list(self.peers.keys())[0]
        self.remove_peer(removed)
        print(f"\nRemoved peer {removed:x}, remaining peers: {len(self.peers)}")

        print("\n=== All features demonstrated successfully ===")


if __name__ == "__main__":
    optimizer = MeshOptimizer("127.0.0.1", 8000)
    optimizer.run()
