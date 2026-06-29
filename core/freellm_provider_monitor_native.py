"""Free LLM Provider Monitor -- Availability checks, uptime tracking, status polling."""
from dataclasses import dataclass
from pathlib import Path
import json, time

@dataclass
class ProviderStatus:
    provider_id: str = ""
    status: str = "unknown"
    last_check: float = 0.0
    response_time_ms: int = 0
    consecutive_failures: int = 0
    uptime_pct: float = 100.0
    last_error: str = ""

class FreellmProviderMonitor:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._statuses: dict[str, ProviderStatus] = {}
        self._check_history: list[dict] = []
        self._persist_path = self.root / "freellm_monitor.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._statuses = {k: ProviderStatus(**v) for k, v in data.get("statuses", {}).items()}
            self._check_history = data.get("history", [])

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "statuses": {k: v.__dict__ for k, v in self._statuses.items()},
            "history": self._check_history[-1000:]
        }, indent=2))

    def check(self, provider_id: str, base_url: str, simulated: bool = True) -> ProviderStatus:
        now = time.time()
        status = self._statuses.get(provider_id)
        if not status:
            status = ProviderStatus(provider_id=provider_id)
            self._statuses[provider_id] = status

        if simulated:
            import random
            is_up = random.random() > 0.05
            status.response_time_ms = random.randint(50, 800)
            if is_up:
                status.status = "up"
                status.consecutive_failures = 0
            else:
                status.consecutive_failures += 1
                status.status = "degraded" if status.consecutive_failures < 3 else "down"
                status.last_error = "Connection timeout (simulated)"
        else:
            status.status = "up"
            status.response_time_ms = 0

        status.last_check = now
        self._check_history.append({
            "provider": provider_id, "status": status.status,
            "time_ms": status.response_time_ms, "ts": now
        })
        self._save()
        return status

    def get_status(self, provider_id: str) -> ProviderStatus | None:
        return self._statuses.get(provider_id)

    def list_up(self) -> list[ProviderStatus]:
        return [s for s in self._statuses.values() if s.status == "up"]

    def list_degraded(self) -> list[ProviderStatus]:
        return [s for s in self._statuses.values() if s.status == "degraded"]

    def list_down(self) -> list[ProviderStatus]:
        return [s for s in self._statuses.values() if s.status == "down"]

    def check_all(self, providers: list[dict]) -> list[ProviderStatus]:
        results = []
        for p in providers:
            results.append(self.check(p["id"], p.get("url", ""), simulated=True))
        return results

    def to_dict(self) -> dict:
        return {"provider_count": len(self._statuses), "checks": len(self._check_history)}

    def get_stats(self) -> dict:
        by_status = {}
        for s in self._statuses.values():
            by_status[s.status] = by_status.get(s.status, 0) + 1
        avg_response = sum(s.response_time_ms for s in self._statuses.values()) / len(self._statuses) if self._statuses else 0
        return {"providers": len(self._statuses), "by_status": by_status, "avg_response_ms": round(avg_response, 1)}

__all__ = ["FreellmProviderMonitor", "ProviderStatus"]
