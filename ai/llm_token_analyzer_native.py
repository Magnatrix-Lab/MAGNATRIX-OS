"""Token Usage Analyzer — Track token consumption, projections, alerts, quota management.

Modul ini menyediakan:
- TokenCounter: estimate token usage for text
- UsageTracker: track per-request, per-model, per-user token usage
- QuotaManager: enforce usage limits and quotas
- UsageProjector: project future usage based on trends
- UsageAlert: configurable alerts for thresholds
- TokenAnalyzer: end-to-end token analysis pipeline
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class AlertLevel(Enum):
    INFO = auto()
    WARNING = auto()
    CRITICAL = auto()


@dataclass
class TokenUsage:
    """Token usage for a single request."""
    usage_id: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int = 0
    model_id: str = ""
    user_id: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.total_tokens == 0:
            self.total_tokens = self.prompt_tokens + self.completion_tokens


@dataclass
class UsageAlert:
    """Alert triggered by usage thresholds."""
    alert_id: str
    level: AlertLevel
    message: str
    threshold: float
    current: float
    timestamp: float = field(default_factory=time.time)


class TokenCounter:
    """Estimate token count from text (simplified)."""

    # Rough approximation: 1 token ~ 0.75 words for English
    TOKEN_RATIO = 0.75

    @staticmethod
    def count(text: str) -> int:
        words = len(text.split())
        return int(words / TokenCounter.TOKEN_RATIO)

    @staticmethod
    def count_messages(messages: List[Dict[str, str]]) -> int:
        total = 0
        for msg in messages:
            total += TokenCounter.count(msg.get("content", ""))
        return total


class UsageTracker:
    """Track token usage across dimensions."""

    def __init__(self):
        self._records: List[TokenUsage] = []
        self._by_model: Dict[str, List[TokenUsage]] = {}
        self._by_user: Dict[str, List[TokenUsage]] = {}
        self._by_time: Dict[str, int] = {}  # hour -> total tokens

    def record(self, usage: TokenUsage) -> None:
        self._records.append(usage)
        self._by_model.setdefault(usage.model_id, []).append(usage)
        self._by_user.setdefault(usage.user_id, []).append(usage)
        hour_key = time.strftime("%Y-%m-%d-%H", time.localtime(usage.timestamp))
        self._by_time[hour_key] = self._by_time.get(hour_key, 0) + usage.total_tokens

    def get_total(self, model_id: Optional[str] = None, user_id: Optional[str] = None) -> int:
        records = self._records
        if model_id:
            records = [r for r in records if r.model_id == model_id]
        if user_id:
            records = [r for r in records if r.user_id == user_id]
        return sum(r.total_tokens for r in records)

    def get_stats(self) -> Dict[str, Any]:
        if not self._records:
            return {"total": 0, "avg_per_request": 0, "requests": 0}
        return {
            "total_tokens": sum(r.total_tokens for r in self._records),
            "prompt_tokens": sum(r.prompt_tokens for r in self._records),
            "completion_tokens": sum(r.completion_tokens for r in self._records),
            "requests": len(self._records),
            "avg_per_request": round(sum(r.total_tokens for r in self._records) / len(self._records), 2),
            "models": {k: {"requests": len(v), "tokens": sum(r.total_tokens for r in v)}
                        for k, v in self._by_model.items()},
            "users": {k: {"requests": len(v), "tokens": sum(r.total_tokens for r in v)}
                       for k, v in self._by_user.items()}
        }

    def get_hourly_usage(self, hours: int = 24) -> List[Tuple[str, int]]:
        """Get hourly usage for last N hours."""
        now = time.time()
        result = []
        for i in range(hours):
            ts = now - i * 3600
            key = time.strftime("%Y-%m-%d-%H", time.localtime(ts))
            result.append((key, self._by_time.get(key, 0)))
        return result


class QuotaManager:
    """Enforce usage limits and quotas."""

    def __init__(self):
        self._quotas: Dict[str, Dict[str, Any]] = {}  # user_id -> quota config
        self._usage: Dict[str, int] = {}  # user_id -> used tokens

    def set_quota(self, user_id: str, max_tokens: int, reset_interval: str = "daily") -> None:
        self._quotas[user_id] = {
            "max_tokens": max_tokens,
            "reset_interval": reset_interval,
            "set_at": time.time()
        }
        self._usage[user_id] = 0

    def check(self, user_id: str, requested_tokens: int) -> Tuple[bool, int, int]:
        """Returns (allowed, remaining, used)."""
        quota = self._quotas.get(user_id)
        if not quota:
            return True, -1, 0
        used = self._usage.get(user_id, 0)
        remaining = quota["max_tokens"] - used
        allowed = requested_tokens <= remaining
        return allowed, remaining, used

    def consume(self, user_id: str, tokens: int) -> bool:
        allowed, remaining, _ = self.check(user_id, tokens)
        if allowed:
            self._usage[user_id] = self._usage.get(user_id, 0) + tokens
            return True
        return False

    def get_quota(self, user_id: str) -> Dict[str, Any]:
        quota = self._quotas.get(user_id, {})
        used = self._usage.get(user_id, 0)
        return {
            "max": quota.get("max_tokens", 0),
            "used": used,
            "remaining": quota.get("max_tokens", 0) - used,
            "reset_interval": quota.get("reset_interval", "")
        }


class UsageProjector:
    """Project future usage based on trends."""

    def __init__(self, tracker: UsageTracker):
        self.tracker = tracker

    def project_daily(self, days: int = 7) -> List[Tuple[str, int]]:
        """Project daily usage for next N days."""
        hourly = self.tracker.get_hourly_usage(24)
        avg_hourly = sum(t for _, t in hourly) / max(len(hourly), 1)
        daily_estimate = int(avg_hourly * 24)
        now = time.time()
        return [(time.strftime("%Y-%m-%d", time.localtime(now + i * 86400)), daily_estimate)
                for i in range(1, days + 1)]

    def project_cost(self, cost_per_1k: float = 0.01) -> Dict[str, float]:
        """Estimate cost based on current usage."""
        stats = self.tracker.get_stats()
        total = stats.get("total_tokens", 0)
        daily = total / max(len(self.tracker._records), 1) * 24  # rough daily
        return {
            "total_cost": round(total / 1000 * cost_per_1k, 4),
            "estimated_daily_cost": round(daily / 1000 * cost_per_1k, 4),
            "estimated_monthly_cost": round(daily / 1000 * cost_per_1k * 30, 4)
        }

    def get_trend(self, hours: int = 24) -> str:
        """Determine if usage is increasing, decreasing, or stable."""
        hourly = self.tracker.get_hourly_usage(hours)
        if len(hourly) < 2:
            return "insufficient_data"
        first_half = sum(t for _, t in hourly[:len(hourly)//2])
        second_half = sum(t for _, t in hourly[len(hourly)//2:])
        if second_half > first_half * 1.2:
            return "increasing"
        elif second_half < first_half * 0.8:
            return "decreasing"
        return "stable"


class AlertManager:
    """Manage usage alerts and thresholds."""

    def __init__(self):
        self._thresholds: Dict[str, List[Tuple[float, AlertLevel]]] = {}
        self._alerts: List[UsageAlert] = []
        self._callbacks: List[Callable[[UsageAlert], None]] = []

    def set_threshold(self, metric: str, value: float, level: AlertLevel) -> None:
        self._thresholds.setdefault(metric, []).append((value, level))
        self._thresholds[metric].sort()

    def check(self, metric: str, current_value: float) -> List[UsageAlert]:
        triggered = []
        for threshold, level in self._thresholds.get(metric, []):
            if current_value >= threshold:
                alert = UsageAlert(
                    alert_id=str(uuid.uuid4())[:12],
                    level=level,
                    message=f"{metric} exceeded {threshold} (current: {current_value})",
                    threshold=threshold,
                    current=current_value
                )
                self._alerts.append(alert)
                triggered.append(alert)
                for cb in self._callbacks:
                    cb(alert)
        return triggered

    def on_alert(self, callback: Callable[[UsageAlert], None]) -> None:
        self._callbacks.append(callback)

    def get_alerts(self, level: Optional[AlertLevel] = None) -> List[UsageAlert]:
        if level:
            return [a for a in self._alerts if a.level == level]
        return self._alerts

    def get_stats(self) -> Dict[str, Any]:
        return {
            "thresholds": {k: [(t, l.name) for t, l in v] for k, v in self._thresholds.items()},
            "total_alerts": len(self._alerts),
            "by_level": {
                "INFO": len([a for a in self._alerts if a.level == AlertLevel.INFO]),
                "WARNING": len([a for a in self._alerts if a.level == AlertLevel.WARNING]),
                "CRITICAL": len([a for a in self._alerts if a.level == AlertLevel.CRITICAL])
            }
        }


class TokenAnalyzer:
    """End-to-end token analysis pipeline."""

    def __init__(self):
        self.counter = TokenCounter()
        self.tracker = UsageTracker()
        self.quota = QuotaManager()
        self.projector = UsageProjector(self.tracker)
        self.alerts = AlertManager()
        self._setup_default_alerts()

    def _setup_default_alerts(self) -> None:
        self.alerts.set_threshold("total_tokens", 10000, AlertLevel.INFO)
        self.alerts.set_threshold("total_tokens", 50000, AlertLevel.WARNING)
        self.alerts.set_threshold("total_tokens", 100000, AlertLevel.CRITICAL)

    def analyze_request(self, prompt: str, completion: str, model_id: str = "", user_id: str = "") -> TokenUsage:
        prompt_tokens = self.counter.count(prompt)
        completion_tokens = self.counter.count(completion)
        usage = TokenUsage(
            usage_id=str(uuid.uuid4())[:12],
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model_id=model_id,
            user_id=user_id
        )
        self.tracker.record(usage)
        self.alerts.check("total_tokens", self.tracker.get_total())
        return usage

    def check_quota(self, user_id: str, prompt: str) -> Tuple[bool, int]:
        estimated = self.counter.count(prompt)
        allowed, remaining, _ = self.quota.check(user_id, estimated)
        return allowed, remaining

    def get_report(self) -> Dict[str, Any]:
        return {
            "usage": self.tracker.get_stats(),
            "projections": {
                "daily": self.projector.project_daily(7),
                "cost": self.projector.project_cost()
            },
            "trend": self.projector.get_trend(),
            "alerts": self.alerts.get_stats()
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.get_report(), f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("TOKEN USAGE ANALYZER DEMO")
    print("=" * 70)

    # 1. Token Counter
    print("\n[1] Token Counter")
    tc = TokenCounter()
    text = "The quick brown fox jumps over the lazy dog."
    print(f"  Text: '{text[:40]}...'")
    print(f"  Estimated tokens: {tc.count(text)}")
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "What is Python?"},
        {"role": "assistant", "content": "Python is a programming language."}
    ]
    print(f"  Messages tokens: {tc.count_messages(messages)}")

    # 2. Usage Tracker
    print("\n[2] Usage Tracker")
    tracker = UsageTracker()
    for i in range(20):
        tracker.record(TokenUsage(
            usage_id=f"u{i}",
            prompt_tokens=50 + i * 5,
            completion_tokens=30 + i * 3,
            model_id="gpt-4" if i % 2 == 0 else "claude-3",
            user_id=f"user-{i % 3}"
        ))
    print(f"  Stats: {tracker.get_stats()}")
    print(f"  Hourly (last 3): {tracker.get_hourly_usage(3)}")

    # 3. Quota Manager
    print("\n[3] Quota Manager")
    qm = QuotaManager()
    qm.set_quota("user-0", max_tokens=1000)
    allowed, remaining, used = qm.check("user-0", 500)
    print(f"  Check 500 tokens: allowed={allowed}, remaining={remaining}, used={used}")
    qm.consume("user-0", 500)
    allowed2, remaining2, used2 = qm.check("user-0", 600)
    print(f"  After 500 used, check 600: allowed={allowed2}, remaining={remaining2}, used={used2}")
    print(f"  Quota: {qm.get_quota('user-0')}")

    # 4. Usage Projector
    print("\n[4] Usage Projector")
    proj = UsageProjector(tracker)
    print(f"  Trend: {proj.get_trend(24)}")
    print(f"  Cost projection: {proj.project_cost(0.02)}")

    # 5. Alerts
    print("\n[5] Alert Manager")
    alerts = AlertManager()
    alerts.set_threshold("daily_tokens", 5000, AlertLevel.WARNING)
    alerts.set_threshold("daily_tokens", 10000, AlertLevel.CRITICAL)
    triggered = alerts.check("daily_tokens", 7500)
    print(f"  Triggered at 7500: {len(triggered)} alerts")
    for a in triggered:
        print(f"    {a.level.name}: {a.message}")
    print(f"  Stats: {alerts.get_stats()}")

    # 6. Full Analyzer
    print("\n[6] Full Token Analyzer")
    analyzer = TokenAnalyzer()
    for i in range(10):
        analyzer.analyze_request(
            prompt=f"Question {i}: How does feature {i} work?" * 5,
            completion=f"Answer {i}: Feature {i} works by..." * 3,
            model_id="gpt-4",
            user_id="user-0"
        )
    print(f"  Report: {analyzer.get_report()}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
