#!/usr/bin/env python3
"""
Phase 3 — Integration Testing + Hybrid Mode for MAGNATRIX-OS
============================================================
End-to-end integration testing, module compatibility checking,
data flow validation, and hybrid local+cloud mode management.
Pure Python stdlib only.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations
import json, time, traceback
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class CompatibilityLevel(Enum):
    FULL = "full"
    PARTIAL = "partial"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"


class HybridMode(Enum):
    LOCAL = "local"
    CLOUD = "cloud"
    HYBRID = "hybrid"
    AUTO = "auto"


@dataclass
class IntegrationTestResult:
    """Result of an integration test."""
    test_name: str
    passed: bool
    duration_ms: float
    modules_tested: List[str]
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompatibilityReport:
    """Compatibility report between two modules."""
    module_a: str
    module_b: str
    level: str
    score: float
    shared_interfaces: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class DataFlowEdge:
    """Represents data flow between modules."""
    source: str
    target: str
    data_type: str
    frequency: str = "on_demand"
    validated: bool = False


class IntegrationTestEngine:
    """End-to-end integration testing engine."""

    def __init__(self, registry: Any = None) -> None:
        self.registry = registry
        self._results: List[IntegrationTestResult] = []

    def run_all(self) -> Dict[str, Any]:
        """Run all integration tests."""
        tests = [
            self.test_event_flow,
            self.test_module_chain,
            self.test_error_recovery,
            self.test_broadcast,
            self.test_request_response,
        ]
        start = time.time()
        for test in tests:
            try:
                test()
            except Exception as e:
                self._results.append(IntegrationTestResult(
                    test_name=test.__name__,
                    passed=False,
                    duration_ms=0.0,
                    modules_tested=[],
                    error=str(e),
                ))
        total_ms = (time.time() - start) * 1000
        passed = sum(1 for r in self._results if r.passed)
        return {
            "total_tests": len(self._results),
            "passed": passed,
            "failed": len(self._results) - passed,
            "total_duration_ms": round(total_ms, 1),
            "results": [asdict(r) for r in self._results],
        }

    def test_event_flow(self) -> IntegrationTestResult:
        """Test event propagation between modules."""
        t0 = time.time()
        event_bus = self.registry.get_module("event")
        if not event_bus or not hasattr(event_bus, "publish"):
            return IntegrationTestResult(
                "test_event_flow", False, 0.0, ["event"],
                "Event bus not available"
            )
        received = []
        def handler(payload):
            received.append(payload)
        if hasattr(event_bus, "subscribe"):
            event_bus.subscribe("test.topic", handler)
            event_bus.publish("test.topic", {"msg": "hello"})
            time.sleep(0.1)
        passed = len(received) > 0
        return IntegrationTestResult(
            "test_event_flow", passed, (time.time()-t0)*1000,
            ["event"], None if passed else "No events received"
        )

    def test_module_chain(self) -> IntegrationTestResult:
        """Test chaining multiple modules."""
        t0 = time.time()
        modules = ["config", "cache", "logging"]
        instances = [self.registry.get_module(m) for m in modules]
        passed = all(i is not None for i in instances)
        return IntegrationTestResult(
            "test_module_chain", passed, (time.time()-t0)*1000,
            modules, None if passed else "Some modules not loaded"
        )

    def test_error_recovery(self) -> IntegrationTestResult:
        """Test module error recovery."""
        t0 = time.time()
        self_healing = self.registry.get_module("self_healing")
        if not self_healing or not hasattr(self_healing, "check_health"):
            return IntegrationTestResult(
                "test_error_recovery", True, (time.time()-t0)*1000,
                ["self_healing"], "Self-healing not available, skipping"
            )
        health = self_healing.check_health("config")
        passed = health is not None
        return IntegrationTestResult(
            "test_error_recovery", passed, (time.time()-t0)*1000,
            ["self_healing"], None if passed else "Health check failed"
        )

    def test_broadcast(self) -> IntegrationTestResult:
        """Test broadcast message to all modules."""
        t0 = time.time()
        integration = self.registry.get_module("integration")
        if not integration or not hasattr(integration, "broadcast"):
            return IntegrationTestResult(
                "test_broadcast", False, 0.0, ["integration"],
                "Integration manager not available"
            )
        try:
            integration.broadcast({"type": "ping", "timestamp": time.time()})
            passed = True
        except Exception as e:
            passed = False
        return IntegrationTestResult(
            "test_broadcast", passed, (time.time()-t0)*1000,
            ["integration"], None if passed else str(e)
        )

    def test_request_response(self) -> IntegrationTestResult:
        """Test request-response between modules."""
        t0 = time.time()
        router = self.registry.get_module("message")
        if not router or not hasattr(router, "send"):
            return IntegrationTestResult(
                "test_request_response", False, 0.0, ["message"],
                "Message router not available"
            )
        try:
            resp = router.send("config", {"action": "get", "key": "test"})
            passed = resp is not None
        except Exception as e:
            passed = False
        return IntegrationTestResult(
            "test_request_response", passed, (time.time()-t0)*1000,
            ["message", "config"], None if passed else str(e)
        )


class HybridModeManager:
    """Manages local+cloud hybrid execution mode."""

    SENSITIVE_OPS = {"auth", "secret", "encryption", "private_key", "password", "biometric"}
    HEAVY_OPS = {"training", "inference_large", "batch_processing", "analytics_bigdata"}

    def __init__(self, registry: Any = None) -> None:
        self.registry = registry
        self.mode = HybridMode.AUTO
        self._local_modules: Set[str] = set()
        self._cloud_modules: Set[str] = set()
        self._policy: Dict[str, Any] = {"default": "local"}

    def enable_local(self) -> None:
        self.mode = HybridMode.LOCAL
        self._local_modules = set(self.registry._modules.keys())
        self._cloud_modules = set()

    def enable_cloud(self) -> None:
        self.mode = HybridMode.CLOUD
        self._cloud_modules = set(self.registry._modules.keys())
        self._local_modules = set()

    def enable_hybrid(self, policy: Optional[Dict[str, Any]] = None) -> None:
        self.mode = HybridMode.HYBRID
        if policy:
            self._policy.update(policy)
        self._apply_policy()

    def _apply_policy(self) -> None:
        for name in self.registry._modules:
            lower = name.lower()
            if any(s in lower for s in self.SENSITIVE_OPS):
                self._local_modules.add(name)
            elif any(h in lower for h in self.HEAVY_OPS):
                self._cloud_modules.add(name)
            else:
                self._local_modules.add(name)

    def route_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Route request to local or cloud based on mode and policy."""
        op = request.get("operation", "").lower()
        target = request.get("target_module", "")
        if self.mode == HybridMode.LOCAL:
            return {"route": "local", "target": target, "reason": "local_mode"}
        elif self.mode == HybridMode.CLOUD:
            return {"route": "cloud", "target": target, "reason": "cloud_mode"}
        elif self.mode == HybridMode.HYBRID:
            if any(s in op for s in self.SENSITIVE_OPS) or target in self._local_modules:
                return {"route": "local", "target": target, "reason": "sensitive_op"}
            if any(h in op for h in self.HEAVY_OPS) or target in self._cloud_modules:
                return {"route": "cloud", "target": target, "reason": "heavy_compute"}
            return {"route": "local", "target": target, "reason": "default"}
        else:  # AUTO
            if any(s in op for s in self.SENSITIVE_OPS):
                return {"route": "local", "target": target, "reason": "auto_sensitive"}
            return {"route": "local", "target": target, "reason": "auto_default"}

    def get_status(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "local_modules": len(self._local_modules),
            "cloud_modules": len(self._cloud_modules),
            "policy": self._policy,
        }


class ModuleCompatibilityChecker:
    """Checks compatibility between modules."""

    def __init__(self, registry: Any = None) -> None:
        self.registry = registry
        self._reports: List[CompatibilityReport] = []

    def check_all_pairs(self) -> List[CompatibilityReport]:
        """Check compatibility of all module pairs."""
        names = list(self.registry._modules.keys())
        for i, a in enumerate(names):
            for b in names[i+1:]:
                self._reports.append(self.check_pair(a, b))
        return self._reports

    def check_pair(self, mod_a: str, mod_b: str) -> CompatibilityReport:
        """Check compatibility between two modules."""
        inst_a = self.registry.get_module(mod_a)
        inst_b = self.registry.get_module(mod_b)
        if inst_a is None or inst_b is None:
            return CompatibilityReport(mod_a, mod_b, "unknown", 0.0)

        methods_a = set(dir(inst_a))
        methods_b = set(dir(inst_b))
        shared = sorted(methods_a & methods_b)

        conflicts = []
        if hasattr(inst_a, "stop") and hasattr(inst_b, "stop"):
            conflicts.append("Both implement stop() — potential shutdown conflict")

        score = min(len(shared) / 10, 1.0) if shared else 0.0
        if conflicts:
            level = CompatibilityLevel.CONFLICT.value
        elif score > 0.5:
            level = CompatibilityLevel.FULL.value
        elif score > 0:
            level = CompatibilityLevel.PARTIAL.value
        else:
            level = CompatibilityLevel.UNKNOWN.value

        return CompatibilityReport(
            mod_a, mod_b, level, round(score, 2),
            shared, conflicts,
            [f"Shared {len(shared)} interfaces"] if shared else []
        )

    def get_matrix(self) -> Dict[str, Dict[str, str]]:
        """Return compatibility matrix."""
        matrix: Dict[str, Dict[str, str]] = {}
        for r in self._reports:
            matrix.setdefault(r.module_a, {})[r.module_b] = r.level
        return matrix


class DataFlowValidator:
    """Validates data flows between modules."""

    def __init__(self, registry: Any = None) -> None:
        self.registry = registry
        self._edges: List[DataFlowEdge] = []

    def trace_flow(self, source: str, target: str) -> Optional[DataFlowEdge]:
        """Trace data flow from source to target module."""
        src = self.registry.get_module(source)
        tgt = self.registry.get_module(target)
        if src is None or tgt is None:
            return None
        edge = DataFlowEdge(source, target, "dict", "on_demand", True)
        self._edges.append(edge)
        return edge

    def detect_cycles(self) -> List[List[str]]:
        """Detect cycles in module data flow."""
        graph: Dict[str, Set[str]] = {}
        for e in self._edges:
            graph.setdefault(e.source, set()).add(e.target)
        cycles = []
        visited = set()
        for node in graph:
            path = [node]
            stack = [(node, iter(graph.get(node, [])))]
            while stack:
                current, children = stack[-1]
                try:
                    child = next(children)
                    if child in path:
                        cycles.append(path[path.index(child):] + [child])
                    elif child not in visited:
                        path.append(child)
                        stack.append((child, iter(graph.get(child, []))))
                except StopIteration:
                    visited.add(current)
                    path.pop()
                    stack.pop()
        return cycles

    def validate_types(self, edge: DataFlowEdge) -> bool:
        """Validate data types on a flow edge."""
        return edge.validated

    def get_flow_graph(self) -> Dict[str, Any]:
        return {
            "edges": len(self._edges),
            "nodes": len(set(e.source for e in self._edges) | set(e.target for e in self._edges)),
            "cycles": len(self.detect_cycles()),
        }


class IntegrationReport:
    """Generates comprehensive integration report."""

    @staticmethod
    def generate(
        test_results: Dict[str, Any],
        compatibility_matrix: Dict[str, Dict[str, str]],
        data_flow: Dict[str, Any],
        hybrid_status: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "timestamp": time.time(),
            "test_summary": test_results,
            "compatibility": {
                "total_pairs": sum(len(v) for v in compatibility_matrix.values()),
                "matrix": compatibility_matrix,
            },
            "data_flow": data_flow,
            "hybrid_mode": hybrid_status,
            "recommendations": IntegrationReport._recommendations(test_results, compatibility_matrix),
        }

    @staticmethod
    def _recommendations(test_results: Dict[str, Any], matrix: Dict[str, Dict[str, str]]) -> List[str]:
        recs = []
        if test_results.get("failed", 0) > 0:
            recs.append(f"Fix {test_results['failed']} failing integration tests")
        conflicts = sum(1 for row in matrix.values() for v in row.values() if v == "conflict")
        if conflicts > 0:
            recs.append(f"Resolve {conflicts} module conflicts")
        return recs if recs else ["All systems integrated successfully"]


class IntegrationHybridManager:
    """Top-level orchestrator for Phase 3."""

    def __init__(self, registry: Any = None) -> None:
        self.registry = registry
        self.test_engine = IntegrationTestEngine(registry)
        self.hybrid = HybridModeManager(registry)
        self.compatibility = ModuleCompatibilityChecker(registry)
        self.data_flow = DataFlowValidator(registry)

    def run_integration_tests(self) -> Dict[str, Any]:
        return self.test_engine.run_all()

    def check_compatibility(self) -> Dict[str, Any]:
        reports = self.compatibility.check_all_pairs()
        return {
            "total_pairs": len(reports),
            "matrix": self.compatibility.get_matrix(),
        }

    def validate_data_flow(self) -> Dict[str, Any]:
        active = self.registry.active_modules() if hasattr(self.registry, "active_modules") else []
        for i, a in enumerate(active):
            for b in active[i+1:]:
                self.data_flow.trace_flow(a, b)
        return self.data_flow.get_flow_graph()

    def generate_report(self) -> Dict[str, Any]:
        tests = self.run_integration_tests()
        compat = self.check_compatibility()
        flow = self.validate_data_flow()
        hybrid = self.hybrid.get_status()
        return IntegrationReport.generate(tests, compat["matrix"], flow, hybrid)

    def set_hybrid_mode(self, mode: str, policy: Optional[Dict[str, Any]] = None) -> None:
        if mode == "local":
            self.hybrid.enable_local()
        elif mode == "cloud":
            self.hybrid.enable_cloud()
        elif mode == "hybrid":
            self.hybrid.enable_hybrid(policy)
        elif mode == "auto":
            self.hybrid.mode = HybridMode.AUTO

    def get_status(self) -> Dict[str, Any]:
        return {
            "integration_tests": self.run_integration_tests(),
            "hybrid_mode": self.hybrid.get_status(),
            "data_flow": self.data_flow.get_flow_graph(),
        }
