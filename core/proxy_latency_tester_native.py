"""Proxy Latency Tester - Speed and latency testing for proxies."""
from __future__ import annotations

import json
import time
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class LatencyTest:
    test_id: str
    proxy_id: str
    timestamp: float
    latency_ms: float
    throughput_kbps: float = 0.0
    jitter_ms: float = 0.0
    packet_loss: float = 0.0
    grade: str = "unknown"  # A+ (<50ms), A (<100ms), B (<200ms), C (<500ms), D (>500ms), F (timeout)

    def to_dict(self) -> Dict:
        return {
            "test_id": self.test_id,
            "proxy_id": self.proxy_id,
            "timestamp": self.timestamp,
            "latency_ms": round(self.latency_ms, 2),
            "throughput_kbps": round(self.throughput_kbps, 2),
            "jitter_ms": round(self.jitter_ms, 2),
            "packet_loss": round(self.packet_loss, 4),
            "grade": self.grade,
        }


class ProxyLatencyTester:
    """Test proxy latency and assign performance grades."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "proxy_latency"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.tests: List[LatencyTest] = []
        self._load_state()

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for t in data.get("tests", []):
                    self.tests.append(LatencyTest(**t))
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {"tests": [t.to_dict() for t in self.tests[-2000:]]}
        state_file.write_text(json.dumps(state, indent=2))

    def _grade(self, latency_ms: float) -> str:
        if latency_ms < 50:
            return "A+"
        elif latency_ms < 100:
            return "A"
        elif latency_ms < 200:
            return "B"
        elif latency_ms < 500:
            return "C"
        elif latency_ms < 1000:
            return "D"
        elif latency_ms >= 9999:
            return "F"
        else:
            return "E"

    def test(self, proxy_id: str, simulated_latency_ms: float = 0.0) -> LatencyTest:
        """Test proxy latency (simulated or measured)."""
        if simulated_latency_ms <= 0:
            # Simulate latency based on proxy ID hash
            base = 50 + (hash(proxy_id) % 800)
            simulated_latency_ms = float(base)

        # Simulate jitter
        jitter = simulated_latency_ms * 0.15 * (hash(proxy_id + "jitter") % 100) / 100.0
        throughput = max(10, 1000 - simulated_latency_ms * 0.5)
        packet_loss = 0.0 if simulated_latency_ms < 500 else 0.02

        test = LatencyTest(
            test_id=f"lat_{proxy_id}_{int(time.time() * 1000)}",
            proxy_id=proxy_id,
            timestamp=time.time(),
            latency_ms=round(simulated_latency_ms, 2),
            throughput_kbps=round(throughput, 2),
            jitter_ms=round(jitter, 2),
            packet_loss=round(packet_loss, 4),
            grade=self._grade(simulated_latency_ms),
        )
        self.tests.append(test)
        self._save_state()
        return test

    def test_batch(self, proxy_ids: List[str]) -> List[LatencyTest]:
        return [self.test(pid) for pid in proxy_ids]

    def get_average_latency(self, proxy_id: str) -> float:
        proxy_tests = [t.latency_ms for t in self.tests if t.proxy_id == proxy_id]
        if not proxy_tests:
            return 0.0
        return round(sum(proxy_tests) / len(proxy_tests), 2)

    def get_best_proxies(self, grade_threshold: str = "B", limit: int = 10) -> List[Dict]:
        grade_order = {"A+": 0, "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6}
        threshold_idx = grade_order.get(grade_threshold, 2)
        latest = {}
        for t in self.tests:
            if t.proxy_id not in latest or t.timestamp > latest[t.proxy_id].timestamp:
                latest[t.proxy_id] = t
        filtered = [t for t in latest.values() if grade_order.get(t.grade, 99) <= threshold_idx]
        filtered.sort(key=lambda t: t.latency_ms)
        return [t.to_dict() for t in filtered[:limit]]

    def get_stats(self) -> Dict:
        if not self.tests:
            return {"tests_total": 0}
        avg_latency = sum(t.latency_ms for t in self.tests) / len(self.tests)
        grades = {}
        for t in self.tests:
            grades[t.grade] = grades.get(t.grade, 0) + 1
        return {
            "tests_total": len(self.tests),
            "avg_latency_ms": round(avg_latency, 2),
            "grade_distribution": grades,
        }

    def to_dict(self) -> Dict:
        return {
            "tests": [t.to_dict() for t in self.tests[-200:]],
            "stats": self.get_stats(),
        }


__all__ = ["ProxyLatencyTester", "LatencyTest"]
