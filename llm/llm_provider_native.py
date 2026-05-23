"""
llm_provider_native.py -- MAGNATRIX-OS Native LLM Provider Gateway
Native Python, zero external dependencies. ~780 lines, 12 classes.
Pattern: AMATI-PELAJARI-TIRU from free-llm-api-keys rotation model.

Part 1: ProviderConfig, KeyPoolManager, ProviderRegistry, RequestRouter, RateLimiterPerKey
Part 2: ResponseCache, ModelMapper, StreamingHandlerStub, CostTracker, FailoverEngine,
        ProviderHealthMonitor, LLMGateway, LLMProviderBridge + demo
"""

from __future__ import annotations

import json
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# -- Part 1: Core Infrastructure (lines ~1-400) -------------------------

class AuthType(Enum):
    """Supported authentication schemes."""
    BEARER = "bearer"
    API_KEY = "api_key"
    X_API_KEY = "x_api_key"
    NONE = "none"


@dataclass
class ProviderConfig:
    """Immutable-ish per-provider configuration."""
    name: str
    endpoint: str
    models: List[str] = field(default_factory=list)
    rate_limit_rpm: int = 60
    rate_limit_tpd: int = 10000
    quota_usd: float = 20.0
    auth_type: AuthType = AuthType.BEARER
    headers: Dict[str, str] = field(default_factory=dict)
    timeout_sec: float = 30.0
    retries: int = 3
    priority: int = 5  # lower = higher priority
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def model_id_for(self, alias: str) -> Optional[str]:
        """Return the provider-specific model ID if alias is supported."""
        if alias in self.models:
            return alias
        # Allow prefix matching for common families
        for m in self.models:
            if alias in m or m in alias:
                return m
        return None


# -- KeyPoolManager -----------------------------------------------------

@dataclass
class KeyEntry:
    key_id: str
    secret: str
    provider: str
    added_at: float
    expires_at: float
    used_count: int = 0
    last_used: float = 0.0
    cooldown_until: float = 0.0
    blacklisted: bool = False
    quota_remaining: float = 20.0


class KeyPoolManager:
    """Pool of API keys with rotation, expiry, blacklist, and cooldown."""

    def __init__(self) -> None:
        self._pool: Dict[str, List[KeyEntry]] = {}  # provider -> keys
        self._lock = threading.RLock()
        self._global_blacklist: set = set()

    def add_key(self, provider: str, secret: str, ttl_sec: float = 86400.0,
                quota_usd: float = 20.0) -> str:
        now = time.time()
        kid = str(uuid.uuid4())[:8]
        entry = KeyEntry(
            key_id=kid,
            secret=secret,
            provider=provider,
            added_at=now,
            expires_at=now + ttl_sec,
            quota_remaining=quota_usd,
        )
        with self._lock:
            self._pool.setdefault(provider, []).append(entry)
        return kid

    def remove_key(self, provider: str, key_id: str) -> bool:
        with self._lock:
            lst = self._pool.get(provider, [])
            for i, e in enumerate(lst):
                if e.key_id == key_id:
                    lst.pop(i)
                    return True
            return False

    def get_key(self, provider: str, strategy: str = "round_robin") -> Optional[KeyEntry]:
        with self._lock:
            lst = [e for e in self._pool.get(provider, [])
                   if not e.blacklisted and e.expires_at > time.time()
                   and e.cooldown_until < time.time()
                   and e.key_id not in self._global_blacklist]
            if not lst:
                return None
            if strategy == "round_robin":
                entry = min(lst, key=lambda e: e.used_count)
            elif strategy == "least_used":
                entry = min(lst, key=lambda e: e.used_count)
            elif strategy == "random":
                entry = random.choice(lst)
            else:
                entry = lst[0]
            entry.used_count += 1
            entry.last_used = time.time()
            return entry

    def return_key(self, provider: str, key_id: str, cooldown: float = 0.0) -> None:
        with self._lock:
            for e in self._pool.get(provider, []):
                if e.key_id == key_id:
                    if cooldown > 0:
                        e.cooldown_until = time.time() + cooldown
                    break

    def blacklist(self, provider: str, key_id: str) -> None:
        with self._lock:
            for e in self._pool.get(provider, []):
                if e.key_id == key_id:
                    e.blacklisted = True
                    self._global_blacklist.add(key_id)
                    break

    def all_keys(self, provider: Optional[str] = None) -> List[KeyEntry]:
        with self._lock:
            if provider:
                return list(self._pool.get(provider, []))
            out: List[KeyEntry] = []
            for lst in self._pool.values():
                out.extend(lst)
            return out

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "providers": list(self._pool.keys()),
                "total_keys": sum(len(v) for v in self._pool.values()),
                "blacklisted": len(self._global_blacklist),
            }


# -- ProviderRegistry -----------------------------------------------------

class ProviderRegistry:
    """Register, index, and health-check multiple LLM providers."""

    def __init__(self) -> None:
        self._configs: Dict[str, ProviderConfig] = {}
        self._health: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def register(self, cfg: ProviderConfig) -> None:
        with self._lock:
            self._configs[cfg.name] = cfg
            self._health.setdefault(cfg.name, {
                "last_ping": 0.0,
                "latency_ms": 9999.0,
                "healthy": True,
                "failures": 0,
            })

    def unregister(self, name: str) -> bool:
        with self._lock:
            return self._configs.pop(name, None) is not None

    def get(self, name: str) -> Optional[ProviderConfig]:
        with self._lock:
            return self._configs.get(name)

    def list_providers(self, only_healthy: bool = False) -> List[str]:
        with self._lock:
            names = []
            for n, cfg in self._configs.items():
                if not cfg.enabled:
                    continue
                if only_healthy and not self._health[n]["healthy"]:
                    continue
                names.append(n)
            return names

    def providers_for_model(self, model_alias: str, only_healthy: bool = False) -> List[str]:
        out: List[str] = []
        for name in self.list_providers(only_healthy=only_healthy):
            cfg = self._configs[name]
            if cfg.model_id_for(model_alias):
                out.append(name)
        return out

    def health_ping(self, name: str, latency_ms: float) -> None:
        with self._lock:
            h = self._health[name]
            h["last_ping"] = time.time()
            h["latency_ms"] = latency_ms
            h["healthy"] = latency_ms < 5000  # < 5s is healthy
            h["failures"] = max(0, h["failures"] - 1)

    def health_fail(self, name: str) -> None:
        with self._lock:
            h = self._health[name]
            h["failures"] += 1
            if h["failures"] >= 3:
                h["healthy"] = False

    def is_healthy(self, name: str) -> bool:
        with self._lock:
            return self._health.get(name, {}).get("healthy", False)

    def health_snapshot(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {k: dict(v) for k, v in self._health.items()}


# -- RateLimiterPerKey --------------------------------------------------

class RateLimiterPerKey:
    """Token-bucket style rate limiter per (key, provider, model)."""

    def __init__(self, default_rpm: int = 60) -> None:
        self._buckets: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        self._default_rpm = default_rpm
        self._lock = threading.RLock()

    def _bucket(self, key_id: str, provider: str, model: str) -> Dict[str, Any]:
        k = (key_id, provider, model)
        if k not in self._buckets:
            self._buckets[k] = {"tokens": self._default_rpm, "last_update": time.time()}
        return self._buckets[k]

    def acquire(self, key_id: str, provider: str, model: str,
                rpm: Optional[int] = None, cost: int = 1) -> bool:
        with self._lock:
            b = self._bucket(key_id, provider, model)
            now = time.time()
            elapsed = now - b["last_update"]
            rate = rpm or self._default_rpm
            b["tokens"] = min(rate, b["tokens"] + elapsed * (rate / 60.0))
            b["last_update"] = now
            if b["tokens"] >= cost:
                b["tokens"] -= cost
                return True
            return False

    def get_tokens(self, key_id: str, provider: str, model: str) -> float:
        with self._lock:
            b = self._bucket(key_id, provider, model)
            now = time.time()
            elapsed = now - b["last_update"]
            b["tokens"] = min(self._default_rpm, b["tokens"] + elapsed * (self._default_rpm / 60.0))
            b["last_update"] = now
            return b["tokens"]


# -- RequestRouter ------------------------------------------------------

class RoutingStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_LATENCY = "least_latency"
    QUOTA_AWARE = "quota_aware"
    PRIORITY = "priority"
    RANDOM = "random"


class RequestRouter:
    """Route requests to the optimal provider based on strategy."""

    def __init__(self, registry: ProviderRegistry, key_pool: KeyPoolManager,
                 limiter: RateLimiterPerKey) -> None:
        self.registry = registry
        self.key_pool = key_pool
        self.limiter = limiter
        self._rr_index: Dict[str, int] = {}
        self._lock = threading.Lock()

    def route(self, model_alias: str,
              strategy: RoutingStrategy = RoutingStrategy.ROUND_ROBIN,
              fallback: bool = True) -> Optional[Tuple[str, KeyEntry]]:
        providers = self.registry.providers_for_model(model_alias, only_healthy=True)
        if not providers:
            if fallback:
                providers = self.registry.providers_for_model(model_alias, only_healthy=False)
            if not providers:
                return None

        scored: List[Tuple[float, str]] = []
        for pname in providers:
            cfg = self.registry.get(pname)
            if cfg is None:
                continue
            key = self.key_pool.get_key(pname)
            if key is None:
                continue
            score = self._score(pname, cfg, key, strategy)
            scored.append((score, pname))
            # return key immediately so it stays available
            self.key_pool.return_key(pname, key.key_id)

        if not scored:
            return None

        scored.sort()
        chosen = scored[0][1]
        key = self.key_pool.get_key(chosen)
        if key is None:
            return None
        # verify rate limit
        model_id = self.registry.get(chosen).model_id_for(model_alias) or model_alias
        if not self.limiter.acquire(key.key_id, chosen, model_id,
                                    rpm=self.registry.get(chosen).rate_limit_rpm):
            self.key_pool.return_key(chosen, key.key_id, cooldown=5.0)
            if fallback and len(scored) > 1:
                return self.route(model_alias, strategy, fallback=False)
            return None
        return chosen, key

    def _score(self, pname: str, cfg: ProviderConfig, key: KeyEntry,
               strategy: RoutingStrategy) -> float:
        if strategy == RoutingStrategy.ROUND_ROBIN:
            with self._lock:
                idx = self._rr_index.get(pname, 0)
                self._rr_index[pname] = idx + 1
            return idx
        if strategy == RoutingStrategy.LEAST_LATENCY:
            h = self.registry.health_snapshot().get(pname, {})
            return h.get("latency_ms", 9999.0)
        if strategy == RoutingStrategy.QUOTA_AWARE:
            return -(key.quota_remaining)
        if strategy == RoutingStrategy.PRIORITY:
            return cfg.priority
        if strategy == RoutingStrategy.RANDOM:
            return random.random()
        return 0.0

    def route_with_fallback_chain(self, model_alias: str,
                                  strategies: List[RoutingStrategy] = None,
                                  max_attempts: int = 3) -> Optional[Tuple[str, KeyEntry]]:
        strategies = strategies or [RoutingStrategy.ROUND_ROBIN,
                                    RoutingStrategy.LEAST_LATENCY,
                                    RoutingStrategy.QUOTA_AWARE]
        for strat in strategies[:max_attempts]:
            result = self.route(model_alias, strategy=strat, fallback=True)
            if result:
                return result
        return None


# -- Part 2: Advanced Components + Demo (lines ~401-780) ----------------

# -- ResponseCache ------------------------------------------------------

class ResponseCache:
    """Simple in-memory cache with TTL and hit/miss metrics."""

    def __init__(self, default_ttl: float = 300.0, max_size: int = 1000) -> None:
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        self._default_ttl = default_ttl
        self._max_size = max_size

    def _make_key(self, provider: str, model: str, messages: Tuple) -> str:
        payload = json.dumps({"p": provider, "m": model, "msg": messages}, sort_keys=True)
        # simple hash
        h = 0
        for ch in payload:
            h = (h * 31 + ord(ch)) & 0xFFFFFFFF
        return f"{provider}:{model}:{h}"

    def get(self, provider: str, model: str, messages: List[Dict[str, str]]) -> Optional[Any]:
        key = self._make_key(provider, model, tuple(json.dumps(m, sort_keys=True) for m in messages))
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if time.time() < expiry:
                    self._hits += 1
                    return value
                del self._cache[key]
            self._misses += 1
            return None

    def set(self, provider: str, model: str, messages: List[Dict[str, str]],
            value: Any, ttl: Optional[float] = None) -> None:
        key = self._make_key(provider, model, tuple(json.dumps(m, sort_keys=True) for m in messages))
        with self._lock:
            if len(self._cache) >= self._max_size:
                # evict oldest by expiry
                oldest = min(self._cache.items(), key=lambda x: x[1][1])
                del self._cache[oldest[0]]
            self._cache[key] = (value, time.time() + (ttl or self._default_ttl))

    def invalidate_provider(self, provider: str) -> int:
        with self._lock:
            to_drop = [k for k in self._cache if k.startswith(provider + ":")]
            for k in to_drop:
                del self._cache[k]
            return len(to_drop)

    def metrics(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / total if total else 0.0,
                "size": len(self._cache),
            }


# -- ModelMapper --------------------------------------------------------

class ModelMapper:
    """Map canonical model aliases to provider-specific model IDs."""

    # Canonical alias -> list of (provider, model_id) fallback chain
    DEFAULT_MAP: Dict[str, List[Tuple[str, str]]] = {
        "gpt-4": [("openai", "gpt-4"), ("grok", "grok-2"), ("deepseek", "deepseek-chat")],
        "gpt-4o": [("openai", "gpt-4o"), ("grok", "grok-2-vision")],
        "claude-3": [("claude", "claude-3-5-sonnet-20241022"), ("openai", "gpt-4")],
        "claude-opus": [("claude", "claude-3-opus-20240229")],
        "deepseek-chat": [("deepseek", "deepseek-chat"), ("openai", "gpt-3.5-turbo")],
        "gemini-pro": [("gemini", "gemini-1.5-pro"), ("openai", "gpt-4")],
        "gemini-flash": [("gemini", "gemini-1.5-flash")],
        "grok-beta": [("grok", "grok-beta")],
        "local-llm": [("local", "llama-3-8b-instruct")],
    }

    def __init__(self, overrides: Optional[Dict[str, List[Tuple[str, str]]]] = None) -> None:
        self._map = dict(overrides or self.DEFAULT_MAP)
        self._lock = threading.RLock()

    def resolve(self, alias: str, preferred_provider: Optional[str] = None) -> Optional[Tuple[str, str]]:
        with self._lock:
            chain = self._map.get(alias, [])
            if preferred_provider:
                for p, m in chain:
                    if p == preferred_provider:
                        return p, m
            return chain[0] if chain else None

    def register_alias(self, alias: str, chain: List[Tuple[str, str]]) -> None:
        with self._lock:
            self._map[alias] = chain

    def list_aliases(self) -> List[str]:
        with self._lock:
            return list(self._map.keys())


# -- StreamingHandlerStub -----------------------------------------------

class StreamingHandlerStub:
    """Stub SSE streaming handler: chunk buffer, abort signal, async iterator mimic."""

    def __init__(self) -> None:
        self._buffer: deque = deque(maxlen=1000)
        self._aborted = False
        self._done = False
        self._lock = threading.Lock()
        self._listeners: List[Callable[[str], None]] = []

    def push_chunk(self, chunk: str) -> None:
        with self._lock:
            if self._aborted or self._done:
                return
            self._buffer.append(chunk)
            for fn in self._listeners:
                try:
                    fn(chunk)
                except Exception:
                    pass

    def abort(self) -> None:
        with self._lock:
            self._aborted = True

    def is_aborted(self) -> bool:
        with self._lock:
            return self._aborted

    def mark_done(self) -> None:
        with self._lock:
            self._done = True

    def get_buffer(self) -> List[str]:
        with self._lock:
            return list(self._buffer)

    def on_chunk(self, callback: Callable[[str], None]) -> None:
        with self._lock:
            self._listeners.append(callback)

    def drain(self) -> str:
        return "".join(self.get_buffer())


# -- CostTracker --------------------------------------------------------

class CostTracker:
    """Track usage per key/provider/model, estimate cost, track quota remaining."""

    # USD per 1K tokens (input, output) rough estimates
    PRICE_TABLE: Dict[str, Tuple[float, float]] = {
        "gpt-4": (0.03, 0.06),
        "gpt-4o": (0.005, 0.015),
        "claude-3-5-sonnet": (0.003, 0.015),
        "claude-3-opus": (0.015, 0.075),
        "deepseek-chat": (0.00014, 0.00028),
        "gemini-1.5-pro": (0.0035, 0.0105),
        "gemini-1.5-flash": (0.00035, 0.00105),
        "grok-2": (0.005, 0.015),
        "local": (0.0, 0.0),
    }

    def __init__(self) -> None:
        self._usage: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def record(self, provider: str, model: str, key_id: str,
               input_tokens: int, output_tokens: int) -> Dict[str, Any]:
        price = self.PRICE_TABLE.get(model, (0.01, 0.03))
        cost = (input_tokens / 1000.0) * price[0] + (output_tokens / 1000.0) * price[1]
        with self._lock:
            k = f"{provider}:{model}:{key_id}"
            rec = self._usage.setdefault(k, {
                "requests": 0, "input_tokens": 0, "output_tokens": 0, "cost": 0.0
            })
            rec["requests"] += 1
            rec["input_tokens"] += input_tokens
            rec["output_tokens"] += output_tokens
            rec["cost"] += cost
            return {"cost_usd": cost, "cumulative_usd": rec["cost"], "quota_remaining": -1}

    def estimate(self, model: str, input_tokens: int, output_tokens: int) -> float:
        price = self.PRICE_TABLE.get(model, (0.01, 0.03))
        return (input_tokens / 1000.0) * price[0] + (output_tokens / 1000.0) * price[1]

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            total_cost = sum(v["cost"] for v in self._usage.values())
            total_req = sum(v["requests"] for v in self._usage.values())
            return {
                "total_cost_usd": round(total_cost, 6),
                "total_requests": total_req,
                "per_key": {k: dict(v) for k, v in self._usage.items()},
            }


# -- FailoverEngine -----------------------------------------------------

class FailoverEngine:
    """Detect failure, retry with exponential backoff, circuit breaker."""

    def __init__(self, registry: ProviderRegistry,
                 max_retries: int = 3,
                 base_delay: float = 1.0,
                 circuit_threshold: int = 5) -> None:
        self.registry = registry
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._circuit_threshold = circuit_threshold
        self._circuit_states: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def _circuit(self, provider: str) -> Dict[str, Any]:
        if provider not in self._circuit_states:
            self._circuit_states[provider] = {"failures": 0, "open_until": 0.0, "half_open": False}
        return self._circuit_states[provider]

    def is_open(self, provider: str) -> bool:
        with self._lock:
            c = self._circuit(provider)
            if c["open_until"] > time.time():
                return True
            if c["half_open"]:
                return False
            return False

    def record_success(self, provider: str) -> None:
        with self._lock:
            c = self._circuit(provider)
            c["failures"] = 0
            c["half_open"] = False
            c["open_until"] = 0.0

    def record_failure(self, provider: str) -> bool:
        with self._lock:
            c = self._circuit(provider)
            c["failures"] += 1
            if c["failures"] >= self._circuit_threshold:
                c["open_until"] = time.time() + 30.0
                c["half_open"] = False
                return True
            c["half_open"] = True
            return False

    def retry(self, fn: Callable, provider: str, *args, **kwargs) -> Any:
        last_exc: Optional[Exception] = None
        for attempt in range(self._max_retries + 1):
            if self.is_open(provider):
                raise RuntimeError(f"Circuit breaker OPEN for {provider}")
            try:
                result = fn(*args, **kwargs)
                self.record_success(provider)
                return result
            except Exception as exc:
                last_exc = exc
                self.registry.health_fail(provider)
                if attempt < self._max_retries:
                    delay = self._base_delay * (2 ** attempt)
                    time.sleep(delay)
        self.record_failure(provider)
        raise last_exc or RuntimeError(f"All retries exhausted for {provider}")


# -- ProviderHealthMonitor ----------------------------------------------

class ProviderHealthMonitor:
    """Ping providers, measure latency, track uptime, mark unhealthy."""

    def __init__(self, registry: ProviderRegistry,
                 ping_interval: float = 60.0,
                 timeout: float = 5.0) -> None:
        self.registry = registry
        self._ping_interval = ping_interval
        self._timeout = timeout
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            for name in self.registry.list_providers():
                latency = self._mock_ping(name)
                self.registry.health_ping(name, latency)
            self._stop_event.wait(self._ping_interval)

    def _mock_ping(self, name: str) -> float:
        # Stub: simulate latency with some jitter + occasional failure
        base = 150.0
        if name == "local":
            base = 20.0
        if name in ("deepseek",):
            base = 400.0
        if random.random() < 0.05:
            # 5% failure
            return 9999.0
        return base + random.random() * 200.0

    def status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "interval": self._ping_interval,
            "health": self.registry.health_snapshot(),
        }


# -- LLMGateway ---------------------------------------------------------

class LLMGateway:
    """Compose all components. Unified interface."""

    def __init__(self) -> None:
        self.registry = ProviderRegistry()
        self.key_pool = KeyPoolManager()
        self.limiter = RateLimiterPerKey()
        self.router = RequestRouter(self.registry, self.key_pool, self.limiter)
        self.cache = ResponseCache()
        self.mapper = ModelMapper()
        self.streamer = StreamingHandlerStub()
        self.cost = CostTracker()
        self.failover = FailoverEngine(self.registry)
        self.monitor = ProviderHealthMonitor(self.registry)
        self._request_count = 0
        self._lock = threading.Lock()

    def register_provider(self, cfg: ProviderConfig) -> None:
        self.registry.register(cfg)

    def add_key(self, provider: str, secret: str, ttl: float = 86400.0) -> str:
        return self.key_pool.add_key(provider, secret, ttl)

    def chat_completion(self, model_alias: str,
                        messages: List[Dict[str, str]],
                        stream: bool = False,
                        strategy: RoutingStrategy = RoutingStrategy.ROUND_ROBIN,
                        use_cache: bool = True) -> Dict[str, Any]:
        with self._lock:
            self._request_count += 1
        # 1. resolve model alias
        resolved = self.mapper.resolve(model_alias)
        if resolved:
            preferred_provider, model_id = resolved
        else:
            preferred_provider, model_id = None, model_alias

        # 2. route to provider + key
        route = self.router.route(model_alias, strategy=strategy)
        if route is None:
            return {"error": "NO_PROVIDER_AVAILABLE", "model": model_alias}
        provider_name, key = route
        cfg = self.registry.get(provider_name)
        actual_model = cfg.model_id_for(model_alias) or model_id

        # 3. cache check
        if use_cache and not stream:
            cached = self.cache.get(provider_name, actual_model, messages)
            if cached is not None:
                return {"cached": True, "provider": provider_name, "content": cached}

        # 4. simulate request (native -- no external HTTP lib)
        result = self._mock_chat(provider_name, actual_model, messages, stream)

        # 5. record cost
        self.cost.record(provider_name, actual_model, key.key_id,
                         result.get("input_tokens", 0), result.get("output_tokens", 0))

        # 6. store cache
        if use_cache and not stream:
            self.cache.set(provider_name, actual_model, messages, result.get("content"))

        return {
            "provider": provider_name,
            "model": actual_model,
            "key_id": key.key_id,
            "content": result.get("content"),
            "input_tokens": result.get("input_tokens"),
            "output_tokens": result.get("output_tokens"),
            "latency_ms": result.get("latency_ms"),
            "request_num": self._request_count,
        }

    def embed(self, model_alias: str, texts: List[str],
              strategy: RoutingStrategy = RoutingStrategy.ROUND_ROBIN) -> Dict[str, Any]:
        route = self.router.route(model_alias, strategy=strategy)
        if route is None:
            return {"error": "NO_PROVIDER_AVAILABLE", "model": model_alias}
        provider_name, key = route
        # stub embedding
        vectors = [[random.random() for _ in range(1536)] for _ in texts]
        return {
            "provider": provider_name,
            "model": model_alias,
            "key_id": key.key_id,
            "vectors": vectors,
            "dimensions": 1536,
        }

    def list_models(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for pname in self.registry.list_providers():
            cfg = self.registry.get(pname)
            out.append({
                "provider": pname,
                "models": cfg.models,
                "healthy": self.registry.is_healthy(pname),
            })
        return out

    def _mock_chat(self, provider: str, model: str,
                   messages: List[Dict[str, str]], stream: bool) -> Dict[str, Any]:
        latency = 100 + random.randint(0, 400)
        if provider == "local":
            latency = 20 + random.randint(0, 50)
        # simulate tiny delay
        time.sleep(0.001)
        content = f"[Mock response from {provider}/{model}]"
        return {
            "content": content,
            "input_tokens": sum(len(m.get("content", "")) for m in messages) // 4,
            "output_tokens": len(content) // 4,
            "latency_ms": latency,
        }

    def start_monitor(self) -> None:
        self.monitor.start()

    def stop_monitor(self) -> None:
        self.monitor.stop()

    def stats(self) -> Dict[str, Any]:
        return {
            "requests": self._request_count,
            "cache": self.cache.metrics(),
            "cost": self.cost.summary(),
            "keys": self.key_pool.stats(),
            "health": self.registry.health_snapshot(),
        }


# -- LLMProviderBridge --------------------------------------------------

class LLMProviderBridge:
    """Bridge LLMGateway to MAGNATRIX-OS event_bus & service_registry stubs."""

    def __init__(self, gateway: LLMGateway,
                 event_bus: Optional[Any] = None,
                 service_registry: Optional[Any] = None) -> None:
        self.gateway = gateway
        self.event_bus = event_bus
        self.service_registry = service_registry
        self._subscribed = False

    def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        if self.event_bus:
            try:
                self.event_bus.emit(event_type, payload)
            except Exception:
                pass

    def chat(self, *args, **kwargs) -> Dict[str, Any]:
        result = self.gateway.chat_completion(*args, **kwargs)
        self.publish("llm.chat", {"result": result, "args": args, "kwargs": kwargs})
        return result

    def embed(self, *args, **kwargs) -> Dict[str, Any]:
        result = self.gateway.embed(*args, **kwargs)
        self.publish("llm.embed", {"result": result})
        return result

    def register_self(self, name: str = "llm_gateway") -> None:
        if self.service_registry:
            try:
                self.service_registry.register(name, self)
            except Exception:
                pass

    def heartbeat(self) -> Dict[str, Any]:
        return {"service": "llm_gateway", "status": "ok", "stats": self.gateway.stats()}


# -- Demo / Main --------------------------------------------------------

def _demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS -- llm_provider_native.py DEMO")
    print("=" * 60)

    gw = LLMGateway()

    # Register 5 providers
    providers = [
        ProviderConfig("openai", "https://api.openai.com/v1",
                       models=["gpt-4", "gpt-4o", "gpt-3.5-turbo"],
                       rate_limit_rpm=60, quota_usd=50.0, priority=1),
        ProviderConfig("claude", "https://api.anthropic.com/v1",
                       models=["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
                       rate_limit_rpm=50, quota_usd=30.0, priority=2),
        ProviderConfig("deepseek", "https://api.deepseek.com/v1",
                       models=["deepseek-chat", "deepseek-coder"],
                       rate_limit_rpm=100, quota_usd=20.0, priority=3),
        ProviderConfig("gemini", "https://generativelanguage.googleapis.com/v1",
                       models=["gemini-1.5-pro", "gemini-1.5-flash"],
                       rate_limit_rpm=60, quota_usd=40.0, priority=4),
        ProviderConfig("grok", "https://api.x.ai/v1",
                       models=["grok-2", "grok-2-vision", "grok-beta"],
                       rate_limit_rpm=45, quota_usd=25.0, priority=5),
    ]
    for p in providers:
        gw.register_provider(p)
        print(f"[+] Registered provider: {p.name} -> {p.endpoint}")

    # Add 10 keys (2 per provider)
    secrets = [
        ("openai", "sk-o1-" + uuid.uuid4().hex[:24]),
        ("openai", "sk-o2-" + uuid.uuid4().hex[:24]),
        ("claude", "sk-c1-" + uuid.uuid4().hex[:24]),
        ("claude", "sk-c2-" + uuid.uuid4().hex[:24]),
        ("deepseek", "sk-d1-" + uuid.uuid4().hex[:24]),
        ("deepseek", "sk-d2-" + uuid.uuid4().hex[:24]),
        ("gemini", "sk-g1-" + uuid.uuid4().hex[:24]),
        ("gemini", "sk-g2-" + uuid.uuid4().hex[:24]),
        ("grok", "sk-x1-" + uuid.uuid4().hex[:24]),
        ("grok", "sk-x2-" + uuid.uuid4().hex[:24]),
    ]
    for prov, sec in secrets:
        kid = gw.add_key(prov, sec)
        print(f"[+] Added key {kid} -> {prov}")

    # Start health monitor
    gw.start_monitor()
    time.sleep(0.1)

    # Send 20 requests with different strategies
    strategies = [
        RoutingStrategy.ROUND_ROBIN,
        RoutingStrategy.LEAST_LATENCY,
        RoutingStrategy.QUOTA_AWARE,
        RoutingStrategy.PRIORITY,
        RoutingStrategy.RANDOM,
    ]
    models = ["gpt-4", "claude-3", "deepseek-chat", "gemini-pro", "grok-beta"]
    messages = [{"role": "user", "content": "Hello, MAGNATRIX-OS!"}]

    print("\n--- 20 Requests with Routing Decisions ---")
    for i in range(20):
        model = models[i % len(models)]
        strat = strategies[i % len(strategies)]
        resp = gw.chat_completion(model, messages, strategy=strat, use_cache=(i > 5))
        provider = resp.get("provider", "FAIL")
        cached = resp.get("cached", False)
        latency = resp.get("latency_ms", 0)
        flag = "[CACHE]" if cached else ""
        print(f"  Req {i+1:02d} | model={model:15s} | strategy={strat.value:15s} "
              f"| provider={provider:8s} | latency={latency:4d}ms {flag}")

    # Show routing stats
    print("\n--- Gateway Stats ---")
    stats = gw.stats()
    print(json.dumps(stats, indent=2, default=str))

    # Failover simulation
    print("\n--- Failover Simulation ---")
    # Force mark openai as unhealthy
    gw.registry.health_fail("openai")
    gw.registry.health_fail("openai")
    gw.registry.health_fail("openai")
    print(f"  openai healthy? {gw.registry.is_healthy('openai')}")
    # Request gpt-4 -- should fallback away from openai
    resp = gw.chat_completion("gpt-4", messages, strategy=RoutingStrategy.ROUND_ROBIN)
    print(f"  gpt-4 routed to: {resp.get('provider')} (fallback away from openai)")

    # Show final model list
    print("\n--- Available Models ---")
    for m in gw.list_models():
        status = "[UP]" if m["healthy"] else "[DOWN]"
        print(f"  {status} {m['provider']:10s} -> {', '.join(m['models'])}")

    gw.stop_monitor()
    print("\n[OK] DEMO complete.")


if __name__ == "__main__":
    _demo()
