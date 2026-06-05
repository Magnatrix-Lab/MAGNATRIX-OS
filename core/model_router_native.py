"""
Model Router — MAGNATRIX-OS Core
Load balancer untuk LLM API calls dengan fallback, rate limit, circuit breaker.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from __future__ import annotations

import time, json, urllib.request, urllib.error
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Callable


class ModelProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MISTRAL = "mistral"
    COHERE = "cohere"
    LOCAL = "local"
    CUSTOM = "custom"


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class EndpointConfig:
    """Configuration for single LLM endpoint."""
    provider: ModelProvider
    base_url: str
    api_key: str = ""
    model_name: str = "default"
    timeout_seconds: float = 30.0
    max_retries: int = 3
    weight: float = 1.0  # Load balancing weight
    rate_limit_rpm: int = 60  # Requests per minute
    circuit_breaker_threshold: int = 5  # Failures before opening
    circuit_breaker_timeout: float = 60.0  # Seconds before half-open


@dataclass
class EndpointStatus:
    """Runtime status of an endpoint."""
    endpoint_id: str
    state: CircuitState
    consecutive_failures: int = 0
    last_failure_time: float = 0.0
    total_requests: int = 0
    successful_requests: int = 0
    avg_latency_ms: float = 0.0
    last_used: float = 0.0


class ModelRouter:
    """
    Router untuk LLM API calls dengan:
    - Round-robin load balancing (weighted)
    - Automatic fallback ke endpoint lain
    - Rate limiting per endpoint
    - Circuit breaker pattern
    - Latency tracking
    """

    def __init__(self) -> None:
        self._endpoints: Dict[str, EndpointConfig] = {}
        self._status: Dict[str, EndpointStatus] = {}
        self._request_counts: Dict[str, List[float]] = {}  # Timestamps for rate limiting
        self._current_index = 0

    def add_endpoint(self, endpoint_id: str, config: EndpointConfig) -> None:
        self._endpoints[endpoint_id] = config
        self._status[endpoint_id] = EndpointStatus(endpoint_id, CircuitState.CLOSED)
        self._request_counts[endpoint_id] = []

    def remove_endpoint(self, endpoint_id: str) -> bool:
        return self._endpoints.pop(endpoint_id, None) is not None

    def route(self, prompt: str, model_prefs: Optional[List[str]] = None) -> Dict[str, Any]:
        """Route a prompt to the best available endpoint."""
        available = self._get_available_endpoints()
        if not available:
            return {"error": "No available endpoints", "status": "failed"}

        # Filter by model preference if specified
        if model_prefs:
            available = [e for e in available if self._endpoints[e].model_name in model_prefs]
        if not available:
            available = self._get_available_endpoints()

        # Weighted round-robin
        selected = self._weighted_select(available)

        # Check rate limit
        if self._is_rate_limited(selected):
            # Try fallback
            fallback = [e for e in available if e != selected and not self._is_rate_limited(e)]
            if fallback:
                selected = fallback[0]
            else:
                return {"error": "All endpoints rate limited", "status": "failed"}

        # Execute
        return self._call_endpoint(selected, prompt)

    def _get_available_endpoints(self) -> List[str]:
        """Get endpoints that are not in OPEN circuit state."""
        available = []
        now = time.time()
        for eid, status in self._status.items():
            if status.state == CircuitState.CLOSED:
                available.append(eid)
            elif status.state == CircuitState.OPEN:
                if now - status.last_failure_time > self._endpoints[eid].circuit_breaker_timeout:
                    status.state = CircuitState.HALF_OPEN
                    available.append(eid)
            elif status.state == CircuitState.HALF_OPEN:
                available.append(eid)
        return available

    def _weighted_select(self, endpoints: List[str]) -> str:
        """Weighted round-robin selection."""
        if not endpoints:
            return ""
        weights = [self._endpoints[e].weight for e in endpoints]
        total = sum(weights)
        if total == 0:
            return endpoints[self._current_index % len(endpoints)]
        # Simple weighted random would be better, but for determinism:
        self._current_index = (self._current_index + 1) % len(endpoints)
        return endpoints[self._current_index]

    def _is_rate_limited(self, endpoint_id: str) -> bool:
        """Check if endpoint is rate limited."""
        config = self._endpoints[endpoint_id]
        now = time.time()
        window = 60.0  # 1 minute
        self._request_counts[endpoint_id] = [t for t in self._request_counts[endpoint_id] if now - t < window]
        return len(self._request_counts[endpoint_id]) >= config.rate_limit_rpm

    def _call_endpoint(self, endpoint_id: str, prompt: str) -> Dict[str, Any]:
        """Call endpoint and track metrics."""
        start = time.time()
        config = self._endpoints[endpoint_id]
        status = self._status[endpoint_id]

        self._request_counts[endpoint_id].append(start)
        status.total_requests += 1
        status.last_used = start

        try:
            # Simulate API call (replace with real HTTP call in production)
            result = self._simulate_call(config, prompt)
            latency = (time.time() - start) * 1000
            status.avg_latency_ms = (status.avg_latency_ms * (status.total_requests - 1) + latency) / status.total_requests
            status.successful_requests += 1
            status.consecutive_failures = 0
            if status.state == CircuitState.HALF_OPEN:
                status.state = CircuitState.CLOSED
            return {"endpoint": endpoint_id, "result": result, "latency_ms": latency, "status": "success"}
        except Exception as e:
            status.consecutive_failures += 1
            status.last_failure_time = time.time()
            if status.consecutive_failures >= config.circuit_breaker_threshold:
                status.state = CircuitState.OPEN
            return {"error": str(e), "endpoint": endpoint_id, "status": "failed", "fallback_available": len(self._get_available_endpoints()) > 1}

    def _simulate_call(self, config: EndpointConfig, prompt: str) -> str:
        """Simulate LLM call. Replace with real implementation."""
        # Real implementation would use urllib.request to call the API
        return f"[Response from {config.provider.value}/{config.model_name}]"

    def get_health(self) -> Dict[str, Any]:
        return {eid: {"state": s.state.value, "success_rate": s.successful_requests / max(s.total_requests, 1), "avg_latency_ms": s.avg_latency_ms} for eid, s in self._status.items()}

    def stats(self) -> Dict[str, Any]:
        return {
            "endpoints": len(self._endpoints),
            "available": len(self._get_available_endpoints()),
            "open_circuits": len([s for s in self._status.values() if s.state == CircuitState.OPEN]),
            "total_requests": sum(s.total_requests for s in self._status.values()),
        }


def run():
    print("=" * 60)
    print("Model Router — Demo")
    print("=" * 60)

    router = ModelRouter()

    print("\n[1] Add endpoints")
    router.add_endpoint("ep1", EndpointConfig(ModelProvider.OPENAI, "https://api.openai.com", model_name="gpt-4", weight=2.0))
    router.add_endpoint("ep2", EndpointConfig(ModelProvider.ANTHROPIC, "https://api.anthropic.com", model_name="claude-3", weight=1.0))
    router.add_endpoint("ep3", EndpointConfig(ModelProvider.LOCAL, "http://localhost:8000", model_name="llama-3", weight=3.0))
    print(f"   Endpoints: {router.stats()}")

    print("\n[2] Route prompts")
    for i in range(5):
        result = router.route("Hello, calculate BMI for 70kg, 175cm")
        print(f"   Call {i+1}: {result.get('endpoint', 'N/A')} — {result.get('status', 'N/A')}")

    print("\n[3] Health check")
    print(f"   {router.get_health()}")

    print(f"\n[4] Stats: {router.stats()}")
    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
