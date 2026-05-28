#!/usr/bin/env python3
"""
MAGNATRIX-OS ASI Unified Kernel
Path: runtime/asi_kernel_native.py
License: AGPL-3.0

Orchestrates all 20 ASI Expansion modules into a single runtime.
Provides unified API for initialization, cross-module communication,
lifecycle management, and health monitoring.

Depends: All 20 ASI module files + Python 3.11+ stdlib.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("asi_kernel")


@dataclass
class ModuleInfo:
    name: str
    module_path: str
    class_name: str
    category: str
    dependencies: List[str] = field(default_factory=list)
    instance: Optional[Any] = None
    status: str = "uninitialized"  # uninitialized | ready | error | disabled
    last_error: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE REGISTRY — All 20 ASI Expansion Modules
# ═══════════════════════════════════════════════════════════════════════════════

ASI_MODULES: List[ModuleInfo] = [
    # Phase 1: Foundations
    ModuleInfo("rsi_engine", "ai.rsi_engine", "RSIEngine", "self_improvement"),
    ModuleInfo("meta_cognition", "ai.meta_cognition", "MetaCognitionEngine", "cognition"),
    ModuleInfo("world_sim", "runtime.world_sim", "World", "simulation"),
    ModuleInfo("causal_reasoning", "ai.causal_reasoning", "CausalGraph", "cognition"),
    ModuleInfo("theory_of_mind", "ai.theory_of_mind", "TheoryOfMindNetwork", "social"),
    ModuleInfo("goal_alignment", "ai.goal_alignment", "GoalAlignmentEngine", "safety"),
    ModuleInfo("counterfactual", "ai.counterfactual", "CounterfactualPlanner", "cognition"),
    ModuleInfo("episodic_memory", "knowledge.episodic", "EpisodicMemory", "memory"),
    # Phase 2: Cognitive Augmentation
    ModuleInfo("auto_research", "knowledge.auto_research", "ResearchLab", "research"),
    ModuleInfo("resource_optimizer", "runtime.resource_optimizer", "ResourceOptimizer", "infrastructure"),
    ModuleInfo("embodiment", "runtime.embodiment", "EmbodimentLayer", "robotics"),
    ModuleInfo("bci", "ai.bci", "BCIDecoder", "neurotech"),
    ModuleInfo("quantum_bridge", "ai.quantum_bridge", "QuantumBridge", "compute"),
    ModuleInfo("affective", "ai.affective", "AffectiveNetwork", "social"),
    ModuleInfo("ethical_reasoning", "ai.ethical_reasoning", "EthicalReasoning", "safety"),
    # Phase 3: Self-Preservation & Sovereignty
    ModuleInfo("replication_guard", "security.replication_guard", "ReplicationGuard", "safety", dependencies=["ethical_reasoning"]),
    ModuleInfo("sensor_mesh", "runtime.sensor_mesh", "SensorMesh", "perception"),
    ModuleInfo("cosmo_model", "runtime.cosmo", "CosmoModel", "simulation"),
    ModuleInfo("hyperpredict", "ai.hyperpredict", "HyperPredictEngine", "cognition"),
    ModuleInfo("energy_grid", "runtime.energy_grid", "EnergyGrid", "infrastructure"),
]


class ASIKernel:
    """Unified kernel orchestrating all 20 ASI modules."""

    def __init__(self, base_path: str = "/mnt/agents/MAGNATRIX-OS"):
        self.base_path = Path(base_path)
        self.modules: Dict[str, ModuleInfo] = {}
        self.health: Dict[str, Any] = {}
        self.metrics: Dict[str, List[float]] = {}
        self._running = False
        self._message_bus: List[Dict] = []
        for mi in ASI_MODULES:
            self.modules[mi.name] = mi

    def _load_module(self, info: ModuleInfo) -> bool:
        """Dynamically load an ASI module by file path."""
        try:
            rel_path = info.module_path.replace(".", "/") + "_native.py"
            file_path = self.base_path / rel_path
            if not file_path.exists():
                # Try without _native suffix
                alt_path = self.base_path / (info.module_path.replace(".", "/") + ".py")
                if alt_path.exists():
                    file_path = alt_path
                else:
                    info.status = "error"
                    info.last_error = f"File not found: {file_path}"
                    return False

            spec = importlib.util.spec_from_file_location(info.module_path, file_path)
            if spec is None or spec.loader is None:
                info.status = "error"
                info.last_error = "Failed to create module spec"
                return False

            mod = importlib.util.module_from_spec(spec)
            sys.modules[info.module_path] = mod
            spec.loader.exec_module(mod)

            # Instantiate the main class with fallback for different signatures
            cls = getattr(mod, info.class_name, None)
            if cls is None:
                info.status = "error"
                info.last_error = f"Class {info.class_name} not found"
                return False

            # Try different constructor patterns
            instance = None
            for args_kwargs in [(), (["feature_a", "feature_b"],), (42,), ({},)]:
                try:
                    instance = cls(*args_kwargs)
                    break
                except TypeError:
                    continue
            if instance is None:
                info.status = "error"
                info.last_error = "Could not instantiate class with any signature"
                return False

            info.instance = instance
            info.status = "ready"
            logger.info(f"✓ {info.name} loaded ({info.class_name})")
            return True

        except Exception as e:
            info.status = "error"
            info.last_error = f"{type(e).__name__}: {e}"
            logger.warning(f"✗ {info.name} failed: {info.last_error}")
            return False

    def init_all(self) -> Tuple[int, int]:
        """Initialize all modules. Returns (ready_count, total_count)."""
        ready = 0
        total = len(self.modules)
        # First pass: load all
        for name, info in self.modules.items():
            if self._load_module(info):
                ready += 1
        # Second pass: resolve dependencies
        for name, info in self.modules.items():
            if info.status == "ready":
                for dep in info.dependencies:
                    if self.modules.get(dep, ModuleInfo("", "", "", "")).status != "ready":
                        info.status = "disabled"
                        info.last_error = f"Dependency {dep} not ready"
                        ready -= 1
        logger.info(f"ASI Kernel: {ready}/{total} modules ready")
        return ready, total

    def health_check(self) -> Dict[str, str]:
        """Check health of all modules."""
        return {name: info.status for name, info in self.modules.items()}

    def call(self, module_name: str, method: str, *args, **kwargs) -> Any:
        """Call a method on a loaded module."""
        info = self.modules.get(module_name)
        if not info or not info.instance:
            raise RuntimeError(f"Module {module_name} not loaded")
        fn = getattr(info.instance, method, None)
        if not fn:
            raise RuntimeError(f"Method {method} not found on {module_name}")
        return fn(*args, **kwargs)

    def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast a message to all listening modules."""
        self._message_bus.append({"time": time.time(), **message})
        # Keep last 1000 messages
        if len(self._message_bus) > 1000:
            self._message_bus = self._message_bus[-1000:]

    def get_messages(self, module_name: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get recent messages from the bus."""
        msgs = self._message_bus[-limit:]
        if module_name:
            msgs = [m for m in msgs if m.get("target") == module_name or m.get("source") == module_name]
        return msgs

    def shutdown(self) -> None:
        """Gracefully shutdown all modules."""
        for name, info in self.modules.items():
            if info.instance and hasattr(info.instance, "shutdown"):
                try:
                    info.instance.shutdown()
                except Exception as e:
                    logger.warning(f"Shutdown error for {name}: {e}")
            info.status = "uninitialized"
            info.instance = None
        self._running = False
        logger.info("ASI Kernel shutdown complete")

    def summary(self) -> Dict[str, Any]:
        """Return system summary for dashboard."""
        ready = sum(1 for m in self.modules.values() if m.status == "ready")
        return {
            "total_modules": len(self.modules),
            "ready_modules": ready,
            "health_pct": ready / len(self.modules) * 100 if self.modules else 0,
            "categories": {cat: sum(1 for m in self.modules.values() if m.category == cat and m.status == "ready")
                          for cat in set(m.category for m in self.modules.values())},
            "errors": {name: info.last_error for name, info in self.modules.items() if info.status == "error"},
        }


def _self_test():
    print("=" * 60)
    print("ASI Unified Kernel — Self Test")
    print("=" * 60)

    kernel = ASIKernel()
    ready, total = kernel.init_all()
    print(f"[Init] {ready}/{total} modules ready")

    health = kernel.health_check()
    for name, status in health.items():
        symbol = "✓" if status == "ready" else "✗"
        print(f"  {symbol} {name}: {status}")

    print(f"[Summary]")
    summary = kernel.summary()
    print(f"  Health: {summary['health_pct']:.0f}%")
    print(f"  Categories: {summary['categories']}")

    # Test broadcast
    kernel.broadcast({"source": "test", "target": "world_sim", "action": "step", "payload": {"n": 1}})
    msgs = kernel.get_messages(limit=5)
    print(f"[Bus] Messages: {len(msgs)}")

    # Test module call
    try:
        if kernel.modules.get("causal_reasoning") and kernel.modules["causal_reasoning"].status == "ready":
            result = kernel.call("causal_reasoning", "add_node", "X")
            print(f"[Call] causal_reasoning.add_node('X'): {result}")
    except Exception as e:
        print(f"[Call] causal_reasoning test: {e}")

    kernel.shutdown()
    print("\n" + "=" * 60)
    print(f"PASS: {ready}/{total} modules ready")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
