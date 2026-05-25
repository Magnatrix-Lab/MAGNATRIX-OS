"""
trading/exchange_adapter_native.py
MAGNATRIX-OS Layer 8 — Cryptocurrency Exchange Adapter
Native pure-Python REST + WebSocket stubs for Binance, Bybit, OKX.
HMAC-SHA256 signing, rate-limiting, order lifecycle, position tracking.
Zero external dependencies.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
import threading
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Callable


# ── Data Models ─────────────────────────────────────────

class OrderSide(Enum):
    BUY = auto()
    SELL = auto()


class OrderType(Enum):
    MARKET = auto()
    LIMIT = auto()
    STOP_LOSS = auto()
    TAKE_PROFIT = auto()
    STOP_LOSS_LIMIT = auto()
    TAKE_PROFIT_LIMIT = auto()


class OrderStatus(Enum):
    PENDING = auto()
    OPEN = auto()
    PARTIALLY_FILLED = auto()
    FILLED = auto()
    CANCELLED = auto()
    REJECTED = auto()
    EXPIRED = auto()


class TimeInForce(Enum):
    GTC = "GTC"   # Good Till Cancelled
    IOC = "IOC"   # Immediate Or Cancel
    FOK = "FOK"   # Fill Or Kill
    GTD = "GTD"   # Good Till Date


@dataclass
class Order:
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: TimeInForce = TimeInForce.GTC
    client_order_id: str = field(default_factory=lambda: f"mx_{int(time.time()*1000)}")
    status: OrderStatus = OrderStatus.PENDING
    filled_qty: float = 0.0
    avg_fill_price: float = 0.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    exchange_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side.name,
            "type": self.order_type.name,
            "quantity": self.quantity,
            "price": self.price,
            "stop_price": self.stop_price,
            "time_in_force": self.time_in_force.value,
            "client_order_id": self.client_order_id,
            "status": self.status.name,
            "filled_qty": self.filled_qty,
            "avg_fill_price": self.avg_fill_price,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "exchange_id": self.exchange_id,
        }


@dataclass
class Balance:
    asset: str
    free: float
    locked: float
    total: float
    updated_at: float = field(default_factory=time.time)


@dataclass
class Position:
    symbol: str
    side: OrderSide          # BUY=long, SELL=short
    size: float
    entry_price: float
    unrealized_pnl: float
    leverage: float = 1.0
    liquidation_price: Optional[float] = None
    margin_mode: str = "isolated"   # isolated / cross
    updated_at: float = field(default_factory=time.time)


@dataclass
class Ticker:
    symbol: str
    last_price: float
    bid: float
    ask: float
    volume_24h: float
    high_24h: float
    low_24h: float
    change_24h: float
    change_pct_24h: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class Candle:
    symbol: str
    interval: str          # 1m, 5m, 15m, 1h, 4h, 1d
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: float


@dataclass
class TradeFill:
    trade_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    fee: float
    fee_asset: str
    timestamp: float


# ── Rate Limiter ────────────────────────────────────────

class RateLimiter:
    """Token-bucket rate limiter per endpoint weight."""

    def __init__(self, max_weight: int = 1200, window_sec: float = 60.0) -> None:
        self.max_weight = max_weight
        self.window_sec = window_sec
        self._tokens = float(max_weight)
        self._last_refill = time.time()
        self._lock = threading.Lock()

    def acquire(self, weight: int = 1, block: bool = True, timeout: float = 5.0) -> bool:
        deadline = time.time() + timeout
        while True:
            with self._lock:
                now = time.time()
                elapsed = now - self._last_refill
                self._tokens = min(self.max_weight, self._tokens + elapsed * (self.max_weight / self.window_sec))
                self._last_refill = now
                if self._tokens >= weight:
                    self._tokens -= weight
                    return True
                if not block:
                    return False
            remaining = deadline - time.time()
            if remaining <= 0:
                return False
            sleep_time = max(0.01, (weight - self._tokens) / (self.max_weight / self.window_sec))
            time.sleep(min(sleep_time, remaining * 0.5))

    @property
    def tokens(self) -> float:
        with self._lock:
            now = time.time()
            self._tokens = min(self.max_weight, self._tokens + (now - self._last_refill) * (self.max_weight / self.window_sec))
            self._last_refill = now
            return self._tokens


# ── Base Exchange Adapter ───────────────────────────────

class ExchangeAdapter(ABC):
    """Abstract base for all exchange adapters."""

    def __init__(self, name: str, api_key: str = "", api_secret: str = "", base_url: str = "", testnet: bool = False) -> None:
        self.name = name
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.testnet = testnet
        self.rate_limiter = RateLimiter()
        self._connected = False
        self._orders: Dict[str, Order] = {}
        self._balances: Dict[str, Balance] = {}
        self._positions: Dict[str, Position] = {}
        self._tickers: Dict[str, Ticker] = {}
        self._candles: Dict[str, List[Candle]] = {}
        self._callbacks: Dict[str, List[Callable[..., None]]] = {}
        self._lock = threading.Lock()

    @abstractmethod
    def connect(self) -> bool: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def place_order(self, order: Order) -> Dict[str, Any]: ...

    @abstractmethod
    def cancel_order(self, symbol: str, client_order_id: str) -> Dict[str, Any]: ...

    @abstractmethod
    def get_order(self, symbol: str, client_order_id: str) -> Optional[Order]: ...

    @abstractmethod
    def get_balance(self, asset: str) -> Optional[Balance]: ...

    @abstractmethod
    def get_position(self, symbol: str) -> Optional[Position]: ...

    @abstractmethod
    def get_ticker(self, symbol: str) -> Optional[Ticker]: ...

    @abstractmethod
    def get_candles(self, symbol: str, interval: str, limit: int = 100) -> List[Candle]: ...

    def on(self, event: str, callback: Callable[..., None]) -> None:
        self._callbacks.setdefault(event, []).append(callback)

    def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        for cb in self._callbacks.get(event, []):
            try:
                cb(*args, **kwargs)
            except Exception:
                traceback.print_exc()

    def is_connected(self) -> bool:
        return self._connected

    def _sign_hmac(self, payload: str, secret: str) -> str:
        return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

    def _timestamp_ms(self) -> int:
        return int(time.time() * 1000)

    def _stub_response(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate a realistic stub response for testing without real API."""
        return {
            "stub": True,
            "method": method,
            "params": params,
            "timestamp": self._timestamp_ms(),
            "exchange": self.name,
        }


# ── Binance Adapter ─────────────────────────────────────

class BinanceAdapter(ExchangeAdapter):
    """Binance Spot + USDM-Futures adapter (REST stubs)."""

    def __init__(self, api_key: str = "", api_secret: str = "", testnet: bool = False) -> None:
        base = "https://testnet.binance.vision" if testnet else "https://api.binance.com"
        super().__init__("binance", api_key, api_secret, base, testnet)
        self.futures_url = "https://testnet.binancefuture.com" if testnet else "https://fapi.binance.com"

    def connect(self) -> bool:
        self._connected = True
        self.emit("connected", self.name)
        return True

    def disconnect(self) -> None:
        self._connected = False
        self.emit("disconnected", self.name)

    def place_order(self, order: Order) -> Dict[str, Any]:
        self.rate_limiter.acquire(weight=1)
        if not self._connected:
            return {"error": "not_connected"}
        ts = self._timestamp_ms()
        params = {
            "symbol": order.symbol.upper(),
            "side": order.side.name,
            "type": order.order_type.name,
            "quantity": order.quantity,
            "newClientOrderId": order.client_order_id,
            "timestamp": ts,
        }
        if order.price is not None:
            params["price"] = order.price
        if order.time_in_force != TimeInForce.GTC:
            params["timeInForce"] = order.time_in_force.value
        # HMAC signature
        query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        signature = self._sign_hmac(query, self.api_secret)
        params["signature"] = signature

        order.exchange_id = f"BNB_{ts}"
        order.status = OrderStatus.OPEN
        with self._lock:
            self._orders[order.client_order_id] = order
        self.emit("order_placed", order)
        return {
            "orderId": order.exchange_id,
            "clientOrderId": order.client_order_id,
            "status": "NEW",
            "stub": True,
        }

    def cancel_order(self, symbol: str, client_order_id: str) -> Dict[str, Any]:
        self.rate_limiter.acquire(weight=1)
        with self._lock:
            order = self._orders.get(client_order_id)
            if order:
                order.status = OrderStatus.CANCELLED
        return {"clientOrderId": client_order_id, "status": "CANCELED", "stub": True}

    def get_order(self, symbol: str, client_order_id: str) -> Optional[Order]:
        self.rate_limiter.acquire(weight=1)
        with self._lock:
            return self._orders.get(client_order_id)

    def get_balance(self, asset: str) -> Optional[Balance]:
        self.rate_limiter.acquire(weight=5)
        bal = Balance(asset=asset.upper(), free=1000.0, locked=0.0, total=1000.0)
        with self._lock:
            self._balances[asset.upper()] = bal
        return bal

    def get_position(self, symbol: str) -> Optional[Position]:
        self.rate_limiter.acquire(weight=5)
        pos = Position(
            symbol=symbol.upper(),
            side=OrderSide.BUY,
            size=0.0,
            entry_price=0.0,
            unrealized_pnl=0.0,
            leverage=1.0,
        )
        with self._lock:
            self._positions[symbol.upper()] = pos
        return pos

    def get_ticker(self, symbol: str) -> Optional[Ticker]:
        self.rate_limiter.acquire(weight=1)
        ticker = Ticker(
            symbol=symbol.upper(),
            last_price=50000.0,
            bid=49999.5,
            ask=50000.5,
            volume_24h=15000.0,
            high_24h=51000.0,
            low_24h=49000.0,
            change_24h=500.0,
            change_pct_24h=1.01,
        )
        with self._lock:
            self._tickers[symbol.upper()] = ticker
        return ticker

    def get_candles(self, symbol: str, interval: str, limit: int = 100) -> List[Candle]:
        self.rate_limiter.acquire(weight=1)
        candles = []
        base_price = 50000.0
        now = time.time()
        interval_sec = self._interval_to_sec(interval)
        for i in range(limit):
            t = now - (limit - i) * interval_sec
            noise = (hash(f"{symbol}{i}") % 100 - 50) / 500.0
            o = base_price * (1 + noise)
            c = o * (1 + (hash(f"{symbol}{i}close") % 20 - 10) / 1000.0)
            h = max(o, c) * 1.001
            lo = min(o, c) * 0.999
            v = 100 + (hash(f"{symbol}{i}vol") % 900)
            candles.append(Candle(symbol=symbol.upper(), interval=interval, open=o, high=h, low=lo, close=c, volume=v, timestamp=t))
        with self._lock:
            self._candles[f"{symbol.upper()}_{interval}"] = candles
        return candles

    @staticmethod
    def _interval_to_sec(interval: str) -> int:
        mapping = {"1m": 60, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600, "4h": 14400, "1d": 86400}
        return mapping.get(interval, 3600)


# ── Bybit Adapter ───────────────────────────────────────

class BybitAdapter(ExchangeAdapter):
    """Bybit v5 unified margin adapter (REST stubs)."""

    def __init__(self, api_key: str = "", api_secret: str = "", testnet: bool = False) -> None:
        base = "https://api-testnet.bybit.com" if testnet else "https://api.bybit.com"
        super().__init__("bybit", api_key, api_secret, base, testnet)

    def connect(self) -> bool:
        self._connected = True
        self.emit("connected", self.name)
        return True

    def disconnect(self) -> None:
        self._connected = False
        self.emit("disconnected", self.name)

    def place_order(self, order: Order) -> Dict[str, Any]:
        self.rate_limiter.acquire(weight=1)
        if not self._connected:
            return {"error": "not_connected"}
        ts = str(self._timestamp_ms())
        payload = json.dumps({
            "category": "linear",
            "symbol": order.symbol.upper(),
            "side": "Buy" if order.side == OrderSide.BUY else "Sell",
            "orderType": "Market" if order.order_type == OrderType.MARKET else "Limit",
            "qty": str(order.quantity),
            "price": str(order.price) if order.price else "",
            "orderLinkId": order.client_order_id,
        })
        # Bybit v5 signature: timestamp+api_key+recv_window+payload
        recv_window = "5000"
        sign_str = f"{ts}{self.api_key}{recv_window}{payload}"
        signature = self._sign_hmac(sign_str, self.api_secret)

        order.exchange_id = f"BYB_{ts}"
        order.status = OrderStatus.OPEN
        with self._lock:
            self._orders[order.client_order_id] = order
        self.emit("order_placed", order)
        return {"orderId": order.exchange_id, "orderLinkId": order.client_order_id, "stub": True}

    def cancel_order(self, symbol: str, client_order_id: str) -> Dict[str, Any]:
        self.rate_limiter.acquire(weight=1)
        with self._lock:
            order = self._orders.get(client_order_id)
            if order:
                order.status = OrderStatus.CANCELLED
        return {"orderLinkId": client_order_id, "orderStatus": "Cancelled", "stub": True}

    def get_order(self, symbol: str, client_order_id: str) -> Optional[Order]:
        self.rate_limiter.acquire(weight=1)
        with self._lock:
            return self._orders.get(client_order_id)

    def get_balance(self, asset: str) -> Optional[Balance]:
        self.rate_limiter.acquire(weight=5)
        bal = Balance(asset=asset.upper(), free=500.0, locked=50.0, total=550.0)
        with self._lock:
            self._balances[asset.upper()] = bal
        return bal

    def get_position(self, symbol: str) -> Optional[Position]:
        self.rate_limiter.acquire(weight=1)
        pos = Position(
            symbol=symbol.upper(),
            side=OrderSide.BUY,
            size=0.5,
            entry_price=49500.0,
            unrealized_pnl=250.0,
            leverage=10.0,
            liquidation_price=45000.0,
        )
        with self._lock:
            self._positions[symbol.upper()] = pos
        return pos

    def get_ticker(self, symbol: str) -> Optional[Ticker]:
        self.rate_limiter.acquire(weight=1)
        ticker = Ticker(
            symbol=symbol.upper(),
            last_price=49800.0,
            bid=49799.0,
            ask=49801.0,
            volume_24h=8200.0,
            high_24h=50500.0,
            low_24h=49200.0,
            change_24h=-200.0,
            change_pct_24h=-0.4,
        )
        with self._lock:
            self._tickers[symbol.upper()] = ticker
        return ticker

    def get_candles(self, symbol: str, interval: str, limit: int = 100) -> List[Candle]:
        self.rate_limiter.acquire(weight=1)
        candles = []
        base = 49800.0
        now = time.time()
        interval_sec = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}.get(interval, 3600)
        for i in range(limit):
            t = now - (limit - i) * interval_sec
            noise = (hash(f"bybit{symbol}{i}") % 60 - 30) / 600.0
            o = base * (1 + noise)
            c = o * (1 + (hash(f"bybit{symbol}{i}c") % 16 - 8) / 800.0)
            h = max(o, c) * 1.0008
            lo = min(o, c) * 0.9992
            v = 50 + (hash(f"bybit{symbol}{i}v") % 450)
            candles.append(Candle(symbol=symbol.upper(), interval=interval, open=o, high=h, low=lo, close=c, volume=v, timestamp=t))
        return candles


# ── OKX Adapter ─────────────────────────────────────────

class OKXAdapter(ExchangeAdapter):
    """OKX (formerly OKEx) adapter (REST stubs)."""

    def __init__(self, api_key: str = "", api_secret: str = "", passphrase: str = "", testnet: bool = False) -> None:
        base = "https://www.okx.com"
        super().__init__("okx", api_key, api_secret, base, testnet)
        self.passphrase = passphrase

    def connect(self) -> bool:
        self._connected = True
        self.emit("connected", self.name)
        return True

    def disconnect(self) -> None:
        self._connected = False
        self.emit("disconnected", self.name)

    def _okx_sign(self, timestamp: str, method: str, path: str, body: str = "") -> Tuple[str, str, str]:
        message = timestamp + method.upper() + path + body
        signature = base64.b64encode(hmac.new(self.api_secret.encode(), message.encode(), hashlib.sha256).digest()).decode()
        return signature, timestamp, self.passphrase

    def place_order(self, order: Order) -> Dict[str, Any]:
        self.rate_limiter.acquire(weight=1)
        if not self._connected:
            return {"error": "not_connected"}
        ts = self._timestamp_ms()
        body = json.dumps({
            "instId": order.symbol.upper(),
            "tdMode": "cash" if order.order_type == OrderType.MARKET else "cross",
            "side": "buy" if order.side == OrderSide.BUY else "sell",
            "ordType": "market" if order.order_type == OrderType.MARKET else "limit",
            "sz": str(order.quantity),
            "px": str(order.price) if order.price else "",
            "clOrdId": order.client_order_id,
        })
        order.exchange_id = f"OKX_{ts}"
        order.status = OrderStatus.OPEN
        with self._lock:
            self._orders[order.client_order_id] = order
        self.emit("order_placed", order)
        return {"ordId": order.exchange_id, "clOrdId": order.client_order_id, "stub": True}

    def cancel_order(self, symbol: str, client_order_id: str) -> Dict[str, Any]:
        self.rate_limiter.acquire(weight=1)
        with self._lock:
            order = self._orders.get(client_order_id)
            if order:
                order.status = OrderStatus.CANCELLED
        return {"clOrdId": client_order_id, "sCode": "0", "stub": True}

    def get_order(self, symbol: str, client_order_id: str) -> Optional[Order]:
        self.rate_limiter.acquire(weight=1)
        with self._lock:
            return self._orders.get(client_order_id)

    def get_balance(self, asset: str) -> Optional[Balance]:
        self.rate_limiter.acquire(weight=2)
        bal = Balance(asset=asset.upper(), free=750.0, locked=25.0, total=775.0)
        with self._lock:
            self._balances[asset.upper()] = bal
        return bal

    def get_position(self, symbol: str) -> Optional[Position]:
        self.rate_limiter.acquire(weight=2)
        pos = Position(
            symbol=symbol.upper(),
            side=OrderSide.SELL,
            size=0.3,
            entry_price=50200.0,
            unrealized_pnl=-60.0,
            leverage=5.0,
            liquidation_price=53000.0,
        )
        with self._lock:
            self._positions[symbol.upper()] = pos
        return pos

    def get_ticker(self, symbol: str) -> Optional[Ticker]:
        self.rate_limiter.acquire(weight=1)
        ticker = Ticker(
            symbol=symbol.upper(),
            last_price=50100.0,
            bid=50099.0,
            ask=50101.0,
            volume_24h=6700.0,
            high_24h=50800.0,
            low_24h=49600.0,
            change_24h=300.0,
            change_pct_24h=0.6,
        )
        with self._lock:
            self._tickers[symbol.upper()] = ticker
        return ticker

    def get_candles(self, symbol: str, interval: str, limit: int = 100) -> List[Candle]:
        self.rate_limiter.acquire(weight=1)
        candles = []
        base = 50100.0
        now = time.time()
        interval_sec = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}.get(interval, 3600)
        for i in range(limit):
            t = now - (limit - i) * interval_sec
            noise = (hash(f"okx{symbol}{i}") % 50 - 25) / 500.0
            o = base * (1 + noise)
            c = o * (1 + (hash(f"okx{symbol}{i}c") % 14 - 7) / 700.0)
            h = max(o, c) * 1.0006
            lo = min(o, c) * 0.9994
            v = 75 + (hash(f"okx{symbol}{i}v") % 375)
            candles.append(Candle(symbol=symbol.upper(), interval=interval, open=o, high=h, low=lo, close=c, volume=v, timestamp=t))
        return candles


# ── WebSocket Streaming Stub ───────────────────────────

class WebSocketStreamStub:
    """Stub for WebSocket real-time market data streaming.
    In production, connects to exchange WS endpoints.
    """

    def __init__(self, exchange: str) -> None:
        self.exchange = exchange
        self._running = False
        self._callbacks: Dict[str, List[Callable[..., None]]] = {}
        self._thread: Optional[threading.Thread] = None

    def on(self, channel: str, callback: Callable[..., None]) -> None:
        self._callbacks.setdefault(channel, []).append(callback)

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._simulate, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def _simulate(self) -> None:
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        while self._running:
            for sym in symbols:
                for channel, cbs in self._callbacks.items():
                    if "tickers" in channel:
                        data = {
                            "symbol": sym,
                            "lastPrice": str(45000 + hash(f"{sym}{time.time()}") % 10000),
                            "volume24h": str(hash(f"{sym}vol") % 100000),
                            "exchange": self.exchange,
                        }
                        for cb in cbs:
                            cb(data)
            time.sleep(1.0)


# ── Multi-Exchange Router ─────────────────────────────

class MultiExchangeRouter:
    """Routes orders to the best exchange by latency/fees."""

    def __init__(self) -> None:
        self._exchanges: Dict[str, ExchangeAdapter] = {}
        self._lock = threading.Lock()
        self._default: Optional[str] = None

    def register(self, name: str, adapter: ExchangeAdapter) -> None:
        with self._lock:
            self._exchanges[name] = adapter
            if self._default is None:
                self._default = name

    def set_default(self, name: str) -> None:
        with self._lock:
            if name in self._exchanges:
                self._default = name

    def place(self, order: Order, exchange: Optional[str] = None) -> Dict[str, Any]:
        target = exchange or self._default
        if target is None or target not in self._exchanges:
            return {"error": "no_exchange"}
        return self._exchanges[target].place_order(order)

    def best_price(self, symbol: str) -> Optional[Tuple[str, Ticker]]:
        best: Optional[Tuple[str, Ticker]] = None
        for name, adapter in self._exchanges.items():
            ticker = adapter.get_ticker(symbol)
            if ticker is None:
                continue
            if best is None or ticker.ask < best[1].ask:
                best = (name, ticker)
        return best

    def aggregate_balances(self) -> Dict[str, List[Balance]]:
        result: Dict[str, List[Balance]] = {}
        for name, adapter in self._exchanges.items():
            # Stub: would iterate all assets
            result[name] = [adapter.get_balance("USDT") or Balance("USDT", 0, 0, 0)]
        return result

    def disconnect_all(self) -> None:
        for adapter in self._exchanges.values():
            adapter.disconnect()


# ── Trading Kernel Bridge ─────────────────────────────

class TradingKernelBridge:
    """Bridge between trading layer and kernel event bus."""

    def __init__(self, router: MultiExchangeRouter) -> None:
        self.router = router

    def on_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a quant signal into an order."""
        side = OrderSide.BUY if signal.get("direction") == "long" else OrderSide.SELL
        order = Order(
            symbol=signal.get("symbol", "BTCUSDT"),
            side=side,
            order_type=OrderType.MARKET if signal.get("urgent") else OrderType.LIMIT,
            quantity=signal.get("size", 0.01),
            price=signal.get("price"),
        )
        return self.router.place(order)

    def get_portfolio_summary(self) -> Dict[str, Any]:
        bal = self.router.aggregate_balances()
        return {
            "exchanges": list(bal.keys()),
            "balances": {k: [b.to_dict() if hasattr(b, "to_dict") else str(b) for b in v] for k, v in bal.items()},
        }


# ── Self-Test ─────────────────────────────────────────

class ExchangeSelfTest:
    @staticmethod
    def run() -> Dict[str, Any]:
        results = {}

        # 1. Binance
        bn = BinanceAdapter(api_key="demo", api_secret="demo", testnet=True)
        results["binance_connect"] = "PASS" if bn.connect() else "FAIL"
        o = Order(symbol="BTCUSDT", side=OrderSide.BUY, order_type=OrderType.LIMIT, quantity=0.01, price=49000)
        r = bn.place_order(o)
        results["binance_order"] = "PASS" if r.get("orderId") else "FAIL"
        ticker = bn.get_ticker("BTCUSDT")
        results["binance_ticker"] = "PASS" if ticker and ticker.last_price > 0 else "FAIL"
        candles = bn.get_candles("BTCUSDT", "1h", limit=5)
        results["binance_candles"] = "PASS" if len(candles) == 5 else "FAIL"

        # 2. Bybit
        bb = BybitAdapter(api_key="demo", api_secret="demo", testnet=True)
        results["bybit_connect"] = "PASS" if bb.connect() else "FAIL"
        pos = bb.get_position("BTCUSDT")
        results["bybit_position"] = "PASS" if pos and pos.leverage > 1 else "FAIL"

        # 3. OKX
        ok = OKXAdapter(api_key="demo", api_secret="demo", passphrase="demo", testnet=True)
        results["okx_connect"] = "PASS" if ok.connect() else "FAIL"
        bal = ok.get_balance("USDT")
        results["okx_balance"] = "PASS" if bal and bal.total > 0 else "FAIL"

        # 4. Multi-router
        router = MultiExchangeRouter()
        router.register("binance", bn)
        router.register("bybit", bb)
        best = router.best_price("BTCUSDT")
        results["router_best_price"] = "PASS" if best is not None else "FAIL"

        # 5. Rate limiter
        rl = RateLimiter(max_weight=10, window_sec=1.0)
        ok_count = sum(rl.acquire(weight=1, block=False) for _ in range(12))
        results["rate_limit"] = "PASS" if ok_count <= 10 else "FAIL"

        results["overall"] = "PASS" if all(v == "PASS" for v in results.values()) else "FAIL"
        return results


if __name__ == "__main__":
    import base64
    print("=== Exchange Adapter Self-Test ===")
    for k, v in ExchangeSelfTest.run().items():
        print(f"  {k}: {v}")
    print("=====================================")
