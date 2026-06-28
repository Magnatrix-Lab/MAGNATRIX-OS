#!/usr/bin/env python3
"""vnpy Gateway Adapter for MAGNATRIX-OS."""
from __future__ import annotations
import hashlib, time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

@dataclass
class GatewayConfig:
    gateway_name: str
    broker_type: str  # "ctp", "ib", "binance", "rqdata", "tushare"
    api_key: str = ""
    api_secret: str = ""
    endpoint: str = ""
    symbols: List[str] = field(default_factory=list)
    def to_dict(self): return asdict(self)

class GatewayBase:
    def __init__(self, config: GatewayConfig):
        self.config = config
        self.connected = False
    def connect(self) -> bool:
        self.connected = True
        return True
    def disconnect(self):
        self.connected = False
    def subscribe(self, symbols: List[str]) -> bool:
        return True
    def send_order(self, symbol: str, direction: str, price: float, volume: float) -> str:
        return f"order_{hashlib.md5(f'{symbol}{time.time()}'.encode()).hexdigest()[:16]}"
    def cancel_order(self, order_id: str) -> bool:
        return True
    def query_position(self) -> Dict[str, Any]:
        return {}
    def query_account(self) -> Dict[str, Any]:
        return {}

class CTPGateway(GatewayBase):
    def __init__(self, config: GatewayConfig):
        super().__init__(config)
    def connect(self) -> bool:
        # Simulate CTP futures connection
        return super().connect()
    def query_position(self) -> Dict[str, Any]:
        return {"gateway": "CTP", "positions": []}

class InteractiveBrokersGateway(GatewayBase):
    def __init__(self, config: GatewayConfig):
        super().__init__(config)
    def connect(self) -> bool:
        return super().connect()
    def query_account(self) -> Dict[str, Any]:
        return {"gateway": "IB", "balance": 100000.0}

class BinanceGateway(GatewayBase):
    def __init__(self, config: GatewayConfig):
        super().__init__(config)
    def send_order(self, symbol: str, direction: str, price: float, volume: float) -> str:
        return super().send_order(symbol, direction, price, volume)

class vnpyGatewayAdapter:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.gateways: Dict[str, GatewayBase] = {}
        self._gateway_map = {
            "ctp": CTPGateway,
            "ib": InteractiveBrokersGateway,
            "binance": BinanceGateway,
        }
    def add_gateway(self, config: GatewayConfig) -> GatewayBase:
        cls = self._gateway_map.get(config.broker_type, GatewayBase)
        gw = cls(config)
        self.gateways[config.gateway_name] = gw
        return gw
    def connect_all(self) -> Dict[str, bool]:
        return {name: gw.connect() for name, gw in self.gateways.items()}
    def to_dict(self): return {"gateways": len(self.gateways)}
