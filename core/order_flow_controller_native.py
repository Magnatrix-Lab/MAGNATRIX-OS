#!/usr/bin/env python3
"""Order Flow Controller for MAGNATRIX-OS."""
from __future__ import annotations
import time
from typing import Any, Dict, List, Optional

class OrderFlowController:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.max_orders_per_second = 10
        self.max_position_size = 100
        self.max_daily_loss = 1000.0
        self.order_history: List[Dict[str, Any]] = []
        self.position_sizes: Dict[str, float] = {}
        self.daily_pnl = 0.0
    def check_rate_limit(self) -> bool:
        now = time.time()
        recent = [o for o in self.order_history if now - o["time"] < 1.0]
        return len(recent) < self.max_orders_per_second
    def check_position_limit(self, symbol: str, new_size: float) -> bool:
        current = self.position_sizes.get(symbol, 0)
        return abs(current + new_size) <= self.max_position_size
    def check_loss_limit(self, pnl: float) -> bool:
        self.daily_pnl += pnl
        return self.daily_pnl > -self.max_daily_loss
    def submit_order(self, symbol: str, direction: str, price: float, volume: float) -> Dict[str, Any]:
        if not self.check_rate_limit():
            return {"approved": False, "reason": "rate_limit_exceeded"}
        if not self.check_position_limit(symbol, volume if direction == "buy" else -volume):
            return {"approved": False, "reason": "position_limit_exceeded"}
        self.order_history.append({"symbol": symbol, "direction": direction, "volume": volume, "time": time.time()})
        self.position_sizes[symbol] = self.position_sizes.get(symbol, 0) + (volume if direction == "buy" else -volume)
        return {"approved": True, "order_id": f"ofc_{len(self.order_history)}"}
    def to_dict(self): return {"orders": len(self.order_history), "positions": len(self.position_sizes)}
