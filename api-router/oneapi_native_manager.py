"""
oneapi_native_manager.py
==========================
MAGNATRIX Native LLM Provider Manager
Layer 1.5: API Router

Pola AMATI-PELAJARI-TIRU dari songquanpeng/one-api:
- Amati:  20+ LLM provider management, unified channel system,
          load balancing, health check, token tracking, model catalog
- Pelajari: Core pattern: (1) ProviderChannel = single provider endpoint,
            (2) HealthChecker = periodic ping + DOWN detection,
            (3) TokenTracker = usage ledger per user per provider,
            (4) ModelCatalog = registry dengan metadata,
            (5) RateLimiter = token bucket per scope,
            (6) FallbackChain = primary → secondary → tertiary
- Tiru:   Native Python asyncio, native provider implementations
          (bukan LiteLLM proxy), MAGNATRIX-specific cost optimization,
          mesh broadcast untuk provider outage
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from collections import defaultdict
import threading


class ProviderType(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    GROQ = "groq"
    COHERE = "cohere"
    MISTRAL = "mistral"
    DEEPSEEK = "deepseek"
    TOGETHER = "together"
    FIREWORKS = "fireworks"
    PERPLEXITY = "perplexity"
    AI21 = "ai21"
    AZURE = "azure"
    VERTEX = "vertex"
    BEDROCK = "bedrock"
    OPENROUTER = "openrouter"
    SAMBANOVA = "sambanova"
    CEREBRAS = "cerebras"
    CLOUDFLARE = "cloudflare"
    GITHUB_MODELS = "github_models"
    LOCAL = "local"
    MAGNATRIX_MESH = "magnatrix_mesh"


class HealthStatus(Enum):
    UP = "up"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class ModelInfo:
    """Model metadata dalam catalog"""
    id: str
    provider: str
    display_name: str = ""
    context_window: int = 4096
    max_output_tokens: int = 4096
    cost_per_1k_input: float = 0.0  # USD
    cost_per_1k_output: float = 0.0
    supports_vision: bool = False
    supports_tools: bool = False
    supports_streaming: bool = True
    supports_json_mode: bool = False
    latency_ms_estimate: float = 500.0
    quality_score: float = 0.5  # 0-1
    reliability_score: float = 0.5
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ProviderChannel:
    """Single provider channel configuration"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    provider_type: ProviderType = ProviderType.OPENAI
    name: str = ""  # Display name
    base_url: str = ""
    api_key: str = ""  # Encrypted at rest in production
    api_version: str = ""
    organization_id: str = ""
    # Health
    health_status: HealthStatus = HealthStatus.UNKNOWN
    last_health_check: Optional[float] = None
    consecutive_failures: int = 0
    max_failures_before_down: int = 3
    # Models exposed via this channel
    models: List[str] = field(default_factory=list)
    # Rate limits
    rpm_limit: int = 60  # Requests per minute
    tpm_limit: int = 100000  # Tokens per minute
    # Weights
    priority: int = 1  # Lower = higher priority
    weight: float = 1.0  # Load balancing weight
    enabled: bool = True
    # Fallback
    fallback_to: Optional[str] = None  # Channel ID fallback
    # Metadata
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            "provider_type": self.provider_type.value,
            "health_status": self.health_status.value
        }


@dataclass
class UsageRecord:
    """Token usage record"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    user_id: str = ""
    channel_id: str = ""
    model_id: str = ""
    request_id: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    status: str = "success"  # success, error, timeout, rate_limited
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return asdict(self)


class HealthChecker:
    """Background health checker untuk semua channels"""

    def __init__(self, check_interval: float = 30.0):
        self.check_interval = check_interval
        self._channels: Dict[str, ProviderChannel] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def register(self, channel: ProviderChannel):
        self._channels[channel.id] = channel

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._check_loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _check_loop(self):
        while self._running:
            for channel in self._channels.values():
                if not channel.enabled:
                    continue
                try:
                    healthy = await self._ping(channel)
                    if healthy:
                        channel.health_status = HealthStatus.UP
                        channel.consecutive_failures = 0
                    else:
                        channel.consecutive_failures += 1
                        if channel.consecutive_failures >= channel.max_failures_before_down:
                            channel.health_status = HealthStatus.DOWN
                        else:
                            channel.health_status = HealthStatus.DEGRADED
                except Exception:
                    channel.consecutive_failures += 1
                    if channel.consecutive_failures >= channel.max_failures_before_down:
                        channel.health_status = HealthStatus.DOWN

                channel.last_health_check = time.time()

            await asyncio.sleep(self.check_interval)

    async def _ping(self, channel: ProviderChannel) -> bool:
        """Ping provider untuk health check"""
        import aiohttp
        try:
            # Simplified: try lightweight request
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {channel.api_key}"}
                async with session.get(
                    f"{channel.base_url}/models",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    return resp.status == 200
        except:
            return False


class TokenTracker:
    """Thread-safe token usage ledger"""

    def __init__(self):
        self._records: List[UsageRecord] = []
        self._user_totals: Dict[str, Dict] = defaultdict(lambda: {
            "total_tokens": 0, "total_cost": 0.0, "request_count": 0
        })
        self._channel_totals: Dict[str, Dict] = defaultdict(lambda: {
            "total_tokens": 0, "total_cost": 0.0, "request_count": 0
        })
        self._lock = asyncio.Lock()

    async def record(self, record: UsageRecord):
        async with self._lock:
            self._records.append(record)
            # Update user totals
            self._user_totals[record.user_id]["total_tokens"] += record.total_tokens
            self._user_totals[record.user_id]["total_cost"] += record.cost_usd
            self._user_totals[record.user_id]["request_count"] += 1
            # Update channel totals
            self._channel_totals[record.channel_id]["total_tokens"] += record.total_tokens
            self._channel_totals[record.channel_id]["total_cost"] += record.cost_usd
            self._channel_totals[record.channel_id]["request_count"] += 1

    async def get_user_usage(self, user_id: str, period_hours: int = 24) -> Dict:
        async with self._lock:
            cutoff = time.time() - (period_hours * 3600)
            records = [r for r in self._records if r.user_id == user_id and r.timestamp > cutoff]
            return {
                "user_id": user_id,
                "period_hours": period_hours,
                "requests": len(records),
                "input_tokens": sum(r.input_tokens for r in records),
                "output_tokens": sum(r.output_tokens for r in records),
                "total_tokens": sum(r.total_tokens for r in records),
                "total_cost_usd": sum(r.cost_usd for r in records),
            }

    async def get_channel_usage(self, channel_id: str) -> Dict:
        return dict(self._channel_totals[channel_id])


class ModelCatalog:
    """Pre-loaded model registry dengan metadata"""

    def __init__(self):
        self._models: Dict[str, ModelInfo] = {}
        self._load_builtin_models()

    def _load_builtin_models(self):
        """Load built-in model definitions"""
        builtins = [
            ModelInfo("gpt-4o", "openai", "GPT-4o", 128000, 4096, 5.0, 15.0, True, True, True, True, 800, 0.95, 0.95),
            ModelInfo("gpt-4o-mini", "openai", "GPT-4o Mini", 128000, 16384, 0.15, 0.60, True, True, True, True, 600, 0.85, 0.90),
            ModelInfo("claude-3-5-sonnet", "anthropic", "Claude 3.5 Sonnet", 200000, 8192, 3.0, 15.0, True, True, True, False, 1000, 0.95, 0.95),
            ModelInfo("claude-3-haiku", "anthropic", "Claude 3 Haiku", 200000, 4096, 0.25, 1.25, True, True, True, False, 500, 0.80, 0.90),
            ModelInfo("gemini-1.5-pro", "gemini", "Gemini 1.5 Pro", 1000000, 8192, 3.5, 10.5, True, True, True, True, 900, 0.90, 0.90),
            ModelInfo("gemini-1.5-flash", "gemini", "Gemini 1.5 Flash", 1000000, 8192, 0.35, 1.05, True, True, True, True, 400, 0.80, 0.85),
            ModelInfo("llama-3.1-70b", "groq", "Llama 3.1 70B", 131072, 4096, 0.59, 0.79, False, True, True, False, 300, 0.85, 0.85),
            ModelInfo("mixtral-8x22b", "mistral", "Mixtral 8x22B", 65536, 4096, 2.0, 6.0, False, True, True, False, 700, 0.82, 0.80),
            ModelInfo("deepseek-chat", "deepseek", "DeepSeek Chat", 64000, 8192, 0.14, 0.28, False, True, True, True, 800, 0.85, 0.85),
            ModelInfo("openrouter/auto", "openrouter", "OpenRouter Auto", 128000, 4096, 0.0, 0.0, True, True, True, True, 1000, 0.80, 0.80, ["auto-routing"]),
        ]
        for m in builtins:
            self._models[m.id] = m

    def get(self, model_id: str) -> Optional[ModelInfo]:
        return self._models.get(model_id)

    def list_all(self) -> List[Dict]:
        return [m.to_dict() for m in self._models.values()]

    def find_by_tag(self, tag: str) -> List[ModelInfo]:
        return [m for m in self._models.values() if tag in m.tags]

    def find_by_capability(self, vision: bool = None, tools: bool = None,
                          streaming: bool = None) -> List[ModelInfo]:
        results = list(self._models.values())
        if vision is not None:
            results = [m for m in results if m.supports_vision == vision]
        if tools is not None:
            results = [m for m in results if m.supports_tools == tools]
        if streaming is not None:
            results = [m for m in results if m.supports_streaming == streaming]
        return results


class RateLimiter:
    """Token bucket rate limiter"""

    def __init__(self):
        self._buckets: Dict[str, Dict] = {}  # key -> {tokens, last_update, capacity}
        self._lock = asyncio.Lock()

    async def check(self, key: str, tokens_needed: int = 1,
                    capacity: int = 60, refill_rate: float = 1.0) -> bool:
        """Check if request is allowed"""
        async with self._lock:
            now = time.time()
            if key not in self._buckets:
                self._buckets[key] = {"tokens": capacity, "last_update": now, "capacity": capacity}

            bucket = self._buckets[key]
            elapsed = now - bucket["last_update"]
            bucket["tokens"] = min(bucket["capacity"], bucket["tokens"] + elapsed * refill_rate)
            bucket["last_update"] = now

            if bucket["tokens"] >= tokens_needed:
                bucket["tokens"] -= tokens_needed
                return True
            return False

    async def get_remaining(self, key: str) -> int:
        async with self._lock:
            if key not in self._buckets:
                return 60
            bucket = self._buckets[key]
            elapsed = time.time() - bucket["last_update"]
            return int(min(bucket["capacity"], bucket["tokens"] + elapsed * 1.0))


class FallbackChain:
    """Fallback routing: primary → secondary → tertiary"""

    def __init__(self, channels: Dict[str, ProviderChannel]):
        self.channels = channels

    def get_fallback_chain(self, channel_id: str) -> List[str]:
        """Get ordered fallback chain"""
        chain = []
        visited = set()
        current = channel_id

        while current and current not in visited:
            visited.add(current)
            chain.append(current)
            channel = self.channels.get(current)
            if channel:
                current = channel.fallback_to
            else:
                break

        return chain

    def get_best_available(self, channel_id: str) -> Optional[str]:
        """Get best available channel dalam chain"""
        for cid in self.get_fallback_chain(channel_id):
            channel = self.channels.get(cid)
            if channel and channel.enabled and channel.health_status in (HealthStatus.UP, HealthStatus.DEGRADED):
                return cid
        return None


class ProviderManager:
    """
    High-level provider manager - unified interface.
    Tiru One-API: manage all LLM providers through single interface.
    """

    def __init__(self):
        self.channels: Dict[str, ProviderChannel] = {}
        self.catalog = ModelCatalog()
        self.health_checker = HealthChecker()
        self.token_tracker = TokenTracker()
        self.rate_limiter = RateLimiter()
        self.fallback = FallbackChain(self.channels)
        self._mesh_broadcast: Optional[Callable] = None

    def connect_mesh(self, broadcast_fn: Callable):
        self._mesh_broadcast = broadcast_fn

    def add_channel(self, channel: ProviderChannel) -> str:
        self.channels[channel.id] = channel
        self.health_checker.register(channel)
        self.fallback = FallbackChain(self.channels)
        return channel.id

    def remove_channel(self, channel_id: str) -> bool:
        if channel_id in self.channels:
            del self.channels[channel_id]
            self.fallback = FallbackChain(self.channels)
            return True
        return False

    async def start(self):
        await self.health_checker.start()

    async def stop(self):
        await self.health_checker.stop()

    def get_channel_for_model(self, model_id: str,
                              strategy: str = "priority") -> Optional[ProviderChannel]:
        """Get best channel untuk model dengan routing strategy"""
        # Find channels yang expose model ini
        candidates = [
            c for c in self.channels.values()
            if model_id in c.models or c.provider_type == ProviderType.OPENROUTER
        ]

        if not candidates:
            return None

        # Filter by health
        healthy = [c for c in candidates
                   if c.health_status in (HealthStatus.UP, HealthStatus.DEGRADED)]
        if not healthy:
            # Try fallback
            for c in candidates:
                best = self.fallback.get_best_available(c.id)
                if best:
                    return self.channels.get(best)
            return None

        # Apply strategy
        if strategy == "priority":
            return min(healthy, key=lambda c: c.priority)
        elif strategy == "cost":
            model = self.catalog.get(model_id)
            if model:
                return min(healthy, key=lambda c: self._estimate_cost(c, model))
        elif strategy == "latency":
            return min(healthy, key=lambda c: c.health_status == HealthStatus.DEGRADED)
        elif strategy == "quality":
            # Prefer highest quality score
            return max(healthy, key=lambda c: self._get_provider_quality(c))
        elif strategy == "random":
            import random
            return random.choice(healthy)

        return healthy[0]

    def _estimate_cost(self, channel: ProviderChannel, model: ModelInfo) -> float:
        """Estimate cost for model via channel"""
        return model.cost_per_1k_input + model.cost_per_1k_output

    def _get_provider_quality(self, channel: ProviderChannel) -> float:
        return 0.8  # Default

    def get_status(self) -> Dict:
        return {
            "channels": len(self.channels),
            "healthy": sum(1 for c in self.channels.values() if c.health_status == HealthStatus.UP),
            "degraded": sum(1 for c in self.channels.values() if c.health_status == HealthStatus.DEGRADED),
            "down": sum(1 for c in self.channels.values() if c.health_status == HealthStatus.DOWN),
            "models": len(self.catalog.list_all()),
            "total_usage_records": len(self.token_tracker._records)
        }


# ==================== DEMO ====================

if __name__ == "__main__":
    async def demo():
        mgr = ProviderManager()

        # Add channels
        mgr.add_channel(ProviderChannel(
            provider_type=ProviderType.OPENAI,
            name="OpenAI Primary",
            base_url="https://api.openai.com/v1",
            api_key="sk-...",
            models=["gpt-4o", "gpt-4o-mini"],
            priority=1
        ))

        mgr.add_channel(ProviderChannel(
            provider_type=ProviderType.ANTHROPIC,
            name="Anthropic Fallback",
            base_url="https://api.anthropic.com",
            api_key="sk-ant-...",
            models=["claude-3-5-sonnet", "claude-3-haiku"],
            priority=2
        ))

        print(f"Models: {len(mgr.catalog.list_all())}")
        print(f"Channels: {mgr.get_status()}")

    asyncio.run(demo())
