"""MAGNATRIX-OS Framework Facade
═════════════════════════════════
Unified import surface for MAGNATRIX-OS.

Usage:
    import magnatrix as mx

    @mx.agent(name="trader")
    class MyTrader:
        pass

    @mx.skill("market_analysis")
    def analyze(ctx, symbol: str) -> dict:
        return {"trend": "up"}

    app = mx.create_app()
    app.boot()

Pure Python ≥3.11. All imports are lazy to avoid circular deps.
"""
from __future__ import annotations

import functools
import importlib
import inspect
import json
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type


# ── Version ────────────────────────────────────────────────────────────────
__version__ = "0.9.5-alpha"
__author__ = "Magnatrix Lab"
__license__ = "MIT"


# ── Lazy module cache ──────────────────────────────────────────────────────
_module_cache: Dict[str, Any] = {}


def _lazy_import(module_path: str, name: str) -> Any:
    """Lazy import with cache — avoids loading everything on `import magnatrix`."""
    key = f"{module_path}.{name}"
    if key not in _module_cache:
        try:
            mod = importlib.import_module(module_path)
            _module_cache[key] = getattr(mod, name)
        except Exception as e:
            _module_cache[key] = None
    return _module_cache[key]


# ════════════════════════════════════════════════════════════════════════════
# Framework Decorators
# ════════════════════════════════════════════════════════════════════════════

_registry: Dict[str, Dict[str, Any]] = {
    "agents": {},
    "skills": {},
    "tools": {},
    "workflows": {},
    "models": {},
    "providers": {},
}


def agent(name: Optional[str] = None, *, description: str = "", tags: Optional[List[str]] = None):
    """Register a class as a MAGNATRIX agent.

    Example:
        @mx.agent(name="arbitrage_bot", description="Cross-exchange HFT agent")
        class ArbitrageBot:
            def run(self, ctx): ...
    """
    def decorator(cls: Type) -> Type:
        key = name or cls.__name__
        _registry["agents"][key] = {
            "cls": cls,
            "name": key,
            "description": description or cls.__doc__ or "",
            "tags": tags or [],
            "module": cls.__module__,
        }
        cls._magnatrix_agent = key
        return cls
    return decorator


def skill(name: Optional[str] = None, *, description: str = "", tags: Optional[List[str]] = None):
    """Register a function as a MAGNATRIX skill.

    Example:
        @mx.skill("sentiment_analysis")
        def analyze_sentiment(ctx, text: str) -> float:
            return 0.8
    """
    def decorator(fn: Callable) -> Callable:
        key = name or fn.__name__
        _registry["skills"][key] = {
            "fn": fn,
            "name": key,
            "description": description or fn.__doc__ or "",
            "tags": tags or [],
            "sig": inspect.signature(fn),
        }
        fn._magnatrix_skill = key
        return fn
    return decorator


def tool(name: Optional[str] = None, *, description: str = "", tags: Optional[List[str]] = None):
    """Register a function as an external tool.

    Alias for `@skill` — semantically separate for external integrations.
    """
    def decorator(fn: Callable) -> Callable:
        key = name or fn.__name__
        _registry["tools"][key] = {
            "fn": fn,
            "name": key,
            "description": description or fn.__doc__ or "",
            "tags": tags or [],
            "sig": inspect.signature(fn),
        }
        fn._magnatrix_tool = key
        return fn
    return decorator


def workflow(name: Optional[str] = None, *, description: str = ""):
    """Register a workflow function or class.

    Example:
        @mx.workflow("daily_report")
        def daily_report(ctx):
            data = ctx.skills["market_data"](ctx, "BTC")
            return ctx.agents["writer"].run(ctx, data)
    """
    def decorator(obj: Any) -> Any:
        key = name or getattr(obj, "__name__", obj.__class__.__name__)
        _registry["workflows"][key] = {
            "obj": obj,
            "name": key,
            "description": description or getattr(obj, "__doc__", "") or "",
        }
        return obj
    return decorator


def model(name: Optional[str] = None, *, provider: str = "local", config: Optional[Dict] = None):
    """Register an LLM model configuration.

    Example:
        @mx.model("llama3-70b", provider="local", config={"gguf_path": "..."})
        class Llama3Model:
            pass
    """
    def decorator(cls: Type) -> Type:
        key = name or cls.__name__
        _registry["models"][key] = {
            "cls": cls,
            "name": key,
            "provider": provider,
            "config": config or {},
        }
        cls._magnatrix_model = key
        return cls
    return decorator


def provider(name: Optional[str] = None, *, tier: int = 1):
    """Register an LLM provider adapter.

    Example:
        @mx.provider("groq", tier=2)
        class GroqProvider:
            pass
    """
    def decorator(cls: Type) -> Type:
        key = name or cls.__name__
        _registry["providers"][key] = {
            "cls": cls,
            "name": key,
            "tier": tier,
        }
        cls._magnatrix_provider = key
        return cls
    return decorator


# ════════════════════════════════════════════════════════════════════════════
# Registry introspection
# ════════════════════════════════════════════════════════════════════════════

class Registry:
    """Introspect and invoke registered framework objects."""

    @classmethod
    def list_agents(cls) -> List[Dict[str, Any]]:
        return [{"name": k, **{x: v[x] for x in v if x != "cls" and x != "fn"}}
                for k, v in _registry["agents"].items()]

    @classmethod
    def list_skills(cls) -> List[Dict[str, Any]]:
        return [{"name": k, **{x: v[x] for x in v if x != "fn" and x != "sig"}}
                for k, v in _registry["skills"].items()]

    @classmethod
    def list_tools(cls) -> List[Dict[str, Any]]:
        return [{"name": k, **{x: v[x] for x in v if x != "fn" and x != "sig"}}
                for k, v in _registry["tools"].items()]

    @classmethod
    def list_workflows(cls) -> List[Dict[str, Any]]:
        return [{"name": k, **{x: v[x] for x in v if x != "obj"}}
                for k, v in _registry["workflows"].items()]

    @classmethod
    def get_agent(cls, name: str) -> Optional[Type]:
        entry = _registry["agents"].get(name)
        return entry["cls"] if entry else None

    @classmethod
    def get_skill(cls, name: str) -> Optional[Callable]:
        entry = _registry["skills"].get(name)
        return entry["fn"] if entry else None

    @classmethod
    def get_tool(cls, name: str) -> Optional[Callable]:
        entry = _registry["tools"].get(name)
        return entry["fn"] if entry else None

    @classmethod
    def get_workflow(cls, name: str) -> Optional[Any]:
        entry = _registry["workflows"].get(name)
        return entry["obj"] if entry else None


# ════════════════════════════════════════════════════════════════════════════
# Application Context (runtime container)
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class AppConfig:
    """Framework-level configuration."""
    data_dir: str = field(default_factory=lambda: os.path.join(
        os.path.expanduser("~"), ".magnatrix-os"))
    log_level: str = "INFO"
    enable_tray: bool = True
    dashboard_port: int = 8080
    boot_layers: List[str] = field(default_factory=lambda: [
        "kernel", "protocol", "api_router", "identity", "runtime",
        "p2p_mesh", "knowledge", "skills", "browser", "trading",
        "security", "ai", "governance", "ide", "uncensored",
    ])


class AppContext:
    """Runtime context holding kernel, agents, skills, and configuration.

    This is the main handle users interact with after `create_app()`.
    """

    def __init__(self, config: Optional[AppConfig] = None) -> None:
        self.config = config or AppConfig()
        self.kernel: Optional[Any] = None
        self._running = False
        self._agents: Dict[str, Any] = {}
        self._skills: Dict[str, Callable] = {}
        self._tools: Dict[str, Callable] = {}
        os.makedirs(self.config.data_dir, exist_ok=True)

    # ── Property accessors ────────────────────────────────────────────────
    @property
    def agents(self) -> Dict[str, Any]:
        return self._agents

    @property
    def skills(self) -> Dict[str, Callable]:
        return self._skills

    @property
    def tools(self) -> Dict[str, Callable]:
        return self._tools

    @property
    def running(self) -> bool:
        return self._running

    # ── Boot / lifecycle ──────────────────────────────────────────────────
    def boot(self) -> bool:
        """Boot the kernel and instantiate registered agents."""
        KernelNative = _lazy_import("kernel.kernel_native", "KernelNative")
        KernelConfig = _lazy_import("kernel.kernel_native", "KernelConfig")
        BootMode = _lazy_import("kernel.kernel_native", "BootMode")

        if KernelNative is None:
            print("[MAGNATRIX] KernelNative not available — degraded boot")
            self._running = True
            return False

        cfg = KernelConfig(
            workspace_dir=self.config.data_dir,
            boot_mode=BootMode.COLD if BootMode else None,
            log_level=self.config.log_level,
        )
        self.kernel = KernelNative(cfg)
        ok = self.kernel.boot()
        self._running = ok

        # Instantiate registered agents
        for name, meta in _registry["agents"].items():
            try:
                self._agents[name] = meta["cls"]()
            except Exception as e:
                print(f"[MAGNATRIX] Agent {name} init failed: {e}")

        # Bind skills
        for name, meta in _registry["skills"].items():
            self._skills[name] = functools.partial(meta["fn"], self)

        # Bind tools
        for name, meta in _registry["tools"].items():
            self._tools[name] = functools.partial(meta["fn"], self)

        print(f"[MAGNATRIX] Boot complete — {len(self._agents)} agents, {len(self._skills)} skills, {len(self._tools)} tools")
        return ok

    def shutdown(self) -> None:
        """Graceful shutdown."""
        self._running = False
        if self.kernel:
            try:
                self.kernel.shutdown()
            except Exception as e:
                print(f"[MAGNATRIX] Kernel shutdown error: {e}")
        print("[MAGNATRIX] Shutdown complete")

    def agent_run(self, name: str, *args, **kwargs) -> Any:
        """Run a registered agent by name."""
        a = self._agents.get(name)
        if a is None:
            raise KeyError(f"Agent '{name}' not found")
        run_fn = getattr(a, "run", getattr(a, "execute", None))
        if run_fn is None:
            raise AttributeError(f"Agent '{name}' has no run()/execute()")
        return run_fn(self, *args, **kwargs)

    def skill_call(self, name: str, *args, **kwargs) -> Any:
        """Call a registered skill by name."""
        s = self._skills.get(name)
        if s is None:
            raise KeyError(f"Skill '{name}' not found")
        return s(*args, **kwargs)

    def workflow_run(self, name: str, *args, **kwargs) -> Any:
        """Run a registered workflow by name."""
        w = Registry.get_workflow(name)
        if w is None:
            raise KeyError(f"Workflow '{name}' not found")
        if callable(w):
            return w(self, *args, **kwargs)
        run_fn = getattr(w, "run", getattr(w, "execute", None))
        if run_fn is None:
            raise AttributeError(f"Workflow '{name}' has no run()/execute()")
        return run_fn(*args, **kwargs)


# ════════════════════════════════════════════════════════════════════════════
# Factory
# ════════════════════════════════════════════════════════════════════════════

def create_app(config: Optional[AppConfig] = None) -> AppContext:
    """Factory: create and return a boot-ready AppContext.

    Example:
        app = mx.create_app(mx.AppConfig(dashboard_port=9090))
        app.boot()
        result = app.agent_run("trader", symbol="BTC")
        app.shutdown()
    """
    return AppContext(config)


# ════════════════════════════════════════════════════════════════════════════
# Backwards-compatible CLI re-export
# ════════════════════════════════════════════════════════════════════════════

def main() -> int:
    """Delegate to legacy magnatrix_main.py CLI."""
    try:
        from magnatrix_main import main as _legacy_main
        return _legacy_main()
    except Exception as e:
        print(f"[MAGNATRIX] CLI error: {e}")
        return 1


def magnatrix_boot() -> int:
    """Entry point: mx-boot."""
    return main()


def magnatrix_status() -> int:
    """Entry point: mx-status."""
    try:
        from magnatrix_main import MagnatrixOS, VersionInfo
        mx = MagnatrixOS(VersionInfo())
        mx.show_dashboard()
        return 0
    except Exception as e:
        print(f"[MAGNATRIX] Status error: {e}")
        return 1


def magnatrix_shutdown() -> int:
    """Entry point: mx-shutdown."""
    try:
        from magnatrix_main import MagnatrixOS, VersionInfo
        mx = MagnatrixOS(VersionInfo())
        mx.shutdown()
        return 0
    except Exception as e:
        print(f"[MAGNATRIX] Shutdown error: {e}")
        return 1


# ════════════════════════════════════════════════════════════════════════════
# Public API surface
# ════════════════════════════════════════════════════════════════════════════
__all__ = [
    # Meta
    "__version__", "__author__", "__license__",
    # Decorators
    "agent", "skill", "tool", "workflow", "model", "provider",
    # Registry
    "Registry",
    # Runtime
    "AppConfig", "AppContext", "create_app",
    # CLI
    "main", "magnatrix_boot", "magnatrix_status", "magnatrix_shutdown",
]


# ── Self-test ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    @agent(name="demo_agent", description="Framework self-test agent")
    class DemoAgent:
        def run(self, ctx):
            return "Hello from DemoAgent"

    @skill("greet")
    def greet(ctx, name: str) -> str:
        return f"Hello, {name}!"

    @workflow("hello_pipeline")
    def hello_pipeline(ctx):
        msg = ctx.skills["greet"]("Framework")
        return msg

    print(f"MAGNATRIX-OS Framework v{__version__}")
    print(f"Agents: {Registry.list_agents()}")
    print(f"Skills: {Registry.list_skills()}")
    print(f"Workflows: {Registry.list_workflows()}")

    app = create_app()
    # Degraded boot (no kernel in isolated env)
    app.boot()
    print(hello_pipeline(app))
    app.shutdown()
