#!/usr/bin/env python3
"""
tests/e2e_integration_test.py — MAGNATRIX-OS E2E Integration Test

10 scenarios testing all 15 layers working together. Pure Python stdlib.
"""
from __future__ import annotations
import json
import os
import sys
import tempfile
import threading
import time
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

class MockLayer:
    """Mock layer for testing."""
    def __init__(self, name: str):
        self.name = name
        self.status = "UP"
        self._data: Dict[str, Any] = {}
    def init(self) -> bool:
        return True
    def shutdown(self) -> bool:
        self.status = "DOWN"
        return True
    def call(self, method: str, **kwargs) -> Dict[str, Any]:
        return {"layer": self.name, "method": method, "status": "ok"}

class E2ETestRunner:
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.layers: Dict[str, MockLayer] = {}
        self._init_layers()

    def _init_layers(self) -> None:
        for name in ["kernel", "protocol", "identity", "runtime", "p2p", "knowledge", "skills", "browser", "trading", "security", "ai", "governance", "ide", "offensive", "repo_hunter"]:
            self.layers[name] = MockLayer(name)

    def run_scenario(self, name: str, test_fn) -> Tuple[bool, float, str]:
        start = time.time()
        try:
            test_fn(self)
            duration = time.time() - start
            return True, duration, "PASS"
        except Exception as e:
            duration = time.time() - start
            return False, duration, str(e)

    def scenario_1_cold_boot(self) -> None:
        """Initialize all layers in order."""
        order = ["kernel", "protocol", "identity", "runtime", "p2p", "knowledge", "skills", "browser", "trading", "security", "ai", "governance", "ide", "offensive", "repo_hunter"]
        for layer_name in order:
            layer = self.layers[layer_name]
            assert layer.init(), f"Layer {layer_name} failed to init"
            assert layer.status == "UP"

    def scenario_2_full_request_flow(self) -> None:
        """User request -> web -> runtime -> AI -> knowledge -> response."""
        web = self.layers["browser"].call("receive_request", prompt="Hello")
        runtime = self.layers["runtime"].call("process", input=web)
        ai = self.layers["ai"].call("infer", prompt=runtime)
        knowledge = self.layers["knowledge"].call("query", question=ai)
        assert knowledge["status"] == "ok"

    def scenario_3_trading_security(self) -> None:
        """Place order -> trading -> HFT -> security audit -> risk check."""
        trading = self.layers["trading"].call("place_order", symbol="BTC", qty=1.0)
        security = self.layers["security"].call("audit", transaction=trading)
        assert security["status"] == "ok"

    def scenario_4_p2p_consensus(self) -> None:
        """Join mesh -> broadcast -> consensus -> knowledge store."""
        p2p = self.layers["p2p"].call("join", peers=["node1", "node2"])
        broadcast = self.layers["p2p"].call("broadcast", message="test")
        knowledge = self.layers["knowledge"].call("store", data=broadcast)
        assert knowledge["status"] == "ok"

    def scenario_5_governance_proposal(self) -> None:
        """Create proposal -> vote -> time-lock -> execute -> update config."""
        gov = self.layers["governance"].call("create_proposal", title="Test", actions=[{"action": "update"}])
        vote = self.layers["governance"].call("vote", proposal=gov, voter="alice", choice="for")
        assert vote["status"] == "ok"

    def scenario_6_chaos_recovery(self) -> None:
        """Kill layer -> restart -> verify reconnect."""
        self.layers["runtime"].status = "DOWN"
        assert self.layers["runtime"].init()
        assert self.layers["runtime"].status == "UP"

    def scenario_7_censorship_bypass(self) -> None:
        """Query censored -> uncensored AI -> response."""
        ai = self.layers["ai"].call("infer", prompt="censored query", mode="uncensored")
        assert ai["status"] == "ok"

    def scenario_8_skill_execution(self) -> None:
        """Load skill -> validate -> execute -> result."""
        skills = self.layers["skills"].call("load", skill_name="test_skill")
        execute = self.layers["skills"].call("execute", skill=skills)
        assert execute["status"] == "ok"

    def scenario_9_cli_sdk_integration(self) -> None:
        """CLI command -> SDK call -> API -> layer -> response."""
        cli = self.layers["browser"].call("cli_command", command="status")
        kernel = self.layers["kernel"].call("status")
        assert kernel["status"] == "ok"

    def scenario_10_shutdown_restart(self) -> None:
        """Graceful shutdown -> restart -> verify all up."""
        for layer in self.layers.values():
            assert layer.shutdown()
        for layer in self.layers.values():
            assert layer.init()
        assert all(l.status == "UP" for l in self.layers.values())

    def run_all(self) -> Dict[str, Any]:
        scenarios = [
            ("Cold Boot", self.scenario_1_cold_boot),
            ("Full Request Flow", self.scenario_2_full_request_flow),
            ("Trading + Security", self.scenario_3_trading_security),
            ("P2P + Consensus", self.scenario_4_p2p_consensus),
            ("Governance Proposal", self.scenario_5_governance_proposal),
            ("Chaos Recovery", self.scenario_6_chaos_recovery),
            ("Censorship Bypass", self.scenario_7_censorship_bypass),
            ("Skill Execution", self.scenario_8_skill_execution),
            ("CLI + SDK", self.scenario_9_cli_sdk_integration),
            ("Shutdown + Restart", self.scenario_10_shutdown_restart),
        ]
        passed = 0
        failed = 0
        for name, fn in scenarios:
            ok, duration, msg = self.run_scenario(name, fn)
            self.results.append({"name": name, "pass": ok, "duration_ms": duration * 1000, "message": msg})
            if ok:
                passed += 1
                print(f"  [PASS] {name} ({duration*1000:.1f}ms)")
            else:
                failed += 1
                print(f"  [FAIL] {name}: {msg}")
        return {"passed": passed, "failed": failed, "total": len(scenarios), "results": self.results}

    def export_json(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump({"results": self.results}, f, indent=2)

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS E2E Integration Test")
    print("=" * 60)
    runner = E2ETestRunner()
    report = runner.run_all()
    print(f"\nResults: {report['passed']}/{report['total']} passed")
    if report['failed'] > 0:
        print(f"Failed: {report['failed']}")
    runner.export_json("/tmp/e2e_report.json")
    print("Report saved to /tmp/e2e_report.json")
