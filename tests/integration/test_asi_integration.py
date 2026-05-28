#!/usr/bin/env python3
"""
Cross-Module ASI Integration Tests — MAGNATRIX-OS
Path: tests/integration/test_asi_integration.py
Tests inter-module communication and end-to-end workflows.
"""

import os
import sys
import random
import math
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def main():
    passed = 0
    total = 0
    results = {}

    def check(name, condition, detail=""):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            results[name] = "PASS"
            print(f"  [PASS] {name}")
        else:
            results[name] = f"FAIL: {detail}"
            print(f"  [FAIL] {name}: {detail}")

    print("=" * 60)
    print("Cross-Module ASI Integration Tests")
    print("=" * 60)

    # ── Test 1: ASI Kernel loads all 20 modules ──
    try:
        from runtime.asi_kernel_native import ASIKernel
        kernel = ASIKernel(PROJECT_ROOT)
        ready, mod_total = kernel.init_all()
        check("Kernel loads all 20 modules", ready == 20, f"got {ready}/{mod_total}")
        kernel.shutdown()
    except Exception as e:
        check("Kernel loads all 20 modules", False, str(e))

    # ── Test 2: Tri-Language Bridge integrates ASI ──
    try:
        from runtime.tri_language_bridge import TriLanguageHub
        hub = TriLanguageHub()
        status = hub.status()
        check("TriLanguageHub detects ASI kernel", "asi_ready" in status and "asi_health_pct" in status)
    except Exception as e:
        check("TriLanguageHub detects ASI kernel", False, str(e))

    # ── Test 3: Crypto + ASI secure operation ──
    try:
        from runtime.tri_language_bridge import TriLanguageHub
        hub = TriLanguageHub()
        result = hub.secure_asi_operation("predict", b"BTCUSDT")
        check("Rust crypto signs ASI operation", result.get("verified") and len(result.get("data_hash", "")) == 64)
    except Exception as e:
        check("Rust crypto signs ASI operation", False, str(e))

    # ── Test 4: Hyperprediction feeds from simulated ticks ──
    try:
        from ai.hyperpredict_native import HyperPredictEngine
        hp = HyperPredictEngine()
        for i in range(50):
            price = 50000.0 + random.gauss(0, 100)
            hp.feed("TEST_0", price)
        pred = hp.predict("TEST_0", 1)
        check("Hyperprediction on tick series", len(pred) > 0 and pred[0].value > 0)
    except Exception as e:
        check("Hyperprediction on tick series", False, str(e))

    # ── Test 5: World Sim physics + energy conservation ──
    try:
        from runtime.world_sim_native import World, PhysicsDomain, Vec2, Position, Velocity, Mass
        world = World(dt=0.001)
        phys = PhysicsDomain(world, gravity=Vec2(0.0, -9.8))
        world.add_domain(phys)
        e = world.add_entity()
        world.ecs.add_component(e, Position(Vec2(0.0, 10.0)))
        world.ecs.add_component(e, Velocity(Vec2(1.0, 0.0)))
        world.ecs.add_component(e, Mass(1.0))
        E0 = phys.total_energy()
        world.step(100)
        E1 = phys.total_energy()
        drift = abs(E1 - E0) / abs(E0) if E0 != 0 else 0
        check("World sim energy conservation", drift < 0.1, f"drift={drift:.2%}")
    except Exception as e:
        check("World sim energy conservation", False, str(e))

    # ── Test 6: Episodic Memory stores and queries ──
    try:
        from knowledge.episodic_native import EpisodicMemory, Episode, Action
        import tempfile
        db = tempfile.mktemp(suffix=".db")
        mem = EpisodicMemory(db, auto_consolidate=False)
        now = time.time()
        for i in range(20):
            ep = Episode(
                id=f"ep_{i:03d}", ts=now - i, agent_id="agent_alpha",
                observation={"price": 50000 + i}, action=Action("trade", {"side": "buy"}),
                reward=float(i % 10) / 10, raw_text=f"Agent bought at price {50000 + i}",
                tags=["trade", "buy"],
            )
            mem.write(ep)
        results_query = mem.query("buy trade", k=5)
        replayed = list(mem.replay("agent_alpha", (now - 100, now)))
        check("Episodic memory query+replay", len(results_query) > 0 and len(replayed) == 20)
    except Exception as e:
        check("Episodic memory query+replay", False, str(e))

    # ── Test 7: Meta-Cognition confidence calibration ──
    try:
        from ai.meta_cognition_native import ConfidenceCalibrator, Strategy
        cal = ConfidenceCalibrator()
        for i in range(30):
            conf = 0.5 + random.random() * 0.5
            correct = random.random() < conf
            cal.record(conf, correct)
        acc = cal.expected_accuracy()
        check("Meta-cognition calibration", 0 <= acc <= 1, f"accuracy={acc}")
    except Exception as e:
        check("Meta-cognition calibration", False, str(e))

    # ── Test 8: Replication Guard rate limiting ──
    try:
        from security.replication_guard_native import TokenBucket
        bucket = TokenBucket(rate=5, capacity=5)
        allowed = 0
        for i in range(10):
            if bucket.consume():
                allowed += 1
        check("Replication guard rate limit", allowed <= 5, f"allowed={allowed}")
    except Exception as e:
        check("Replication guard rate limit", False, str(e))

    # ── Test 9: Auto-Research generates hypotheses ──
    try:
        from knowledge.auto_research_native import PatternInductor
        inductor = PatternInductor()
        data = []
        for i in range(100):
            x = float(i)
            y = 2.0 * x + random.gauss(0, 5)
            data.append({"x": x, "y": y, "z": random.gauss(0, 10)})
        hyps = inductor.generate(data, max_hypotheses=3)
        check("Auto-research hypothesis generation", len(hyps) > 0)
    except Exception as e:
        check("Auto-research hypothesis generation", False, str(e))

    # ── Test 10: Sensor Mesh spatial + anomaly ──
    try:
        from runtime.sensor_mesh_native import SensorMesh, SensorReading
        mesh = SensorMesh(cell_size=10.0)
        for i in range(20):
            mesh.ingest(SensorReading("temp_1", float(i), 20.0 + random.gauss(0, 2), x=float(i), y=0.0, z=0.0))
        mesh.ingest(SensorReading("temp_1", 21.0, 80.0, x=21.0, y=0.0, z=0.0))
        nearby = mesh.query_spatial(5.0, 0.0, 0.0, 5.0)
        anomalies = mesh.detect_anomaly("temp_1", window=10)
        check("Sensor mesh spatial+anomaly", len(nearby) > 0 and len(anomalies) > 0)
    except Exception as e:
        check("Sensor mesh spatial+anomaly", False, str(e))

    # ── Test 11: BCI decoding ──
    try:
        from ai.bci_native import BCIDecoder, EEGSample
        bci = BCIDecoder(n_channels=4)
        bci.calibrate(1.0)
        train_samples = []
        labels = []
        for i in range(20):
            ch = [random.gauss(5 if i % 2 == 0 else 15, 3) for _ in range(4)]
            train_samples.append(EEGSample(float(i), ch))
            labels.append(0 if i % 2 == 0 else 1)
        bci.train(train_samples, labels)
        test_sample = EEGSample(0.0, [random.gauss(15, 3) for _ in range(4)])
        label, conf = bci.decode(test_sample)
        check("BCI train+decode", label in (0, 1) and 0 <= conf <= 1)
    except Exception as e:
        check("BCI train+decode", False, str(e))

    # ── Test 12: Energy Grid renewable-first ──
    try:
        from runtime.energy_grid_native import EnergyGrid, EnergySource
        grid = EnergyGrid()
        grid.add_source(EnergySource("solar", 500, 0, 0.05, True))
        grid.add_source(EnergySource("gas", 1000, 450, 0.15, False))
        sched = grid.optimize_schedule(400)
        check("Energy grid renewable-first", sched.get("shortfall", 1) == 0 and sched.get("renewable_pct", 0) >= 50)
    except Exception as e:
        check("Energy grid renewable-first", False, str(e))

    # ── Test 13: Goal alignment corrigibility ──
    try:
        from ai.goal_alignment_native import GoalAlignmentEngine
        ga = GoalAlignmentEngine(["speed", "safety"])
        ok, msg = ga.corrigibility_check("process_data")
        ok2, msg2 = ga.corrigibility_check("block_shutdown")
        check("Goal alignment corrigibility", ok and not ok2, f"safe={ok}, unsafe_blocked={not ok2}")
    except Exception as e:
        check("Goal alignment corrigibility", False, str(e))

    # ── Test 14: Quantum Bridge routing ──
    try:
        from ai.quantum_bridge_native import QuantumBridge, QuantumTask
        bridge = QuantumBridge(max_qubits=30)
        r1 = bridge.route_task(QuantumTask("grover_small", "grover", 16, 10.0))
        r2 = bridge.route_task(QuantumTask("factor_large", "factorization", 1000000, 1000.0))
        check("Quantum bridge routing", r1["route"] in ("quantum", "classical") and r2["route"] == "classical")
    except Exception as e:
        check("Quantum bridge routing", False, str(e))

    # ── Test 15: ASI Message Bus ──
    try:
        from runtime.asi_kernel_native import ASIKernel
        kernel = ASIKernel(PROJECT_ROOT)
        kernel.init_all()
        kernel.broadcast({"source": "world_sim", "action": "tick", "payload": {}})
        kernel.broadcast({"source": "security", "action": "alert", "payload": {}})
        msgs = kernel.get_messages(limit=10)
        kernel.shutdown()
        check("ASI message bus", len(msgs) == 2)
    except Exception as e:
        check("ASI message bus", False, str(e))

    # ── Test 16: Embodiment + e-stop ──
    try:
        from runtime.embodiment_native import EmbodimentLayer
        robot = EmbodimentLayer(n_joints=3)
        ok = robot.connect()
        robot.send_command([0.5, 0.3, 0.2])
        state = robot.read_state()
        robot.estop()
        blocked = not robot.send_command([1.0, 1.0, 1.0])
        check("Embodiment connect+e-stop", ok and len(state["joints"]) == 3 and blocked)
    except Exception as e:
        check("Embodiment connect+e-stop", False, str(e))

    # ── Test 17: Cosmological climate + supply chain ──
    try:
        from runtime.cosmo_native import CosmoModel
        cosmo = CosmoModel()
        climate = cosmo.climate_predict(solar_constant=1361, albedo=0.3)
        flow = cosmo.supply_chain_model(["S", "A", "B", "T"],
            [("S", "A", 10), ("S", "B", 5), ("A", "T", 7), ("B", "T", 8)], "S", "T")
        check("Cosmo climate+supply chain", -50 < climate["equilibrium_temp_c"] < 100 and flow > 0)
    except Exception as e:
        check("Cosmo climate+supply chain", False, str(e))

    # ── Test 18: RSI safety + sandbox ──
    try:
        from ai.rsi_engine_native import RSIEngine
        rsi = RSIEngine()
        pid = rsi.propose_modification("test.py", "def f(x): return x", "def f(x): return x + 1", "test")
        safe, violations = rsi.safety.check("import os; os.system('ls')")
        check("RSI safety blocks dangerous code", not safe)
    except Exception as e:
        check("RSI safety blocks dangerous code", False, str(e))

    # ── Test 19: Affective PAD state ──
    try:
        from ai.affective_native import AffectiveState
        state = AffectiveState(pleasure=0.5, arousal=0.7, dominance=0.3)
        label = state.to_emotion_label()
        check("Affective PAD model", 0 <= state.pleasure <= 1 and label is not None)
    except Exception as e:
        check("Affective PAD model", False, str(e))

    # ── Test 20: Full system stress test ──
    try:
        from runtime.asi_kernel_native import ASIKernel
        from runtime.tri_language_bridge import TriLanguageHub
        kernel = ASIKernel(PROJECT_ROOT)
        ready, _ = kernel.init_all()
        hub = TriLanguageHub()
        health = hub.asi_health()
        summary = hub.asi.summary
        kernel.shutdown()
        check("Full system stress", ready == 20 and len(health) == 20 and summary.get("health_pct") == 100.0)
    except Exception as e:
        check("Full system stress", False, str(e))

    # Results
    print()
    print("=" * 60)
    print(f"PASS: {passed}/{total}")
    print("=" * 60)

    for k, v in results.items():
        if v != "PASS":
            print(f"  {k}: {v}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
