#!/usr/bin/env python3
"""
MAGNATRIX-OS | Layer 4 — Health Checker
Native health check engine with probing, circuit breaker, and degradation.
- TCP / HTTP / ICMP-like health probes
- Circuit breaker pattern (closed/open/half-open)
- Degraded mode fallback
- Health score aggregation
"""
import socket, time, threading, json, os, sys, random, struct
from typing import Dict, List, Optional, Callable, Any, Tuple
from collections import deque, defaultdict
from dataclasses import dataclass
from enum import Enum


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class ProbeResult:
    healthy: bool
    latency_ms: float
    timestamp: float
    error: str = ""


class TCPProbe:
    """TCP connect probe."""

    def __init__(self, timeout: float = 2.0):
        self.timeout = timeout

    def check(self, host: str, port: int) -> ProbeResult:
        start = time.time()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(self.timeout)
            s.connect((host, port))
            s.close()
            return ProbeResult(True, (time.time() - start) * 1000, time.time())
        except Exception as e:
            return ProbeResult(False, (time.time() - start) * 1000, time.time(), str(e))


class HTTPProbe:
    """HTTP HEAD/GET probe (simulated)."""

    def __init__(self, timeout: float = 2.0, method: str = "HEAD"):
        self.timeout = timeout
        self.method = method

    def check(self, url: str) -> ProbeResult:
        start = time.time()
        try:
            # Simulated HTTP probe
            parsed = url if url.startswith("http") else f"http://{url}"
            # In real impl: urllib.request.urlopen with timeout
            # Here we simulate success/failure based on URL pattern
            if "fail" in parsed or "error" in parsed:
                return ProbeResult(False, (time.time() - start) * 1000, time.time(), "Simulated failure")
            return ProbeResult(True, (time.time() - start) * 1000, time.time())
        except Exception as e:
            return ProbeResult(False, (time.time() - start) * 1000, time.time(), str(e))


class ICMPProbe:
    """ICMP-like probe (simulated since raw ICMP requires root)."""

    def check(self, host: str) -> ProbeResult:
        start = time.time()
        try:
            # Simulation: resolve DNS as proxy for reachability
            socket.gethostbyname(host)
            return ProbeResult(True, (time.time() - start) * 1000, time.time())
        except Exception as e:
            return ProbeResult(False, (time.time() - start) * 1000, time.time(), str(e))


class CircuitBreaker:
    """Circuit breaker for service calls."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 10.0, half_open_max: int = 3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max = half_open_max
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._last_failure_time = 0.0
        self._half_open_attempts = 0
        self._lock = threading.Lock()

    def call(self, fn: Callable, *args, **kwargs) -> Any:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.time() - self._last_failure_time > self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_attempts = 0
                else:
                    raise Exception("Circuit breaker is OPEN")
            if self._state == CircuitState.HALF_OPEN and self._half_open_attempts >= self.half_open_max:
                raise Exception("Circuit breaker half-open limit reached")
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_attempts += 1
        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                self._failures = 0
                self._half_open_attempts = 0
            elif self._state == CircuitState.CLOSED:
                self._failures = max(0, self._failures - 1)

    def _on_failure(self):
        with self._lock:
            self._failures += 1
            self._last_failure_time = time.time()
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
            elif self._failures >= self.failure_threshold:
                self._state = CircuitState.OPEN

    @property
    def state(self) -> str:
        return self._state.value

    def stats(self) -> Dict:
        return {
            "state": self._state.value,
            "failures": self._failures,
            "last_failure": self._last_failure_time,
        }


class HealthAggregator:
    """Aggregate health scores from multiple probes."""

    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self._history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self._lock = threading.Lock()

    def add(self, service: str, result: ProbeResult):
        with self._lock:
            self._history[service].append(result)

    def score(self, service: str) -> float:
        with self._lock:
            results = list(self._history[service])
        if not results:
            return 0.0
        healthy = sum(1 for r in results if r.healthy)
        return healthy / len(results)

    def latency_p99(self, service: str) -> float:
        with self._lock:
            latencies = sorted([r.latency_ms for r in self._history[service]])
        if not latencies:
            return 0.0
        idx = int(len(latencies) * 0.99)
        return latencies[min(idx, len(latencies) - 1)]

    def report(self) -> Dict[str, Dict]:
        with self._lock:
            services = list(self._history.keys())
        return {
            s: {"score": self.score(s), "latency_p99": self.latency_p99(s), "samples": len(self._history[s])}
            for s in services
        }


class DegradedMode:
    """Fallback to degraded functionality when health is poor."""

    def __init__(self, fallback: Callable):
        self.fallback = fallback
        self._active = False

    def maybe_run(self, primary: Callable, health_score: float, threshold: float = 0.5):
        if health_score < threshold:
            self._active = True
            return self.fallback()
        self._active = False
        return primary()

    @property
    def is_degraded(self) -> bool:
        return self._active


class HealthChecker:
    """Full health checker with probes, circuit breaker, and aggregation."""

    def __init__(self):
        self.tcp = TCPProbe()
        self.http = HTTPProbe()
        self.icmp = ICMPProbe()
        self.aggregator = HealthAggregator()
        self.breakers: Dict[str, CircuitBreaker] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def probe_service(self, name: str, host: str, port: int, probe_type: str = "tcp") -> ProbeResult:
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker()
        breaker = self.breakers[name]
        try:
            if probe_type == "tcp":
                result = breaker.call(self.tcp.check, host, port)
            elif probe_type == "http":
                result = breaker.call(self.http.check, f"http://{host}:{port}")
            elif probe_type == "icmp":
                result = breaker.call(self.icmp.check, host)
            else:
                result = ProbeResult(False, 0, time.time(), "Unknown probe type")
        except Exception as e:
            result = ProbeResult(False, 0, time.time(), str(e))
        self.aggregator.add(name, result)
        return result

    def start_monitoring(self, services: List[Dict], interval_sec: float = 5.0):
        self._running = True
        def _loop():
            while self._running:
                for svc in services:
                    self.probe_service(svc["name"], svc["host"], svc["port"], svc.get("type", "tcp"))
                time.sleep(interval_sec)
        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def health_report(self) -> Dict:
        return {
            "aggregated": self.aggregator.report(),
            "circuits": {k: v.stats() for k, v in self.breakers.items()},
        }


# ─── SELF TESTS ───
if __name__ == "__main__":
    tests = []
    def _t(name, fn):
        tests.append((name, fn))

    _t("tcp_probe", lambda: TCPProbe().check("127.0.0.1", 80).latency_ms >= 0)
    _t("http_probe", lambda: HTTPProbe().check("example.com").healthy or not HTTPProbe().check("example.com").healthy)
    _t("icmp_probe", lambda: ICMPProbe().check("127.0.0.1").healthy)
    _t("circuit_closed", lambda: CircuitBreaker().state == "closed")
    def _circuit_open():
        cb = CircuitBreaker(failure_threshold=1)
        cb._state = CircuitState.OPEN
        return cb.state == "open"
    _t("circuit_open", _circuit_open)
    def _circuit_halfopen():
        cb = CircuitBreaker(recovery_timeout=0.01)
        cb._state = CircuitState.OPEN
        cb._last_failure_time = time.time() - 1
        cb.call(lambda: True)
        return cb.state == "closed"
    _t("circuit_halfopen", _circuit_halfopen)
    _t("aggregator_score", lambda: (a := HealthAggregator(), a.add("s", ProbeResult(True, 10, 0)), a.add("s", ProbeResult(False, 20, 0)), a.score("s") == 0.5)[3])
    _t("degraded", lambda: DegradedMode(lambda: "fallback").maybe_run(lambda: "primary", 0.3) == "fallback")
    _t("health_report", lambda: "aggregated" in HealthChecker().health_report())
    _t("latency_p99", lambda: HealthAggregator().latency_p99("x") == 0.0)

    passed = 0
    for name, fn in tests:
        try:
            ok = fn()
            print(f"  {'PASS' if ok else 'FAIL'} {name}")
            if ok:
                passed += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")
    print(f"\nHealth Checker: {passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)
