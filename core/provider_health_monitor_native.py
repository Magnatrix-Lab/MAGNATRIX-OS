"""
provider_health_monitor_native.py
MAGNATRIX-OS — Provider Health Monitor

Inspired by OmniRoute: Monitor provider health, rate limits, and latency. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class HealthCheck:
    check_id: str
    provider: str
    status: str  # healthy, degraded, down
    latency_ms: float
    rate_limit_remaining: int
    rate_limit_total: int
    error_rate: float
    checked_at: str = ""

    def __post_init__(self):
        if not self.checked_at:
            self.checked_at = datetime.now().isoformat()


class ProviderHealthMonitor:
    """Monitor provider health, rate limits, and latency."""

    def __init__(self, cache_dir: str = "./provider_health"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.checks: Dict[str, List[HealthCheck]] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "checks.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for pid, clist in data.items():
                        self.checks[pid] = [HealthCheck(**c) for c in clist]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "checks.json", "w", encoding="utf-8") as f:
            json.dump({pid: [asdict(c) for c in clist] for pid, clist in self.checks.items()}, f, indent=2)

    def check(self, check_id: str, provider: str, latency_ms: float,
              rate_limit_remaining: int, rate_limit_total: int, error_rate: float = 0.0) -> HealthCheck:
        status = "healthy"
        if latency_ms > 5000 or error_rate > 0.1:
            status = "down"
        elif latency_ms > 1000 or error_rate > 0.05 or rate_limit_remaining < rate_limit_total * 0.1:
            status = "degraded"

        check = HealthCheck(
            check_id=check_id, provider=provider, status=status, latency_ms=latency_ms,
            rate_limit_remaining=rate_limit_remaining, rate_limit_total=rate_limit_total,
            error_rate=error_rate,
        )
        self.checks.setdefault(provider, []).append(check)
        # Keep last 100 checks per provider
        self.checks[provider] = self.checks[provider][-100:]
        self._save()
        return check

    def get_status(self, provider: str) -> str:
        checks = self.checks.get(provider, [])
        if not checks:
            return "unknown"
        return checks[-1].status

    def get_healthy_providers(self) -> List[str]:
        return [p for p, checks in self.checks.items() if checks and checks[-1].status == "healthy"]

    def get_stats(self) -> Dict[str, Any]:
        total_checks = sum(len(c) for c in self.checks.values())
        healthy = len(self.get_healthy_providers())
        return {"total_checks": total_checks, "providers": len(self.checks), "healthy": healthy}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["ProviderHealthMonitor", "HealthCheck"]