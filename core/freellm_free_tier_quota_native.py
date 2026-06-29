"""Free LLM Free Tier Quota -- Track daily/weekly/monthly quota consumption."""
from dataclasses import dataclass
from pathlib import Path
import json, time

@dataclass
class QuotaEntry:
    provider_id: str = ""
    model_id: str = ""
    daily_limit: int = 0
    weekly_limit: int = 0
    monthly_limit: int = 0
    used_today: int = 0
    used_this_week: int = 0
    used_this_month: int = 0
    window_day: float = 0.0
    window_week: float = 0.0
    window_month: float = 0.0

class FreellmFreeTierQuota:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._quotas: dict[str, QuotaEntry] = {}
        self._persist_path = self.root / "freellm_quota.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._quotas = {k: QuotaEntry(**v) for k, v in data.get("quotas", {}).items()}

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "quotas": {k: v.__dict__ for k, v in self._quotas.items()}
        }, indent=2))

    def _key(self, provider: str, model: str) -> str:
        return provider + ":" + model

    def _reset_windows(self, q: QuotaEntry) -> None:
        now = time.time()
        if now - q.window_day >= 86400:
            q.used_today = 0
            q.window_day = now
        if now - q.window_week >= 604800:
            q.used_this_week = 0
            q.window_week = now
        if now - q.window_month >= 2592000:
            q.used_this_month = 0
            q.window_month = now

    def set_quota(self, provider: str, model: str, daily: int, weekly: int, monthly: int) -> QuotaEntry:
        key = self._key(provider, model)
        q = self._quotas.get(key)
        if not q:
            q = QuotaEntry(provider_id=provider, model_id=model, window_day=time.time(), window_week=time.time(), window_month=time.time())
            self._quotas[key] = q
        q.daily_limit = daily
        q.weekly_limit = weekly
        q.monthly_limit = monthly
        self._save()
        return q

    def consume(self, provider: str, model: str, amount: int = 1) -> dict:
        key = self._key(provider, model)
        q = self._quotas.get(key)
        if not q:
            return {"allowed": True, "remaining": "unlimited", "reason": "no quota set"}
        self._reset_windows(q)
        q.used_today += amount
        q.used_this_week += amount
        q.used_this_month += amount
        self._save()
        return {
            "allowed": q.used_today <= q.daily_limit and q.used_this_week <= q.weekly_limit and q.used_this_month <= q.monthly_limit,
            "daily_remaining": max(0, q.daily_limit - q.used_today),
            "weekly_remaining": max(0, q.weekly_limit - q.used_this_week),
            "monthly_remaining": max(0, q.monthly_limit - q.used_this_month)
        }

    def get_remaining(self, provider: str, model: str) -> dict:
        key = self._key(provider, model)
        q = self._quotas.get(key)
        if not q:
            return {"daily": "unlimited", "weekly": "unlimited", "monthly": "unlimited"}
        self._reset_windows(q)
        return {
            "daily": max(0, q.daily_limit - q.used_today),
            "weekly": max(0, q.weekly_limit - q.used_this_week),
            "monthly": max(0, q.monthly_limit - q.used_this_month)
        }

    def to_dict(self) -> dict:
        return {"quota_count": len(self._quotas)}

    def get_stats(self) -> dict:
        by_provider = {}
        for q in self._quotas.values():
            by_provider[q.provider_id] = by_provider.get(q.provider_id, 0) + 1
        return {"quotas": len(self._quotas), "by_provider": by_provider}

__all__ = ["FreellmFreeTierQuota", "QuotaEntry"]
