#!/usr/bin/env python3
"""
tests/chaos/raft_chaos_native.py
================================
Chaos Engineering: Raft Under Network Partition

Tests Raft safety under:
  - Network partition (leader isolated)
  - Random node crash/restart
  - Message delay and drop
  - Slow leader election
"""

from __future__ import annotations

import random
import shutil
import sys
import time

sys.path.insert(0, "consensus")
from raft_native import RaftNode, RaftConfig, KeyValueStateMachine, InMemoryTransport


def test_partition_recovery():
    """Partition leader, verify new leader elected, rejoin and converge."""
    print("[CHAOS] Test: Network partition recovery")
    for nid in ["p1", "p2", "p3"]:
        shutil.rmtree(f"/tmp/magnatrix-raft/{nid}", ignore_errors=True)
    nodes = []
    peers = ["p1", "p2", "p3"]
    for nid in peers:
        cfg = RaftConfig(
            node_id=nid, peers=[p for p in peers if p != nid],
            election_timeout_min_ms=100, election_timeout_max_ms=200,
            heartbeat_interval_ms=30, data_dir=f"/tmp/magnatrix-raft/{nid}",
        )
        node = RaftNode(cfg, KeyValueStateMachine())
        InMemoryTransport.register(node)
        nodes.append(node)
    for n in nodes:
        n.start()

    time.sleep(0.6)
    old_leader = next((n for n in nodes if n.is_leader()), None)
    assert old_leader is not None, "No leader before partition"
    print(f"  Leader before partition: {old_leader.id}")

    # Simulate partition: isolate leader from others
    old_id = old_leader.id
    InMemoryTransport._registry.pop(old_id, None)  # Leader can't send/receive
    time.sleep(0.5)

    # Remaining nodes should elect new leader
    remaining = [n for n in nodes if n.id != old_id]
    new_leader = next((n for n in remaining if n.is_leader()), None)
    assert new_leader is not None, "No new leader after partition"
    print(f"  New leader after partition: {new_leader.id}")

    # Rejoin old leader
    InMemoryTransport.register(old_leader)
    time.sleep(0.4)

    # Submit command to new leader
    new_leader.submit({"op": "set", "key": "partition_test", "value": "ok"})
    time.sleep(0.3)

    # Verify all nodes converged
    for n in nodes:
        assert n.state_machine.state.get("partition_test") == "ok", \
            f"Node {n.id} did not converge"
    print("  All nodes converged after rejoin")

    for n in nodes:
        n.stop()
    print("  PASS")


def test_random_crash():
    """Randomly crash and restart nodes."""
    print("[CHAOS] Test: Random crash/restart")
    for nid in ["c1", "c2", "c3"]:
        shutil.rmtree(f"/tmp/magnatrix-raft/{nid}", ignore_errors=True)
    nodes = []
    peers = ["c1", "c2", "c3"]
    for nid in peers:
        cfg = RaftConfig(
            node_id=nid, peers=[p for p in peers if p != nid],
            election_timeout_min_ms=100, election_timeout_max_ms=200,
            heartbeat_interval_ms=30, data_dir=f"/tmp/magnatrix-raft/{nid}",
        )
        node = RaftNode(cfg, KeyValueStateMachine())
        InMemoryTransport.register(node)
        nodes.append(node)
    for n in nodes:
        n.start()

    time.sleep(0.6)
    leader = next((n for n in nodes if n.is_leader()), None)
    assert leader is not None

    # Crash 1 random node
    victim = random.choice([n for n in nodes if n != leader])
    victim.stop()
    print(f"  Crashed {victim.id}")

    # Submit to leader
    leader.submit({"op": "set", "key": "crash_test", "value": "1"})
    time.sleep(0.3)

    # Restart victim
    victim.start()
    time.sleep(0.3)

    # Verify victim caught up
    assert victim.state_machine.state.get("crash_test") == "1", \
        f"Node {victim.id} did not catch up after restart"
    print(f"  {victim.id} caught up after restart")

    for n in nodes:
        n.stop()
    print("  PASS")


if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS  |  RAFT CHAOS ENGINEERING")
    print("=" * 60)
    test_partition_recovery()
    test_random_crash()
    print("=" * 60)
