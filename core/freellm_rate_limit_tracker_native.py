"""Free LLM Rate Limit Tracker -- RPM/RPD monitoring, quota usage."""
from dataclasses import dataclass
from pathlib import Path
import json, time

@dataclass
class RateLimitUsage:
    provider_id: str = ""
    model_id: str = ""
    requests_this_minute: int = 0
    requests_this_day: int = 0
    tokens_this_minute: int = 0
    tokens_this_day: int = 0
    window_start_minute: float = 0.0
    window_start_day: float = 0.0

class FreellmRateLimitTracker:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._usage: dict[str, RateLimitUsage] = {}
        self._persist_path = self.root / "freellm_rate_limits.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._usage = {k: RateLimitUsage(**v) for k, v in data.get("usage", {}).items()}

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "usage": {k: v.__dict__ for k, v in self._usage.items()}
        }, indent=2))

    def _key(self, provider: str, model: str) -> str:
        return provider + ":" + model

    def _reset_window(self, usage: RateLimitUsage) -> None:
        now = time.time()
        if now - usage.window_start_minute >= 60:
            usage.requests_this_minute = 0
            usage.tokens_this_minute = 0
            usage.window_start_minute = now
        if now - usage.window_start_day >= 86400:
            usage.requests_this_day = 0
            usage.tokens_this_day = 0
            usage.window_start_day = now

    def record_request(self, provider: str, model: str, tokens: int = 0) -> RateLimitUsage:
        key = self._key(provider, model)
        usage = self._usage.get(key)
        if not usage:
            usage = RateLimitUsage(provider_id=provider, model_id=model, window_start_minute=time.time(), window_start_day=time.time())
            self._usage[key] = usage
        self._reset_window(usage)
        usage.requests_this_minute += 1
        usage.requests_this_day += 1
        usage.tokens_this_minute += tokens
        usage.tokens_this_day += tokens
        self._save()
        return usage

    def check_limit(self, provider: str, model: str, rpm_limit: int, rpd_limit: int) -> dict:
        key = self._key(provider, model)
        usage = self._usage.get(key)
        if not usage:
            return {"allowed": True, "rpm_remaining": rpm_limit, "rpd_remaining": rpd_limit}
        self._reset_window(usage)
        rpm_remaining = max(0, rpm_limit - usage.requests_this_minute)
        rpd_remaining = max(0, rpd_limit - usage.requests_this_day)
        return {
            "allowed": rpm_remaining > 0 and rpd_remaining > 0,
            "rpm_remaining": rpm_remaining,
            "rpd_remaining": rpd_remaining,
            "rpm_used": usage.requests_this_minute,
            "rpd_used": usage.requests_this_day
        }

    def get_usage(self, provider: str, model: str) -> RateLimitUsage | None:
        return self._usage.get(self._key(provider, model))

    def to_dict(self) -> dict:
        return {"tracked_models": len(self._usage)}

    def get_stats(self) -> dict:
        total_req = sum(u.requests_this_day for u in self._usage.values())
        total_tokens = sum(u.tokens_this_day for u in self._usage.values())
        return {"tracked": len(self._usage), "total_requests_today": total_req, "total_tokens_today": total_tokens}

__all__ = ["FreellmRateLimitTracker", "RateLimitUsage"]
