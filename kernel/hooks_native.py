#!/usr/bin/env python3
"""
================================================================================
MAGNATRIX-OS — Hooks Engine (Layer 0 Extension)
Inspired by: agiresearch/AIOS aios/hooks/
Pre/post execution hooks for personalization, logging, rate limiting,
and behavior modification across all system operations.
================================================================================
Zero-dependency hook chain with priority ordering and conditional execution.
================================================================================
"""
from __future__ import annotations

import hashlib
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union


# =============================================================================
# Constants
# =============================================================================
DEFAULT_HOOK_TIMEOUT = 5.0


# =============================================================================
# Data Types
# =============================================================================
class HookPhase(Enum):
    BEFORE = "before"
    AFTER = "after"
    AROUND = "around"
    ON_ERROR = "on_error"


class HookPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    DEBUG = 4


@dataclass
class HookContext:
    operation: str
    agent_id: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_time: float = 0.0
    result: Any = None
    error: Optional[Exception] = None
    cancelled: bool = False
    skip_remaining: bool = False


@dataclass
class HookRecord:
    hook_id: str
    name: str
    phase: HookPhase
    priority: HookPriority
    handler: Callable[[HookContext], Any]
    conditions: List[Callable[[HookContext], bool]] = field(default_factory=list)
    enabled: bool = True
    execution_count: int = 0
    total_duration_ms: float = 0.0


# =============================================================================
# Base Hook
# =============================================================================
class BaseHook(ABC):
    def __init__(self, name: str, phase: HookPhase, priority: HookPriority = HookPriority.NORMAL) -> None:
        self.name = name
        self.phase = phase
        self.priority = priority
        self.hook_id = hashlib.sha256(f"{name}:{phase.value}".encode()).hexdigest()[:12]
        self.enabled = True
        self._conditions: List[Callable[[HookContext], bool]] = []

    def when(self, condition: Callable[[HookContext], bool]) -> BaseHook:
        self._conditions.append(condition)
        return self

    def should_run(self, ctx: HookContext) -> bool:
        if not self.enabled:
            return False
        return all(c(ctx) for c in self._conditions)

    @abstractmethod
    def run(self, ctx: HookContext) -> None: ...


class LoggingHook(BaseHook):
    """Log all operations with timing."""

    def __init__(self, log_fn: Optional[Callable[[str], None]] = None) -> None:
        super().__init__("logging", HookPhase.AROUND, HookPriority.CRITICAL)
        self.log_fn = log_fn or print

    def run(self, ctx: HookContext) -> None:
        if ctx.result is not None:
            duration = (time.time() - ctx.start_time) * 1000 if ctx.start_time else 0
            self.log_fn(f"[HOOK] {ctx.operation} | agent={ctx.agent_id} | dur={duration:.1f}ms")


class RateLimitHook(BaseHook):
    """Rate limit operations per agent."""

    def __init__(self, max_calls: int = 100, window_sec: float = 60.0) -> None:
        super().__init__("rate_limit", HookPhase.BEFORE, HookPriority.HIGH)
        self.max_calls = max_calls
        self.window_sec = window_sec
        self._counters: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def run(self, ctx: HookContext) -> None:
        now = time.time()
        with self._lock:
            calls = self._counters.get(ctx.agent_id, [])
            calls = [c for c in calls if now - c < self.window_sec]
            if len(calls) >= self.max_calls:
                ctx.cancelled = True
                ctx.error = RuntimeError(f"Rate limit exceeded for {ctx.agent_id}")
                return
            calls.append(now)
            self._counters[ctx.agent_id] = calls


class MetricsHook(BaseHook):
    """Collect operation metrics."""

    def __init__(self) -> None:
        super().__init__("metrics", HookPhase.AFTER, HookPriority.NORMAL)
        self._metrics: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def run(self, ctx: HookContext) -> None:
        duration = (time.time() - ctx.start_time) * 1000 if ctx.start_time else 0
        with self._lock:
            key = f"{ctx.agent_id}:{ctx.operation}"
            if key not in self._metrics:
                self._metrics[key] = {"count": 0, "total_ms": 0.0, "errors": 0}
            self._metrics[key]["count"] += 1
            self._metrics[key]["total_ms"] += duration
            if ctx.error:
                self._metrics[key]["errors"] += 1

    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return dict(self._metrics)


class ValidationHook(BaseHook):
    """Validate parameters before execution."""

    def __init__(self, schema: Dict[str, Any]) -> None:
        super().__init__("validation", HookPhase.BEFORE, HookPriority.CRITICAL)
        self.schema = schema

    def run(self, ctx: HookContext) -> None:
        required = self.schema.get("required", [])
        for key in required:
            if key not in ctx.parameters:
                ctx.cancelled = True
                ctx.error = ValueError(f"Missing required parameter: {key}")
                return


class PersonalizationHook(BaseHook):
    """Inject agent-specific personalization into parameters."""

    def __init__(self, persona_registry: Any = None) -> None:
        super().__init__("personalization", HookPhase.BEFORE, HookPriority.NORMAL)
        self.persona = persona_registry

    def run(self, ctx: HookContext) -> None:
        if self.persona:
            prefs = self.persona.get(ctx.agent_id, {})
            ctx.parameters.update({"_personalization": prefs})


class CircuitBreakerHook(BaseHook):
    """Circuit breaker for failing operations."""

    def __init__(self, failure_threshold: int = 5, recovery_sec: float = 30.0) -> None:
        super().__init__("circuit_breaker", HookPhase.BEFORE, HookPriority.HIGH)
        self.failure_threshold = failure_threshold
        self.recovery_sec = recovery_sec
        self._failures: Dict[str, Tuple[int, float]] = {}
        self._lock = threading.Lock()

    def run(self, ctx: HookContext) -> None:
        key = f"{ctx.agent_id}:{ctx.operation}"
        with self._lock:
            count, last_fail = self._failures.get(key, (0, 0.0))
            if count >= self.failure_threshold:
                if time.time() - last_fail < self.recovery_sec:
                    ctx.cancelled = True
                    ctx.error = RuntimeError(f"Circuit breaker OPEN for {key}")
                    return
                else:
                    self._failures[key] = (0, 0.0)

    def on_error(self, ctx: HookContext) -> None:
        key = f"{ctx.agent_id}:{ctx.operation}"
        with self._lock:
            count, _ = self._failures.get(key, (0, 0.0))
            self._failures[key] = (count + 1, time.time())


# =============================================================================
# Hook Registry
# =============================================================================
class HookRegistry:
    """Register and manage all hooks with priority ordering."""

    def __init__(self) -> None:
        self._hooks: Dict[HookPhase, List[BaseHook]] = {
            phase: [] for phase in HookPhase
        }
        self._lock = threading.Lock()

    def register(self, hook: BaseHook) -> None:
        with self._lock:
            self._hooks[hook.phase].append(hook)
            self._hooks[hook.phase].sort(key=lambda h: h.priority.value)

    def unregister(self, hook_id: str) -> bool:
        with self._lock:
            for phase, hooks in self._hooks.items():
                for i, h in enumerate(hooks):
                    if h.hook_id == hook_id:
                        hooks.pop(i)
                        return True
            return False

    def get_hooks(self, phase: HookPhase) -> List[BaseHook]:
        with self._lock:
            return [h for h in self._hooks[phase] if h.enabled]

    def enable(self, hook_id: str) -> bool:
        with self._lock:
            for hooks in self._hooks.values():
                for h in hooks:
                    if h.hook_id == hook_id:
                        h.enabled = True
                        return True
            return False

    def disable(self, hook_id: str) -> bool:
        with self._lock:
            for hooks in self._hooks.values():
                for h in hooks:
                    if h.hook_id == hook_id:
                        h.enabled = False
                        return True
            return False


# =============================================================================
# Hook Engine
# =============================================================================
class HookEngine:
    """Execute hook chains around operations."""

    def __init__(self, registry: HookRegistry) -> None:
        self.registry = registry
        self._error_handlers: List[Callable[[HookContext], None]] = []

    def on_error(self, handler: Callable[[HookContext], None]) -> None:
        self._error_handlers.append(handler)

    def execute(self, operation: str, agent_id: str, parameters: Dict[str, Any], fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Tuple[Any, Optional[Exception]]:
        ctx = HookContext(
            operation=operation,
            agent_id=agent_id,
            parameters=parameters,
            start_time=time.time(),
        )
        # Run BEFORE hooks
        for hook in self.registry.get_hooks(HookPhase.BEFORE):
            if hook.should_run(ctx):
                try:
                    hook.run(ctx)
                except Exception as exc:
                    ctx.error = exc
                    for h in self.registry.get_hooks(HookPhase.ON_ERROR):
                        if h.should_run(ctx):
                            h.run(ctx)
                    for eh in self._error_handlers:
                        eh(ctx)
                    return None, exc
            if ctx.cancelled or ctx.skip_remaining:
                return None, ctx.error

        # Run AROUND hooks (wrap the function)
        around_hooks = self.registry.get_hooks(HookPhase.AROUND)
        if around_hooks:
            def wrapped() -> Any:
                return fn(*args, **kwargs)
            for hook in reversed(around_hooks):
                if hook.should_run(ctx):
                    original = wrapped
                    def make_wrapper(h: BaseHook, orig: Callable[[], Any]) -> Callable[[], Any]:
                        def wrapper() -> Any:
                            h.run(ctx)
                            return orig()
                        return wrapper
                    wrapped = make_wrapper(hook, original)
            try:
                ctx.result = wrapped()
            except Exception as exc:
                ctx.error = exc
        else:
            try:
                ctx.result = fn(*args, **kwargs)
            except Exception as exc:
                ctx.error = exc

        # Run AFTER hooks
        for hook in self.registry.get_hooks(HookPhase.AFTER):
            if hook.should_run(ctx):
                try:
                    hook.run(ctx)
                except Exception:
                    pass

        # Error handling
        if ctx.error:
            for hook in self.registry.get_hooks(HookPhase.ON_ERROR):
                if hook.should_run(ctx):
                    try:
                        hook.run(ctx)
                    except Exception:
                        pass
            for eh in self._error_handlers:
                eh(ctx)
            return None, ctx.error

        return ctx.result, None

    def execute_simple(self, operation: str, agent_id: str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        result, error = self.execute(operation, agent_id, {}, fn, *args, **kwargs)
        if error:
            raise error
        return result


# =============================================================================
# Hook Kernel Bridge
# =============================================================================
class HookKernelBridge:
    def __init__(self, engine: HookEngine, event_bus: Any = None) -> None:
        self.engine = engine
        self.bus = event_bus
        engine.on_error(self._on_error)

    def _on_error(self, ctx: HookContext) -> None:
        if self.bus:
            self.bus.publish("hook.error", {
                "operation": ctx.operation,
                "agent_id": ctx.agent_id,
                "error": str(ctx.error) if ctx.error else "",
            })


# =============================================================================
# Demo
# =============================================================================
def run_demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Hooks Engine Demo")
    print("=" * 60)
    registry = HookRegistry()
    engine = HookEngine(registry)

    # Register hooks
    log_hook = LoggingHook()
    registry.register(log_hook)

    rate_hook = RateLimitHook(max_calls=3, window_sec=10.0)
    registry.register(rate_hook)

    metrics_hook = MetricsHook()
    registry.register(metrics_hook)

    val_hook = ValidationHook({"required": ["input"]})
    registry.register(val_hook)

    def sample_op(input: str) -> str:
        return f"Processed: {input}"

    # Valid call
    result, err = engine.execute("process", "agent-1", {"input": "hello"}, sample_op, "hello")
    print(f"Valid: result={result}, err={err}")

    # Invalid call (missing required param)
    result, err = engine.execute("process", "agent-1", {}, sample_op, "hello")
    print(f"Invalid: err={err}")

    # Rate limit test
    for i in range(5):
        result, err = engine.execute("process", "agent-1", {"input": f"test-{i}"}, sample_op, f"test-{i}")
        print(f"  Call {i+1}: {'OK' if not err else f'RATE LIMITED: {err}'}")

    # Metrics
    print(f"Metrics: {metrics_hook.get_metrics()}")
    print("Demo complete.")


if __name__ == "__main__":
    run_demo()
