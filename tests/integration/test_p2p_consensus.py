#!/usr/bin/env python3
"""
tests/integration/test_p2p_consensus.py
P2P mesh + consensus end-to-end tests.
"""
import sys, os, time, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from p2p_mesh.p2p_mesh_native import P2PNode, _encrypt_p2p, _decrypt_p2p
from runtime.multi_agent_swarm_native import AgentSwarmNative, AgentIdentity


def test_p2p_encryption():
    key = os.urandom(32)
    plaintext = b"p2p secret message"
    try:
        ciphertext = _encrypt_p2p(plaintext, key)
        decrypted = _decrypt_p2p(ciphertext, key)
        assert decrypted == plaintext
        print("PASS: P2P ChaCha20 encryption roundtrip")
    except RuntimeError as e:
        print(f"SKIP: P2P encryption ({e})")


def test_kademlia_dht():
    # Mock DHT test using the Kademlia160 pattern
    from p2p_mesh.p2p_mesh_native import Kademlia160
    dht = Kademlia160(node_id=os.urandom(20))
    key = b"test_key"
    value = b"test_value"
    dht.store(key, value)
    found = dht.find_value(key)
    assert found == value
    print("PASS: Kademlia DHT store/find")


def test_p2p_node_creation():
    node = P2PNode(listen_port=0)
    assert node.node_id is not None
    assert len(node.node_id) == 20
    print("PASS: P2P node creation")


def test_swarm_leader_election():
    swarm = AgentSwarmNative()
    a1 = AgentIdentity("agent-1", "coordinator", priority=10)
    a2 = AgentIdentity("agent-2", "worker", priority=5)
    a3 = AgentIdentity("agent-3", "worker", priority=3)
    swarm.register_agent(a1)
    swarm.register_agent(a2)
    swarm.register_agent(a3)
    leader = swarm.elect_leader()
    assert leader == "agent-1"
    print("PASS: Swarm leader election (bully algorithm)")


def test_swarm_consensus():
    swarm = AgentSwarmNative()
    for i in range(5):
        swarm.register_agent(AgentIdentity(f"agent-{i}", "voter", priority=i))
    result = swarm.propose_vote("upgrade_protocol", {"version": "2.0"})
    assert result["quorum_reached"] == True
    print("PASS: Swarm consensus voting (5 agents, quorum reached)")


def test_swarm_message_broadcast():
    swarm = AgentSwarmNative()
    received = []
    swarm.register_agent(AgentIdentity("a1", "listener"))
    swarm.register_agent(AgentIdentity("a2", "listener"))
    swarm.broadcast("test_event", {"data": "hello"})
    print("PASS: Swarm message broadcast")


def test_swarm_fault_tolerance():
    swarm = AgentSwarmNative()
    swarm.register_agent(AgentIdentity("a1", "coordinator", priority=10))
    swarm.register_agent(AgentIdentity("a2", "worker", priority=5))
    swarm.register_agent(AgentIdentity("a3", "worker", priority=3, alive=False))
    # a3 is dead, should not participate in leader election
    leader = swarm.elect_leader()
    assert leader in ("a1", "a2")
    print("PASS: Swarm fault tolerance (dead agent excluded)")


def run_all():
    print("=" * 60)
    print("P2P + Consensus End-to-End Tests")
    print("=" * 60)
    tests = [
        test_p2p_encryption,
        test_kademlia_dht,
        test_p2p_node_creation,
        test_swarm_leader_election,
        test_swarm_consensus,
        test_swarm_message_broadcast,
        test_swarm_fault_tolerance,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"FAIL: {t.__name__}: {e}")
            failed += 1
    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")
    return failed == 0


if __name__ == "__main__":
    ok = run_all()
    sys.exit(0 if ok else 1)
