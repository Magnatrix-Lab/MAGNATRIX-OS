"""Fallback Engine — graceful degradation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Any, Optional
from enum import Enum, auto
import time

class FallbackStrategy(Enum):
    STATIC = auto()
    CACHE = auto()
    DEFAULT_VALUE = auto()
    ALTERNATIVE = auto()

@dataclass
class FallbackConfig:
    strategy: FallbackStrategy
    fallback_value: Any = None
    alternative_func: Optional[Callable] = None
    cache_key: Optional[str] = None

class FallbackEngine:
    def __init__(self):
        self.fallbacks: Dict[str, FallbackConfig] = {}
        self.cache: Dict[str, Any] = {}
        self.history: List[Dict] = []

    def register(self, operation_id: str, config: FallbackConfig):
        self.fallbacks[operation_id] = config

    def execute(self, operation_id: str, primary_func: Callable, *args, **kwargs) -> Any:
        try:
            result = primary_func(*args, **kwargs)
            self.history.append({"op": operation_id, "primary": True, "time": time.time()})
            return result
        except Exception as e:
            config = self.fallbacks.get(operation_id)
            if not config:
                raise e
            self.history.append({"op": operation_id, "primary": False, "fallback": config.strategy.name, "time": time.time()})
            if config.strategy == FallbackStrategy.STATIC:
                return config.fallback_value
            elif config.strategy == FallbackStrategy.DEFAULT_VALUE:
                return config.fallback_value
            elif config.strategy == FallbackStrategy.CACHE and config.cache_key:
                return self.cache.get(config.cache_key, config.fallback_value)
            elif config.strategy == FallbackStrategy.ALTERNATIVE and config.alternative_func:
                return config.alternative_func(*args, **kwargs)
            return config.fallback_value

    def cache_result(self, key: str, value: Any):
        self.cache[key] = value

    def stats(self) -> Dict:
        primary = sum(1 for h in self.history if h.get("primary"))
        fallback = sum(1 for h in self.history if not h.get("primary"))
        return {"operations": len(self.fallbacks), "primary": primary, "fallback": fallback, "cache_size": len(self.cache)}

def run():
    engine = FallbackEngine()
    engine.register("fetch", FallbackConfig(FallbackStrategy.STATIC, fallback_value={"cached": True}))
    def fail():
        raise ValueError("service down")
    def success():
        return {"data": "live"}
    print(engine.execute("fetch", fail))
    print(engine.execute("fetch", success))
    print(engine.stats())

if __name__ == "__main__":
    run()
