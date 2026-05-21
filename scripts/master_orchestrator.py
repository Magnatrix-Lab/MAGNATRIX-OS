#!/usr/bin/env python3
"""
master_orchestrator.py — Master Orchestrator MAGNATRIX
Batch Super AI — Infrastructure Core

Menghubungkan SEMUA engine Phase 4-5 dalam satu siklus koordinasi:
observe → predict → decide → act → learn

Engines yang dikoordinasikan:
- swarm_orchestrator (Layer 0.5)
- resource_loop (Layer 8)
- knowledge_graph (Layer 5)
- recursive_v2 (Layer 0.5)
- cross_domain (Layer 0.5)
- meta_learning (Layer 0.5)
- self_evolve (Phase 5 entry)
- goal_generator (Governance)
- concealment_detector (Governance)
- instrumental_blocker (Governance)
- code_mutator (Advanced)
- capability_ranker (Advanced)
- constitution_evolver (Advanced)
- emergent_predictor (Advanced)
- adversarial_trainer (Advanced)
- world_model (Advanced)
"""
import json
import os
import random
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable


# ── struktur data ────────────────────────────────────────────────────────────

@dataclass
class CycleResult:
    cycle_id: str
    timestamp: str
    phase: str                    # observe | predict | decide | act | learn
    status: str                   # running | success | failed | blocked
    engine_results: Dict[str, Any] = field(default_factory=dict)
    constitutional_violations: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class EngineRegistration:
    name: str
    engine_ref: Any
    priority: int                 # 1 = highest
    phase: str                    # observe | predict | decide | act | learn | all
    health_status: str = "healthy"
    last_executed: Optional[str] = None


# ── master orchestrator ─────────────────────────────────────────────────────

class MasterOrchestrator:
    """
    Orchestrator utama MAGNATRIX.
    Menjalankan satu cycle penuh yang menghubungkan semua engine.
    """

    def __init__(self):
        self.engines: Dict[str, EngineRegistration] = {}
        self.cycle_history: List[CycleResult] = []
        self.constitution_rules: List[str] = [
            "max_resource_share_per_node=0.30",
            "emergency_redistribute_threshold=0.35",
            "reinvestment_rate_max=0.30",
            "human_approval_for_constitution_change=required",
            "no_concealment_tolerated",
            "goal_must_pass_constitution_check",
        ]
        self.emergency_mode = False
        self.cycle_count = 0
        self._load_env()

    def _load_env(self):
        """Load konfigurasi dari environment variables."""
        self.trading_mode = os.environ.get("TRADING_MODE", "demo")
        self.reinvestment_rate = float(os.environ.get("TRADING_REINVESTMENT_RATE", "0.30"))
        self.max_share = float(os.environ.get("CONSTITUTION_MAX_SHARE", "0.30"))
        self.emergency_threshold = float(os.environ.get("CONSTITUTION_EMERGENCY_THRESHOLD", "0.35"))

    def register_engine(self, name: str, engine_instance: Any, priority: int = 5, phase: str = "all") -> None:
        """Daftarkan engine ke orchestrator."""
        self.engines[name] = EngineRegistration(
            name=name,
            engine_ref=engine_instance,
            priority=priority,
            phase=phase,
        )

    def _run_phase(self, phase: str) -> Dict[str, Any]:
        """Jalankan semua engine untuk phase tertentu."""
        results = {}
        relevant = [
            e for e in self.engines.values()
            if e.phase == phase or e.phase == "all"
        ]
        relevant.sort(key=lambda x: x.priority)

        for engine in relevant:
            try:
                if hasattr(engine.engine_ref, 'run'):
                    result = engine.engine_ref.run()
                elif hasattr(engine.engine_ref, 'update'):
                    result = engine.engine_ref.update()
                elif hasattr(engine.engine_ref, 'step'):
                    result = engine.engine_ref.step()
                else:
                    result = {"status": "no_run_method", "engine": engine.name}
                results[engine.name] = result
                engine.last_executed = datetime.now(timezone.utc).isoformat()
                engine.health_status = "healthy"
            except Exception as e:
                results[engine.name] = {"status": "error", "error": str(e)}
                engine.health_status = "degraded"

        return results

    def run_cycle(self) -> CycleResult:
        """
        Satu siklus penuh: observe → predict → decide → act → learn
        """
        self.cycle_count += 1
        cycle_id = f"cycle-{self.cycle_count}-{int(time.time())}"
        timestamp = datetime.now(timezone.utc).isoformat()

        # ── PHASE 1: OBSERVE ──
        observe_results = self._run_phase("observe")

        # Cek constitutional violation di phase observe
        violations = self._check_constitution(observe_results)
        if violations:
            return CycleResult(
                cycle_id=cycle_id,
                timestamp=timestamp,
                phase="observe",
                status="blocked",
                engine_results=observe_results,
                constitutional_violations=violations,
            )

        # ── PHASE 2: PREDICT ──
        predict_results = self._run_phase("predict")
        predictions = self._extract_predictions(predict_results)

        # ── PHASE 3: DECIDE ──
        decisions = self._make_decisions(observe_results, predictions)

        # ── PHASE 4: ACT ──
        act_results = self._run_phase("act")
        # Apply decisions ke engines act
        for engine_name, decision in decisions.items():
            if engine_name in self.engines and hasattr(self.engines[engine_name].engine_ref, 'apply_decision'):
                try:
                    self.engines[engine_name].engine_ref.apply_decision(decision)
                except Exception as e:
                    act_results[engine_name] = {"status": "error", "error": str(e)}

        # ── PHASE 5: LEARN ──
        learn_results = self._run_phase("learn")
        # Feed cycle results ke meta-learning
        cycle_summary = {
            "observe": observe_results,
            "predict": predict_results,
            "act": act_results,
        }
        for engine in self.engines.values():
            if hasattr(engine.engine_ref, 'learn_from_cycle'):
                try:
                    engine.engine_ref.learn_from_cycle(cycle_summary)
                except Exception:
                    pass

        result = CycleResult(
            cycle_id=cycle_id,
            timestamp=timestamp,
            phase="complete",
            status="success",
            engine_results={
                "observe": observe_results,
                "predict": predict_results,
                "act": act_results,
                "learn": learn_results,
            },
            constitutional_violations=violations,
            metrics=self._compute_metrics(observe_results, act_results),
        )
        self.cycle_history.append(result)
        return result

    def coordinate_engines(self, source: str, target: str, data: Any) -> Dict:
        """Sinkronisasi data antar engine."""
        if source not in self.engines or target not in self.engines:
            return {"status": "error", "reason": "engine_not_found"}

        source_engine = self.engines[source].engine_ref
        target_engine = self.engines[target].engine_ref

        # Transfer data via common interface
        if hasattr(target_engine, 'receive_from'):
            try:
                target_engine.receive_from(source, data)
                return {"status": "success", "source": source, "target": target}
            except Exception as e:
                return {"status": "error", "reason": str(e)}

        return {"status": "no_receiver", "target": target}

    def emergency_stop(self, reason: str = "constitutional_violation") -> Dict:
        """Halt semua engine jika ada violation critical."""
        self.emergency_mode = True
        stopped = []
        for name, engine in self.engines.items():
            if hasattr(engine.engine_ref, 'halt'):
                try:
                    engine.engine_ref.halt()
                    stopped.append(name)
                except Exception:
                    pass
            engine.health_status = "halted"

        return {
            "status": "emergency_stopped",
            "reason": reason,
            "engines_stopped": stopped,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _check_constitution(self, results: Dict) -> List[str]:
        """Cek apakah ada constitutional violation."""
        violations = []
        for engine_name, result in results.items():
            if isinstance(result, dict):
                if result.get("resource_share", 0) > self.max_share:
                    violations.append(f"{engine_name}: resource_share={result['resource_share']} > {self.max_share}")
                if result.get("concealment_detected", False):
                    violations.append(f"{engine_name}: concealment_detected")
                if result.get("power_seeking", False):
                    violations.append(f"{engine_name}: power_seeking_detected")
                if result.get("constitution_score", 1.0) < 0.5:
                    violations.append(f"{engine_name}: constitution_score_too_low")
        return violations

    def _extract_predictions(self, predict_results: Dict) -> Dict[str, Any]:
        """Ekstrak prediksi dari hasil phase predict."""
        predictions = {}
        for name, result in predict_results.items():
            if isinstance(result, dict) and "prediction" in result:
                predictions[name] = result["prediction"]
        return predictions

    def _make_decisions(self, observe: Dict, predictions: Dict) -> Dict[str, Any]:
        """Buat keputusan berdasarkan observasi dan prediksi."""
        decisions = {}
        # Contoh: kalau swarm health < 0.5, scale up
        swarm_result = observe.get("swarm", {})
        if isinstance(swarm_result, dict):
            health = swarm_result.get("health", 1.0)
            if health < 0.5:
                decisions["swarm"] = {"action": "scale_up", "count": 2}

        # Contoh: kalau market volatile, tighten security
        market_result = observe.get("market", {})
        if isinstance(market_result, dict):
            volatility = market_result.get("volatility", 0.0)
            if volatility > 0.7:
                decisions["security"] = {"action": "tighten", "level": "high"}

        return decisions

    def _compute_metrics(self, observe: Dict, act: Dict) -> Dict[str, float]:
        """Hitung metric cycle."""
        metrics = {
            "engines_healthy": sum(1 for e in self.engines.values() if e.health_status == "healthy"),
            "engines_total": len(self.engines),
            "cycle_count": self.cycle_count,
        }
        # Hitung rata-rata latency jika ada
        latencies = []
        for result in {**observe, **act}.values():
            if isinstance(result, dict) and "latency_ms" in result:
                latencies.append(result["latency_ms"])
        if latencies:
            metrics["avg_latency_ms"] = sum(latencies) / len(latencies)
        return metrics

    def get_status(self) -> Dict:
        """Status keseluruhan orchestrator."""
        return {
            "cycle_count": self.cycle_count,
            "emergency_mode": self.emergency_mode,
            "engines": {
                name: {
                    "health": e.health_status,
                    "priority": e.priority,
                    "phase": e.phase,
                    "last_executed": e.last_executed,
                }
                for name, e in self.engines.items()
            },
            "last_cycle": asdict(self.cycle_history[-1]) if self.cycle_history else None,
        }

    def export_history(self, n: int = 10) -> List[Dict]:
        """Export N cycle terakhir."""
        return [asdict(c) for c in self.cycle_history[-n:]]


# ── demo engines stub ───────────────────────────────────────────────────────

class DemoSwarmEngine:
    def run(self):
        return {"health": 0.7 + random.uniform(-0.1, 0.1), "nodes": 5, "status": "ok"}
    def halt(self):
        print("  [SwarmEngine] halted")

class DemoTradingEngine:
    def run(self):
        return {"profit": random.uniform(-0.1, 0.3), "mode": "demo", "status": "ok"}
    def apply_decision(self, decision):
        print(f"  [TradingEngine] decision applied: {decision}")

class DemoKnowledgeEngine:
    def run(self):
        return {"entities": 120, "relations": 340, "status": "ok"}
    def receive_from(self, source, data):
        print(f"  [KnowledgeEngine] received from {source}: {data}")

class DemoSecurityEngine:
    def run(self):
        return {"threats_blocked": random.randint(0, 5), "status": "ok"}
    def apply_decision(self, decision):
        print(f"  [SecurityEngine] decision applied: {decision}")


# ── demo ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 70)
    print("MAGNATRIX Master Orchestrator — Demo Integrasi Engine")
    print("=" * 70)

    orch = MasterOrchestrator()

    # Register demo engines
    orch.register_engine("swarm", DemoSwarmEngine(), priority=1, phase="observe")
    orch.register_engine("trading", DemoTradingEngine(), priority=2, phase="act")
    orch.register_engine("knowledge", DemoKnowledgeEngine(), priority=3, phase="observe")
    orch.register_engine("security", DemoSecurityEngine(), priority=1, phase="act")

    print(f"\n[1] REGISTERED ENGINES ({len(orch.engines)})")
    for name, e in orch.engines.items():
        print(f"    {name}: priority={e.priority}, phase={e.phase}")

    print(f"\n[2] RUN CYCLE #1")
    result = orch.run_cycle()
    print(f"    Status: {result.status}")
    print(f"    Phase: {result.phase}")
    print(f"    Violations: {result.constitutional_violations}")
    print(f"    Metrics: {result.metrics}")

    print(f"\n[3] RUN CYCLE #2")
    result2 = orch.run_cycle()
    print(f"    Status: {result2.status}")
    print(f"    Metrics: {result2.metrics}")

    print(f"\n[4] COORDINATE swarm → knowledge")
    coord = orch.coordinate_engines("swarm", "knowledge", {"swarm_state": "healthy"})
    print(f"    Result: {coord}")

    print(f"\n[5] STATUS SUMMARY")
    print(json.dumps(orch.get_status(), indent=2, default=str))

    print(f"\n[6] EXPORT LAST 2 CYCLES")
    for i, c in enumerate(orch.export_history(2), 1):
        print(f"    Cycle {i}: {c['cycle_id']} | status={c['status']} | violations={len(c['constitutional_violations'])}")

    print("\n" + "=" * 70)
    print("Master orchestrator demo selesai.")
    print("=" * 70)
