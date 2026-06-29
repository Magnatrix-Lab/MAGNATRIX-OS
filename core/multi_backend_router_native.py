
"""
multi_backend_router_native.py
MAGNATRIX-OS — Multi-Backend Router

Route requests across multiple backends with fallback, health checks,
and load balancing. Inspired by Agent-Reach v1.5.0 routing.
Pure Python standard library.
"""

import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto


class BackendStatus(Enum):
    HEALTHY = auto()
    DEGRADED = auto()
    UNHEALTHY = auto()
    UNKNOWN = auto()


@dataclass
class Backend:
    name: str
    url: str
    priority: int = 1
    weight: float = 1.0
    timeout: float = 10.0
    status: BackendStatus = BackendStatus.UNKNOWN
    last_check: float = 0.0
    response_time_ms: float = 0.0
    failure_count: int = 0
    success_count: int = 0


class MultiBackendRouter:
    """Route requests across multiple backends with health checking."""

    def __init__(self, max_failures: int = 3, check_interval: float = 30.0):
        self.backends: Dict[str, Backend] = {}
        self.max_failures = max_failures
        self.check_interval = check_interval
        self._route_history: List[Dict] = []

    def register(self, name: str, url: str, priority: int = 1, weight: float = 1.0) -> None:
        self.backends[name] = Backend(name=name, url=url, priority=priority, weight=weight)

    def check_health(self, name: str, probe_fn: Optional[Callable] = None) -> BackendStatus:
        """Check backend health via probe function."""
        backend = self.backends.get(name)
        if not backend:
            return BackendStatus.UNKNOWN
        if probe_fn:
            try:
                start = time.time()
                result = probe_fn(backend.url)
                backend.response_time_ms = (time.time() - start) * 1000
                backend.status = BackendStatus.HEALTHY if result else BackendStatus.UNHEALTHY
                if result:
                    backend.success_count += 1
                    backend.failure_count = 0
                else:
                    backend.failure_count += 1
            except Exception:
                backend.status = BackendStatus.UNHEALTHY
                backend.failure_count += 1
        backend.last_check = time.time()
        # Mark unhealthy if too many failures
        if backend.failure_count >= self.max_failures:
            backend.status = BackendStatus.UNHEALTHY
        return backend.status

    def check_all_health(self, probe_fn: Optional[Callable] = None) -> Dict[str, str]:
        return {name: self.check_health(name, probe_fn).name for name in self.backends}

    def select_backend(self, strategy: str = "priority") -> Optional[Backend]:
        """Select best backend using chosen strategy."""
        healthy = [b for b in self.backends.values() if b.status == BackendStatus.HEALTHY]
        if not healthy:
            # Fallback to degraded
            healthy = [b for b in self.backends.values() if b.status in (BackendStatus.HEALTHY, BackendStatus.DEGRADED)]
        if not healthy:
            return None
        if strategy == "priority":
            return min(healthy, key=lambda b: b.priority)
        elif strategy == "round_robin":
            # Simple round-robin via history
            if self._route_history:
                last = self._route_history[-1].get("backend")
                candidates = [b for b in healthy if b.name != last]
                if candidates:
                    return candidates[0]
            return healthy[0]
        elif strategy == "fastest":
            return min(healthy, key=lambda b: b.response_time_ms)
        elif strategy == "weighted":
            total_weight = sum(b.weight for b in healthy)
            import random
            r = random.uniform(0, total_weight)
            cumulative = 0.0
            for b in healthy:
                cumulative += b.weight
                if r <= cumulative:
                    return b
            return healthy[-1]
        return healthy[0]

    def route(self, request_fn: Callable, strategy: str = "priority") -> Any:
        """Route a request to the best available backend."""
        backend = self.select_backend(strategy)
        if not backend:
            raise Exception("No healthy backends available")
        self._route_history.append({
            "backend": backend.name, "timestamp": datetime.now().isoformat(),
            "strategy": strategy,
        })
        return request_fn(backend.url)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "backends": len(self.backends),
            "healthy": sum(1 for b in self.backends.values() if b.status == BackendStatus.HEALTHY),
            "unhealthy": sum(1 for b in self.backends.values() if b.status == BackendStatus.UNHEALTHY),
            "total_routes": len(self._route_history),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["MultiBackendRouter", "Backend", "BackendStatus"]
