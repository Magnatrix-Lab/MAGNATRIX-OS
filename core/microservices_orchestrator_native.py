"""
microservices_orchestrator_native.py
MAGNATRIX-OS — Microservices Orchestrator

Inspired by donnemartin/system-design-primer microservices patterns:
Service discovery, circuit breaker, rate limiting, health checks. Pure stdlib.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class Service:
    service_id: str
    name: str
    version: str
    endpoint: str
    is_healthy: bool = True
    last_check: float = 0.0
    failure_count: int = 0
    circuit_state: str = "closed"  # closed, open, half-open


class MicroservicesOrchestrator:
    """Orchestrate microservices with discovery, circuit breaker, rate limiting."""

    def __init__(self, data_dir: str = "./microservices"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.services: Dict[str, Service] = {}
        self.rate_limits: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        for fname in ["services.json", "rate_limits.json"]:
            f = self.data_dir / fname
            if f.exists():
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        if fname == "services.json":
                            self.services = {k: Service(**v) for k, v in data.items()}
                        else:
                            self.rate_limits = data
                except Exception:
                    pass

    def _save(self) -> None:
        with open(self.data_dir / "services.json", "w", encoding="utf-8") as f:
            json.dump({k: asdict(v) for k, v in self.services.items()}, f, indent=2)
        with open(self.data_dir / "rate_limits.json", "w", encoding="utf-8") as f:
            json.dump(self.rate_limits, f, indent=2)

    def register(self, service_id: str, name: str, version: str, endpoint: str) -> Service:
        svc = Service(service_id=service_id, name=name, version=version, endpoint=endpoint)
        self.services[service_id] = svc
        self._save()
        return svc

    def deregister(self, service_id: str) -> bool:
        if service_id in self.services:
            del self.services[service_id]
            self._save()
            return True
        return False

    def discover(self, name: str) -> List[Service]:
        return [s for s in self.services.values() if s.name == name and s.is_healthy]

    def health_check(self, service_id: str, is_healthy: bool) -> bool:
        svc = self.services.get(service_id)
        if not svc:
            return False
        svc.is_healthy = is_healthy
        svc.last_check = time.time()
        if not is_healthy:
            svc.failure_count += 1
            if svc.failure_count >= 5:
                svc.circuit_state = "open"
        else:
            svc.failure_count = 0
            if svc.circuit_state == "open":
                svc.circuit_state = "half-open"
            elif svc.circuit_state == "half-open":
                svc.circuit_state = "closed"
        self._save()
        return True

    def set_rate_limit(self, service_id: str, max_requests: int, window_seconds: int) -> None:
        self.rate_limits[service_id] = {"max": max_requests, "window": window_seconds, "requests": []}
        self._save()

    def check_rate_limit(self, service_id: str) -> bool:
        rl = self.rate_limits.get(service_id, {})
        if not rl:
            return True
        now = time.time()
        window = rl["window"]
        rl["requests"] = [t for t in rl.get("requests", []) if now - t < window]
        if len(rl["requests"]) >= rl["max"]:
            return False
        rl["requests"].append(now)
        self._save()
        return True

    def get_stats(self) -> Dict[str, Any]:
        healthy = sum(1 for s in self.services.values() if s.is_healthy)
        open_circuits = sum(1 for s in self.services.values() if s.circuit_state == "open")
        return {"services": len(self.services), "healthy": healthy, "open_circuits": open_circuits}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["MicroservicesOrchestrator", "Service"]