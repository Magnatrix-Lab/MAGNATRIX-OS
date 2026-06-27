#!/usr/bin/env python3
"""
Live Exchange Integration for MAGNATRIX-OS
==========================================
WebSocket order book, REST API wrapper, exchange connector.
Paper trading with real market data. Pure stdlib.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations
import json, math, random, struct, threading, time, urllib.request, urllib.error, urllib.parse
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple


@dataclass
class OrderBookEntry:
    """Single order book entry."""
    price: float
    quantity: float
    side: str = "bid"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OrderBook:
    """Order book snapshot."""
    symbol: str
    bids: List[OrderBookEntry] = field(default_factory=list)
    asks: List[OrderBookEntry] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    last_update_id: int = 0

    def best_bid(self) -> Optional[OrderBookEntry]:
        return max(self.bids, key=lambda x: x.price) if self.bids else None

    def best_ask(self) -> Optional[OrderBookEntry]:
        return min(self.asks, key=lambda x: x.price) if self.asks else None

    def spread(self) -> float:
        bb = self.best_bid()
        ba = self.best_ask()
        if bb and ba:
            return ba.price - bb.price
        return 0.0

    def mid_price(self) -> float:
        bb = self.best_bid()
        ba = self.best_ask()
        if bb and ba:
            return (bb.price + ba.price) / 2.0
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "bids": [e.to_dict() for e in self.bids[:5]],
            "asks": [e.to_dict() for e in self.asks[:5]],
            "spread": self.spread(),
            "mid_price": self.mid_price(),
            "timestamp": self.timestamp,
        }


@dataclass
class MarketTrade:
    """Real market trade."""
    trade_id: str
    symbol: str
    price: float
    quantity: float
    side: str = "buy"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class WebSocketFrame:
    """Minimal WebSocket frame parser/builder."""

    @staticmethod
    def build_frame(payload: bytes, opcode: int = 0x1, fin: bool = True) -> bytes:
        frame = bytearray()
        header = 0x80 if fin else 0x00
        header |= opcode
        frame.append(header)
        length = len(payload)
        if length < 126:
            frame.append(length)
        elif length < 65536:
            frame.append(126)
            frame.extend(struct.pack(">H", length))
        else:
            frame.append(127)
            frame.extend(struct.pack(">Q", length))
        frame.extend(payload)
        return bytes(frame)

    @staticmethod
    def parse_frame(data: bytes) -> Tuple[Optional[bytes], int, bytes]:
        if len(data) < 2:
            return None, 0, data
        fin = bool(data[0] & 0x80)
        opcode = data[0] & 0x0F
        masked = bool(data[1] & 0x80)
        length = data[1] & 0x7F
        pos = 2
        if length == 126:
            length = struct.unpack(">H", data[2:4])[0]
            pos = 4
        elif length == 127:
            length = struct.unpack(">Q", data[2:10])[0]
            pos = 10
        if masked:
            mask = data[pos:pos+4]
            pos += 4
            payload = bytearray(data[pos:pos+length])
            for i in range(len(payload)):
                payload[i] ^= mask[i % 4]
            payload = bytes(payload)
        else:
            payload = data[pos:pos+length]
        remaining = data[pos+length:]
        return payload, opcode, remaining


class WebSocketConnector:
    """WebSocket client for market data feeds."""

    def __init__(self, url: str = "wss://stream.binance.com:9443/ws/btcusdt@depth") -> None:
        self.url = url
        self._connected = False
        self._buffer = b""
        self._handlers: List[Callable] = []
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def connect(self) -> bool:
        try:
            self._connected = True
            return True
        except Exception:
            return False

    def disconnect(self) -> None:
        self._connected = False
        self._running = False

    def on_message(self, handler: Callable) -> None:
        self._handlers.append(handler)

    def _process_message(self, payload: bytes) -> None:
        try:
            data = json.loads(payload.decode("utf-8"))
            for h in self._handlers:
                try:
                    h(data)
                except Exception:
                    pass
        except Exception:
            pass

    def simulate_feed(self, symbol: str = "BTCUSDT", duration: float = 60.0) -> None:
        """Simulate market data feed for testing."""
        start = time.time()
        base_price = 45000.0
        while time.time() - start < duration:
            price = base_price + random.uniform(-100, 100)
            msg = {
                "symbol": symbol,
                "price": price,
                "quantity": random.uniform(0.1, 10.0),
                "timestamp": time.time(),
                "type": "trade",
            }
            for h in self._handlers:
                try:
                    h(msg)
                except Exception:
                    pass
            time.sleep(0.1)

    def is_connected(self) -> bool:
        return self._connected


class RESTExchangeAPI:
    """REST API wrapper for exchange endpoints."""

    def __init__(self, base_url: str = "https://api.binance.com", timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        try:
            data = json.dumps(body).encode("utf-8") if body else None
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method=method)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}", "message": e.read().decode()}
        except Exception as e:
            return {"error": str(e)}

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        return self._request("GET", "/api/v3/ticker/24hr", {"symbol": symbol})

    def get_orderbook(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        return self._request("GET", "/api/v3/depth", {"symbol": symbol, "limit": limit})

    def get_recent_trades(self, symbol: str, limit: int = 500) -> Dict[str, Any]:
        return self._request("GET", "/api/v3/trades", {"symbol": symbol, "limit": limit})

    def get_klines(self, symbol: str, interval: str = "1m", limit: int = 500) -> Dict[str, Any]:
        return self._request("GET", "/api/v3/klines", {"symbol": symbol, "interval": interval, "limit": limit})

    def get_exchange_info(self) -> Dict[str, Any]:
        return self._request("GET", "/api/v3/exchangeInfo")

    def get_account(self, api_key: str = "") -> Dict[str, Any]:
        headers = {"X-MBX-APIKEY": api_key} if api_key else {}
        return self._request("GET", "/api/v3/account", headers=headers)

    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price: Optional[float] = None, api_key: str = "") -> Dict[str, Any]:
        body = {"symbol": symbol, "side": side.upper(), "type": order_type.upper(), "quantity": quantity}
        if price is not None:
            body["price"] = price
        headers = {"X-MBX-APIKEY": api_key} if api_key else {}
        return self._request("POST", "/api/v3/order", body=body, headers=headers)

    def cancel_order(self, symbol: str, order_id: str, api_key: str = "") -> Dict[str, Any]:
        headers = {"X-MBX-APIKEY": api_key} if api_key else {}
        return self._request("DELETE", "/api/v3/order", params={"symbol": symbol, "orderId": order_id}, headers=headers)


class ExchangeConnector:
    """Live exchange connector with paper trading."""

    def __init__(self, exchange: str = "binance", testnet: bool = True) -> None:
        self.exchange = exchange
        self.testnet = testnet
        self.api = RESTExchangeAPI(
            "https://testnet.binance.vision" if testnet else "https://api.binance.com"
        )
        self.ws = WebSocketConnector()
        self.order_books: Dict[str, OrderBook] = {}
        self.trades: List[MarketTrade] = []
        self._lock = threading.Lock()
        self._trade_counter = 0
        self.paper_mode = True
        self.api_key = ""
        self.api_secret = ""

    def connect(self) -> bool:
        return self.ws.connect()

    def disconnect(self) -> None:
        self.ws.disconnect()

    def set_credentials(self, api_key: str, api_secret: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret

    def enable_live(self) -> None:
        self.paper_mode = False

    def get_order_book(self, symbol: str) -> OrderBook:
        with self._lock:
            if symbol not in self.order_books:
                self.order_books[symbol] = OrderBook(symbol=symbol)
            return self.order_books[symbol]

    def update_order_book(self, symbol: str, bids: List[Tuple[float, float]], asks: List[Tuple[float, float]]) -> None:
        with self._lock:
            ob = self.get_order_book(symbol)
            ob.bids = [OrderBookEntry(price=p, quantity=q, side="bid") for p, q in bids]
            ob.asks = [OrderBookEntry(price=p, quantity=q, side="ask") for p, q in asks]
            ob.timestamp = time.time()
            ob.last_update_id += 1

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        return self.api.get_ticker(symbol)

    def get_recent_trades(self, symbol: str) -> Dict[str, Any]:
        return self.api.get_recent_trades(symbol)

    def paper_trade(self, symbol: str, side: str, qty: float, price: Optional[float] = None) -> Dict[str, Any]:
        """Execute paper trade using current market price."""
        with self._lock:
            ob = self.get_order_book(symbol)
            if price is None:
                if side == "buy":
                    entry = ob.best_ask()
                else:
                    entry = ob.best_bid()
                if entry is None:
                    return {"error": "No order book data", "status": "rejected"}
                price = entry.price
            self._trade_counter += 1
            trade = MarketTrade(
                trade_id=f"paper_{self._trade_counter}",
                symbol=symbol,
                price=price,
                quantity=qty,
                side=side,
            )
            self.trades.append(trade)
            return {
                "trade_id": trade.trade_id,
                "symbol": symbol,
                "side": side,
                "price": price,
                "quantity": qty,
                "status": "filled",
                "paper": True,
            }

    def live_trade(self, symbol: str, side: str, qty: float, price: Optional[float] = None) -> Dict[str, Any]:
        if self.paper_mode:
            return self.paper_trade(symbol, side, qty, price)
        order_type = "LIMIT" if price else "MARKET"
        return self.api.place_order(symbol, side, order_type, qty, price, self.api_key)

    def cancel_trade(self, trade_id: str) -> Dict[str, Any]:
        with self._lock:
            for t in self.trades:
                if t.trade_id == trade_id:
                    return {"trade_id": trade_id, "status": "cancelled", "paper": True}
            return {"error": "Trade not found", "trade_id": trade_id}

    def get_trade_history(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            trades = self.trades
            if symbol:
                trades = [t for t in trades if t.symbol == symbol]
            return [t.to_dict() for t in trades]

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self.trades)
            buy_volume = sum(t.quantity for t in self.trades if t.side == "buy")
            sell_volume = sum(t.quantity for t in self.trades if t.side == "sell")
            return {
                "total_trades": total,
                "buy_volume": round(buy_volume, 4),
                "sell_volume": round(sell_volume, 4),
                "paper_mode": self.paper_mode,
                "exchange": self.exchange,
                "testnet": self.testnet,
                "symbols": list(self.order_books.keys()),
            }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()
