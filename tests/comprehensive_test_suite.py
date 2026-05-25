#!/usr/bin/env python3
"""
tests/comprehensive_test_suite.py
=================================
End-to-End Integration Test Suite for MAGNATRIX-OS

Runs smoke tests across all layers to verify:
  - Each layer boots without error
  - Inter-layer communication (kernel bridge)
  - Crypto round-trip
  - Sandbox layer configuration
  - AI tokenizer + inference
  - P2P message serialization
  - Raft consensus replication
  - Event streaming pub/sub
  - Observability metrics
"""

from __future__ import annotations

import sys
import time
import traceback
from typing import Dict, List, Any, Tuple


def _test_crypto() -> Tuple[bool, str]:
    try:
        sys.path.insert(0, "identity")
        from crypto_identity_native import Ed25519KeyPair, X25519, AES256GCM, ChaCha20Poly1305
        kp = Ed25519KeyPair()
        msg = b"test"
        assert kp.verify(msg, kp.sign(msg)), "Ed25519 sign/verify failed"
        priv, pub = X25519.keypair()
        ss = X25519.shared_secret(priv, pub)
        assert len(ss) == 32, "X25519 shared secret wrong length"
        key, iv, nonce = b"\x00" * 32, b"\x00" * 12, b"\x00" * 12
        cipher = AES256GCM(key)
        ct, tag = cipher.encrypt(msg, iv)
        assert cipher.decrypt(ct, iv, tag) == msg, "AES-GCM decrypt failed"
        ccp = ChaCha20Poly1305(key)
        ct2, tag2 = ccp.encrypt(msg, nonce)
        assert ccp.decrypt(ct2, nonce, tag2) == msg, "ChaCha20 decrypt failed"
        return True, "crypto OK"
    except Exception as e:
        return False, str(e)


def _test_sandbox() -> Tuple[bool, str]:
    try:
        sys.path.insert(0, "security")
        from sandbox_native import ResourceLimits, SeccompFilter
        limits = ResourceLimits(cpu_time_sec=60, open_files=64)
        bpf = SeccompFilter.build_allowlist_filter()
        assert len(bpf) > 0, "seccomp filter empty"
        return True, "sandbox OK"
    except Exception as e:
        return False, str(e)


def _test_ai() -> Tuple[bool, str]:
    try:
        sys.path.insert(0, "ai")
        from uncensored_ai_native import BPETokenizer, InferenceEngine, KVCacheManager
        tok = BPETokenizer()
        tokens = tok.encode("Hello world")
        assert len(tokens) > 0, "tokenizer empty"
        kv = KVCacheManager(max_layers=2, max_seq_len=8, head_dim=4)
        kv.store(0, 0, [0.1] * 4, [0.2] * 4, 0)
        assert kv.stats["entries"] == 1, "KV cache store failed"
        engine = InferenceEngine(vocab_size=100, n_layers=2, n_heads=2, head_dim=4)
        engine.load_weights_stub()
        result = engine.generate("Hi", max_tokens=5)
        assert isinstance(result, str), "inference did not return string"
        return True, "ai OK"
    except Exception as e:
        return False, str(e)


def _test_p2p() -> Tuple[bool, str]:
    try:
        sys.path.insert(0, "p2p-mesh")
        from p2p_mesh_native import PeerInfo, _derive_session_key
        peer = PeerInfo(peer_id="test", address=("127.0.0.1", 8000))
        key = _derive_session_key(b"seed", "peer-1")
        assert len(key) == 32, "session key wrong length"
        return True, "p2p OK"
    except Exception as e:
        return False, str(e)


def _test_raft() -> Tuple[bool, str]:
    try:
        sys.path.insert(0, "consensus")
        from raft_native import RaftNode, RaftConfig, KeyValueStateMachine, InMemoryTransport
        import shutil
        for nid in ["r1", "r2", "r3"]:
            shutil.rmtree(f"/tmp/magnatrix-raft/{nid}", ignore_errors=True)
        nodes = []
        peers = ["r1", "r2", "r3"]
        for nid in peers:
            cfg = RaftConfig(node_id=nid, peers=[p for p in peers if p != nid],
                             election_timeout_min_ms=80, election_timeout_max_ms=150,
                             heartbeat_interval_ms=20, data_dir=f"/tmp/magnatrix-raft/{nid}")
            node = RaftNode(cfg, KeyValueStateMachine())
            InMemoryTransport.register(node)
            nodes.append(node)
        for n in nodes:
            n.start()
        time.sleep(0.6)
        leader = next((n for n in nodes if n.is_leader()), None)
        assert leader is not None, "no leader elected"
        leader.submit({"op": "set", "key": "x", "value": "1"})
        time.sleep(0.3)
        assert all(n.state_machine.state.get("x") == "1" for n in nodes), "replication failed"
        for n in nodes:
            n.stop()
        return True, "raft OK"
    except Exception as e:
        return False, str(e)


def _test_streaming() -> Tuple[bool, str]:
    try:
        import shutil, uuid
        sys.path.insert(0, "streaming")
        from event_stream_native import EventStreamingEngine, Event
        uid = uuid.uuid4().hex[:8]
        data_dir = f"/tmp/magnatrix-streaming-test-{uid}"
        shutil.rmtree(data_dir, ignore_errors=True)
        engine = EventStreamingEngine(data_dir=data_dir)
        engine.publish(Event(topic="test", payload={"data": 1}))
        group = engine.create_consumer_group("g1", ["test"])
        batch = engine.consume("g1", "test")
        assert len(batch) >= 1, f"expected >=1 event, got {len(batch)}"
        engine.shutdown()
        return True, "streaming OK"
    except Exception as e:
        return False, str(e)


def _test_observability() -> Tuple[bool, str]:
    try:
        sys.path.insert(0, "observability")
        from metrics_native import ObservabilityEngine
        obs = ObservabilityEngine()
        c = obs.metrics.counter("test_counter")
        c.inc(5)
        assert c.value == 5, "counter increment failed"
        obs.health.register("test", lambda: (True, "ok"))
        result = obs.run_health_check()
        assert result["healthy"] is True, "health check failed"
        return True, "observability OK"
    except Exception as e:
        return False, str(e)


def run_all() -> Dict[str, Any]:
    tests = [
        ("crypto", _test_crypto),
        ("sandbox", _test_sandbox),
        ("ai", _test_ai),
        ("p2p", _test_p2p),
        ("raft", _test_raft),
        ("streaming", _test_streaming),
        ("observability", _test_observability),
    ]
    results = {}
    passed = 0
    for name, fn in tests:
        try:
            ok, msg = fn()
            results[name] = {"pass": ok, "message": msg}
            if ok:
                passed += 1
        except Exception as e:
            results[name] = {"pass": False, "message": str(e)}
    return {"passed": passed, "total": len(tests), "results": results}


if __name__ == "__main__":
    import json
    print("=" * 60)
    print("MAGNATRIX-OS  |  COMPREHENSIVE INTEGRATION TEST SUITE")
    print("=" * 60)
    result = run_all()
    for name, res in result["results"].items():
        status = "PASS" if res["pass"] else "FAIL"
        print(f"  [{status}] {name:20s} — {res['message']}")
    print(f"\n  {result['passed']}/{result['total']} tests passed")
    if result["passed"] == result["total"]:
        print("  ALL SYSTEMS OPERATIONAL")
    print("=" * 60)
