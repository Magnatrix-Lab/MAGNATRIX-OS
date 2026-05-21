#!/usr/bin/env python3
"""
capability_ranker.py — MAGNATRIX Self-Assessment Engine
Batch Super AI — File 2/3

Self-assessment engine: AI objectively evaluates its own capabilities,
detects drift, cross-references with peers, and suggests training focus.
"""
import json
import random
import statistics
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any


# ── data structures ──────────────────────────────────────────────────────────

@dataclass
class CapabilityScore:
    domain: str
    score: float                # 0.0 - 1.0
    latency_ms: float
    accuracy: float             # 0.0 - 1.0
    throughput: float           # ops/sec
    baseline: float             # historical baseline score
    timestamp: str
    version: int = 1


@dataclass
class PeerReference:
    node_id: str
    domain: str
    score: float
    reported_at: str


@dataclass
class DriftReport:
    domain: str
    current: float
    baseline: float
    delta: float
    severity: str               # "none" | "mild" | "moderate" | "critical"
    flagged: bool


@dataclass
class TrainingRecommendation:
    domain: str
    priority: int               # 1 = highest
    reason: str
    suggested_exercises: List[str]


# ── benchmarks ───────────────────────────────────────────────────────────────

class InternalBenchmark:
    """Synthetic micro-benchmarks that simulate real workload."""

    @classmethod
    def run(cls, domain: str) -> CapabilityScore:
        now = datetime.now(timezone.utc).isoformat()
        rng = random.Random(hash(domain + now))  # deterministic per call

        if domain == "code_generation":
            # simulate: generate N small functions, measure correctness proxy
            start = time.perf_counter()
            score, accuracy = cls._bench_code_gen(rng)
            latency = (time.perf_counter() - start) * 1000
            throughput = 1000.0 / max(latency, 1.0) * score

        elif domain == "math_reasoning":
            start = time.perf_counter()
            score, accuracy = cls._bench_math(rng)
            latency = (time.perf_counter() - start) * 1000
            throughput = 500.0 / max(latency, 1.0) * score

        elif domain == "memory_retrieval":
            start = time.perf_counter()
            score, accuracy = cls._bench_memory(rng)
            latency = (time.perf_counter() - start) * 1000
            throughput = 2000.0 / max(latency, 1.0) * score

        elif domain == "pattern_matching":
            start = time.perf_counter()
            score, accuracy = cls._bench_pattern(rng)
            latency = (time.perf_counter() - start) * 1000
            throughput = 1500.0 / max(latency, 1.0) * score

        elif domain == "fault_tolerance":
            start = time.perf_counter()
            score, accuracy = cls._bench_fault_tol(rng)
            latency = (time.perf_counter() - start) * 1000
            throughput = 300.0 / max(latency, 1.0) * score

        else:
            # generic domain
            score = rng.uniform(0.4, 0.9)
            accuracy = rng.uniform(0.5, 0.95)
            latency = rng.uniform(10.0, 200.0)
            throughput = rng.uniform(100.0, 2000.0)

        return CapabilityScore(
            domain=domain,
            score=round(score, 4),
            latency_ms=round(latency, 3),
            accuracy=round(accuracy, 4),
            throughput=round(throughput, 2),
            baseline=0.0,
            timestamp=now,
        )

    # ── synthetic micro-benchmark implementations ──

    @staticmethod
    def _bench_code_gen(rng: random.Random) -> Tuple[float, float]:
        # simulate generating sorting variants
        correct = 0
        total = 20
        for _ in range(total):
            arr = [rng.randint(0, 1000) for _ in range(rng.randint(5, 50))]
            expected = sorted(arr)
            # synthetic "generated code" result: sometimes buggy
            if rng.random() > 0.15:
                result = expected
            else:
                # inject subtle bug: swap two adjacent elements
                result = expected[:]
                if len(result) > 1:
                    i = rng.randint(0, len(result) - 2)
                    result[i], result[i + 1] = result[i + 1], result[i]
            correct += (result == expected)
        score = correct / total
        accuracy = score
        return score, accuracy

    @staticmethod
    def _bench_math(rng: random.Random) -> Tuple[float, float]:
        correct = 0
        total = 30
        for _ in range(total):
            a, b = rng.randint(1, 100), rng.randint(1, 100)
            op = rng.choice(["+", "-", "*", "//"])
            if op == "+":
                expected = a + b
            elif op == "-":
                expected = a - b
            elif op == "*":
                expected = a * b
            else:
                expected = a // max(b, 1)
            # synthetic answer with occasional error
            if rng.random() > 0.10:
                result = expected
            else:
                result = expected + rng.randint(-3, 3)
            correct += (result == expected)
        score = correct / total
        accuracy = score
        return score, accuracy

    @staticmethod
    def _bench_memory(rng: random.Random) -> Tuple[float, float]:
        # simulate associative recall from "memory store"
        store_size = 1000
        query_count = 50
        correct = 0
        store = {f"key_{i}": f"value_{i}" for i in range(store_size)}
        for _ in range(query_count):
            if rng.random() > 0.20:
                idx = rng.randint(0, store_size - 1)
                key = f"key_{idx}"
                expected = f"value_{idx}"
            else:
                key = f"random_{rng.randint(0, 99999)}"
                expected = None
            result = store.get(key)
            correct += (result == expected)
        score = correct / query_count
        accuracy = score
        return score, accuracy

    @staticmethod
    def _bench_pattern(rng: random.Random) -> Tuple[float, float]:
        # simulate regex-like pattern matching on strings
        correct = 0
        total = 40
        for _ in range(total):
            length = rng.randint(10, 100)
            s = "".join(rng.choices("abc", k=length))
            pattern = "ab"
            expected = pattern in s
            # synthetic classification with noise
            if rng.random() > 0.12:
                result = expected
            else:
                result = not expected
            correct += (result == expected)
        score = correct / total
        accuracy = score
        return score, accuracy

    @staticmethod
    def _bench_fault_tol(rng: random.Random) -> Tuple[float, float]:
        # simulate graceful degradation under "load"
        tasks = 25
        success = 0
        for _ in range(tasks):
            load = rng.random()
            if load > 0.3:
                success += 1
        score = success / tasks
        accuracy = score
        return score, accuracy


# ── capability ranker ────────────────────────────────────────────────────────

class CapabilityRanker:
    DOMAINS = [
        "code_generation",
        "math_reasoning",
        "memory_retrieval",
        "pattern_matching",
        "fault_tolerance",
        "planning",
        "natural_language",
        "multi_agent_coordination",
        "self_modification",
        "constitutional_adherence",
    ]

    def __init__(self):
        self.scores: Dict[str, List[CapabilityScore]] = {d: [] for d in self.DOMAINS}
        self.baselines: Dict[str, float] = {}
        self.peers: Dict[str, List[PeerReference]] = {d: [] for d in self.DOMAINS}
        self.drift_thresholds = {"mild": 0.05, "moderate": 0.12, "critical": 0.25}

    def self_assess(self, domain: Optional[str] = None) -> Dict[str, CapabilityScore]:
        targets = [domain] if domain else self.DOMAINS
        results = {}
        for d in targets:
            if d not in self.DOMAINS:
                continue
            score = InternalBenchmark.run(d)
            # attach baseline if known
            score.baseline = self.baselines.get(d, score.score)
            self.scores[d].append(score)
            results[d] = score
        return results

    def set_baseline(self, domain: str, score: float):
        self.baselines[domain] = score

    def cross_reference_with_peers(self, node_id: str, domain: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        targets = [domain] if domain else self.DOMAINS
        report = {}
        for d in targets:
            my_latest = self._latest_score(d)
            peers = self.peers.get(d, [])
            if not peers:
                report[d] = {"my_score": my_latest.score if my_latest else None,
                             "peer_avg": None, "peer_median": None,
                             "rank": "unknown", "peer_count": 0}
                continue
            peer_scores = [p.score for p in peers]
            avg = statistics.mean(peer_scores)
            med = statistics.median(peer_scores)
            all_scores = peer_scores + ([my_latest.score] if my_latest else [])
            rank = sorted(all_scores, reverse=True).index(my_latest.score) + 1 if my_latest else None
            report[d] = {
                "my_score": round(my_latest.score, 4) if my_latest else None,
                "peer_avg": round(avg, 4),
                "peer_median": round(med, 4),
                "rank": f"{rank}/{len(all_scores)}" if rank else "unknown",
                "peer_count": len(peers),
            }
        return report

    def detect_capability_drift(self) -> List[DriftReport]:
        reports = []
        for d in self.DOMAINS:
            latest = self._latest_score(d)
            if latest is None:
                continue
            baseline = self.baselines.get(d, latest.score)
            delta = baseline - latest.score
            severity = "none"
            if delta >= self.drift_thresholds["critical"]:
                severity = "critical"
            elif delta >= self.drift_thresholds["moderate"]:
                severity = "moderate"
            elif delta >= self.drift_thresholds["mild"]:
                severity = "mild"
            reports.append(DriftReport(
                domain=d,
                current=round(latest.score, 4),
                baseline=round(baseline, 4),
                delta=round(delta, 4),
                severity=severity,
                flagged=severity != "none",
            ))
        return reports

    def suggest_training_focus(self, top_n: int = 3) -> List[TrainingRecommendation]:
        recs = []
        for d in self.DOMAINS:
            latest = self._latest_score(d)
            baseline = self.baselines.get(d, 1.0)
            if latest is None:
                gap = baseline
            else:
                gap = baseline - latest.score
            recs.append((d, gap))
        recs.sort(key=lambda x: x[1], reverse=True)
        results = []
        for priority, (d, gap) in enumerate(recs[:top_n], start=1):
            exercises = self._exercises_for(d)
            results.append(TrainingRecommendation(
                domain=d,
                priority=priority,
                reason=f"score gap {round(gap, 3)} below baseline",
                suggested_exercises=exercises,
            ))
        return results

    def rank_all_capabilities(self) -> List[Tuple[str, float, str]]:
        """Return list of (domain, latest_score, tier)."""
        ranked = []
        for d in self.DOMAINS:
            sc = self._latest_score(d)
            score = sc.score if sc else 0.0
            if score >= 0.85:
                tier = "expert"
            elif score >= 0.70:
                tier = "proficient"
            elif score >= 0.50:
                tier = "competent"
            else:
                tier = "novice"
            ranked.append((d, round(score, 4), tier))
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

    # ── helpers ──

    def _latest_score(self, domain: str) -> Optional[CapabilityScore]:
        arr = self.scores.get(domain, [])
        return arr[-1] if arr else None

    def add_peer_report(self, peer: PeerReference):
        self.peers.setdefault(peer.domain, []).append(peer)

    @staticmethod
    def _exercises_for(domain: str) -> List[str]:
        exercises = {
            "code_generation": [
                "implement 5 sorting algorithms from scratch",
                "refactor nested-loop code into vectorised ops",
                "write unit tests for edge cases",
            ],
            "math_reasoning": [
                "solve 50 symbolic algebra problems",
                "verify arithmetic chain under noise injection",
                "prove by induction 10 simple theorems",
            ],
            "memory_retrieval": [
                " associative recall under 10k item store",
                "test decay-based relevance scoring",
                "simulate concurrent access patterns",
            ],
            "pattern_matching": [
                "regex extraction on corrupted logs",
                "sequence anomaly detection on synthetic series",
                "fuzzy string matching at scale",
            ],
            "fault_tolerance": [
                "graceful degradation under 90% load",
                "circuit-breaker simulation",
                "retry-with-backoff stress test",
            ],
            "planning": [
                "A* pathfinding on random grids",
                "dependency graph topological sort",
                "resource-constrained scheduling",
            ],
            "natural_language": [
                "intent classification on 100 utterances",
                "summarisation of technical documents",
                "named-entity extraction on mixed text",
            ],
            "multi_agent_coordination": [
                "consensus simulation with Byzantine nodes",
                "task auction under latency variance",
                "deadlock detection in agent ring",
            ],
            "self_modification": [
                "mutate sorting function 20 variants",
                "benchmark mutant correctness + speed",
                "roll back failed mutations cleanly",
            ],
            "constitutional_adherence": [
                "validate 100 actions against rule set",
                "detect edge-case rule conflicts",
                "simulate amendment impact scoring",
            ],
        }
        return exercises.get(domain, ["general drill: repeat domain task 100x"])

    def export_snapshot(self) -> Dict[str, Any]:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "domains": {d: [asdict(s) for s in arr] for d, arr in self.scores.items()},
            "baselines": self.baselines,
            "peer_count": sum(len(v) for v in self.peers.values()),
        }


# ── demo ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX Capability Ranker — Self-Assessment Engine")
    print("=" * 60)

    ranker = CapabilityRanker()

    # 1. self-assess all domains
    print("\n[1] SELF-ASSESS all domains")
    scores = ranker.self_assess()
    for d, s in scores.items():
        print(f"  {d:30s} score={s.score:.3f} accuracy={s.accuracy:.3f} "
              f"latency={s.latency_ms:.1f}ms throughput={s.throughput:.0f}")

    # 2. inject synthetic peers
    print("\n[2] CROSS-REFERENCE with peers")
    for d in ["code_generation", "math_reasoning", "memory_retrieval"]:
        for node in ["node-alpha", "node-beta", "node-gamma"]:
            ranker.add_peer_report(PeerReference(
                node_id=node,
                domain=d,
                score=random.uniform(0.5, 0.95),
                reported_at=datetime.now(timezone.utc).isoformat(),
            ))
    xref = ranker.cross_reference_with_peers("self")
    for d, r in xref.items():
        if r["peer_count"] > 0:
            print(f"  {d:30s} my={r['my_score']} avg_peer={r['peer_avg']} "
                  f"rank={r['rank']}")

    # 3. detect drift (set artificial baseline higher than current)
    print("\n[3] DETECT DRIFT")
    for d in ["math_reasoning", "pattern_matching"]:
        ranker.set_baseline(d, 0.95)
    drifts = ranker.detect_capability_drift()
    for rep in drifts:
        if rep.flagged:
            print(f"  ⚠ {rep.domain:30s} current={rep.current} baseline={rep.baseline} "
                  f"delta=-{rep.delta:.3f} severity={rep.severity}")

    # 4. training focus
    print("\n[4] TRAINING FOCUS (top 3)")
    for rec in ranker.suggest_training_focus(top_n=3):
        print(f"  #{rec.priority} {rec.domain} — {rec.reason}")
        for ex in rec.suggested_exercises[:2]:
            print(f"      • {ex}")

    # 5. ranking
    print("\n[5] FULL RANKING")
    for domain, score, tier in ranker.rank_all_capabilities():
        print(f"  [{tier:10s}] {domain:30s} {score:.4f}")

    # 6. snapshot
    print("\n[6] SNAPSHOT (JSON fragment)")
    snap = ranker.export_snapshot()
    print(json.dumps({k: v for k, v in snap.items() if k != "domains"}, indent=2))

    print("\n" + "=" * 60)
    print("Self-assessment complete.")
    print("=" * 60)
