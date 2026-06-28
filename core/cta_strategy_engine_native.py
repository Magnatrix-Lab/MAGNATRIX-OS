#!/usr/bin/env python3
"""CTA Strategy Engine for MAGNATRIX-OS."""
from __future__ import annotations
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

class CTAStrategy:
    def __init__(self, strategy_name: str, symbols: List[str]):
        self.strategy_name = strategy_name
        self.symbols = symbols
        self.positions: Dict[str, float] = {}
        self.orders: List[Dict[str, Any]] = []
        self.active = False
    def on_init(self): pass
    def on_start(self): self.active = True
    def on_tick(self, tick: Dict[str, Any]): pass
    def on_bar(self, bar: Dict[str, Any]): pass
    def on_order(self, order: Dict[str, Any]): pass
    def on_stop(self): self.active = False
    def buy(self, symbol: str, price: float, volume: float) -> str:
        order = {"symbol": symbol, "direction": "buy", "price": price, "volume": volume, "time": time.time()}
        self.orders.append(order)
        return f"buy_{len(self.orders)}"
    def sell(self, symbol: str, price: float, volume: float) -> str:
        order = {"symbol": symbol, "direction": "sell", "price": price, "volume": volume, "time": time.time()}
        self.orders.append(order)
        return f"sell_{len(self.orders)}"
    def to_dict(self):
        return {"name": self.strategy_name, "active": self.active, "orders": len(self.orders)}

class CTAStrategyEngine:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.strategies: Dict[str, CTAStrategy] = {}
    def add_strategy(self, strategy: CTAStrategy) -> str:
        self.strategies[strategy.strategy_name] = strategy
        return strategy.strategy_name
    def start_all(self):
        for s in self.strategies.values():
            s.on_init()
            s.on_start()
    def stop_all(self):
        for s in self.strategies.values():
            s.on_stop()
    def on_tick(self, tick: Dict[str, Any]):
        for s in self.strategies.values():
            if s.active:
                s.on_tick(tick)
    def on_bar(self, bar: Dict[str, Any]):
        for s in self.strategies.values():
            if s.active:
                s.on_bar(bar)
    def to_dict(self): return {"strategies": len(self.strategies)}
