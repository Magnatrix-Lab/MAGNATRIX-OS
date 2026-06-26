#!/usr/bin/env python3
"""
Real-Time Data Connectors for MAGNATRIX-OS
==========================================
WebSocket, market feed, news, and on-chain data connectors.
Pure Python stdlib only. No external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations
import json, socket, ssl, threading, time, urllib.request, urllib.parse, urllib.error
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple


@dataclass
class FeedMessage:
    """Unified feed message."""
    source: str
    type: str
    timestamp: float
    payload: Dict[str, Any] = field(default_factory=dict)
    raw: str = ""


class WebSocketConnector:
    """WebSocket client using socket + HTTP upgrade."""

    def __init__(self, url: str = "ws://localhost:8080") -> None:
        self.url = url
        self._socket: Optional[socket.socket] = None
        self._handlers: List[Callable[[Dict[str, Any]], None]] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def _parse_url(self) -> Tuple[str, str, int, str]:
        parsed = urllib.parse.urlparse(self.url)
        host = parsed.hostname or "localhost"
        port = parsed.port or (443 if parsed.scheme == "wss" else 80)
        path = parsed.path or "/"
        return parsed.scheme, host, port, path

    def connect(self) -> bool:
        scheme, host, port, path = self._parse_url()
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(10)
            if scheme == "wss":
                self._socket = ssl.wrap_socket(self._socket)
            self._socket.connect((host, port))

            key = "dGhlIHNhbXBsZSBub25jZQ=="
            req = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {host}\r\n"
                f"Upgrade: websocket\r\n"
                f"Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\n"
                f"Sec-WebSocket-Version: 13\r\n"
                f"\r\n"
            )
            self._socket.send(req.encode())
            resp = self._socket.recv(1024)
            if b"101" not in resp:
                self._socket.close()
                self._socket = None
                return False

            self._running = True
            self._thread = threading.Thread(target=self._receive_loop, daemon=True)
            self._thread.start()
            return True
        except Exception as e:
            self._socket = None
            return False

    def _receive_loop(self) -> None:
        while self._running and self._socket:
            try:
                data = self._socket.recv(4096)
                if not data:
                    break
                msg = self._decode_frame(data)
                if msg:
                    with self._lock:
                        for h in self._handlers:
                            try:
                                h(msg)
                            except Exception:
                                pass
            except socket.timeout:
                continue
            except Exception:
                break

    def _decode_frame(self, data: bytes) -> Optional[Dict[str, Any]]:
        try:
            text = data.decode("utf-8", errors="ignore")
            start = text.find("{")
            if start >= 0:
                return json.loads(text[start:])
            return None
        except Exception:
            return None

    def subscribe(self, channel: str, handler: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        if handler:
            with self._lock:
                self._handlers.append(handler)
        if self._socket:
            msg = json.dumps({"action": "subscribe", "channel": channel})
            self._socket.send(msg.encode())

    def on_message(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        with self._lock:
            self._handlers.append(handler)

    def disconnect(self) -> None:
        self._running = False
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None

    def is_connected(self) -> bool:
        return self._socket is not None and self._running


class MarketFeedConnector:
    """Connects to exchange market data feeds."""

    EXCHANGE_URLS = {
        "binance": "wss://stream.binance.com:9443/ws",
        "coinbase": "wss://ws-feed.exchange.coinbase.com",
    }

    def __init__(self, exchange: str = "binance") -> None:
        self.exchange = exchange
        self.ws = WebSocketConnector(self.EXCHANGE_URLS.get(exchange, ""))
        self._ticks: List[Dict[str, Any]] = []
        self._orderbooks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def connect(self) -> bool:
        success = self.ws.connect()
        if success:
            self.ws.on_message(self._on_message)
        return success

    def _on_message(self, msg: Dict[str, Any]) -> None:
        with self._lock:
            if "e" in msg and msg["e"] == "trade":
                self._ticks.append({
                    "symbol": msg.get("s", ""),
                    "price": float(msg.get("p", 0)),
                    "qty": float(msg.get("q", 0)),
                    "timestamp": msg.get("T", time.time()),
                })
            elif "bids" in msg or "asks" in msg:
                self._orderbooks[msg.get("product_id", "")] = msg

    def subscribe_ticker(self, symbol: str) -> None:
        stream = f"{symbol.lower()}@trade"
        self.ws.subscribe(stream)

    def subscribe_orderbook(self, symbol: str) -> None:
        stream = f"{symbol.lower()}@depth"
        self.ws.subscribe(stream)

    def get_tick(self, symbol: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            for t in reversed(self._ticks):
                if t["symbol"] == symbol:
                    return t
            return None

    def get_ticks(self, symbol: str, n: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            return [t for t in reversed(self._ticks) if t["symbol"] == symbol][:n]

    def get_orderbook(self, symbol: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._orderbooks.get(symbol)

    def disconnect(self) -> None:
        self.ws.disconnect()


class NewsFeedConnector:
    """News API connector."""

    SOURCES = {
        "hackernews": "https://hacker-news.firebaseio.com/v0/topstories.json",
        "reddit": "https://www.reddit.com/r/programming/.json",
    }

    def __init__(self) -> None:
        self._headlines: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def fetch_headlines(self, source: str = "hackernews") -> List[Dict[str, Any]]:
        url = self.SOURCES.get(source, "")
        if not url:
            return []
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MAGNATRIX-OS/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                if source == "hackernews" and isinstance(data, list):
                    ids = data[:10]
                    headlines = []
                    for item_id in ids:
                        try:
                            item_url = f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
                            with urllib.request.urlopen(item_url, timeout=5) as r:
                                item = json.loads(r.read().decode())
                                headlines.append({"title": item.get("title", ""), "url": item.get("url", "")})
                        except Exception:
                            pass
                    with self._lock:
                        self._headlines = headlines
                    return headlines
                elif source == "reddit" and "data" in data:
                    posts = data["data"]["children"][:10]
                    headlines = [{"title": p["data"].get("title", ""), "url": p["data"].get("url", "")} for p in posts]
                    with self._lock:
                        self._headlines = headlines
                    return headlines
        except Exception as e:
            return [{"error": str(e)}]
        return []

    def search(self, query: str) -> List[Dict[str, Any]]:
        return [{"query": query, "results": "Search requires external API key"}]

    def subscribe_feed(self, source: str, interval: int = 60) -> None:
        def poll():
            while True:
                self.fetch_headlines(source)
                time.sleep(interval)
        threading.Thread(target=poll, daemon=True).start()

    def get_headlines(self) -> List[Dict[str, Any]]:
        with self._lock:
            return self._headlines.copy()


class OnChainDataConnector:
    """Blockchain data reader."""

    RPC_NODES = {
        "ethereum": "https://cloudflare-eth.com",
        "bitcoin": "https://blockchain.info",
    }

    def __init__(self, chain: str = "ethereum") -> None:
        self.chain = chain
        self._blocks: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def get_block(self, height: int) -> Optional[Dict[str, Any]]:
        if self.chain == "ethereum":
            return self._rpc_call("eth_getBlockByNumber", [hex(height), False])
        return None

    def get_transaction(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        if self.chain == "ethereum":
            return self._rpc_call("eth_getTransactionByHash", [tx_hash])
        return None

    def get_balance(self, address: str) -> Optional[str]:
        if self.chain == "ethereum":
            return self._rpc_call("eth_getBalance", [address, "latest"])
        return None

    def _rpc_call(self, method: str, params: List[Any]) -> Optional[Dict[str, Any]]:
        url = self.RPC_NODES.get(self.chain, "")
        if not url:
            return None
        try:
            payload = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1})
            req = urllib.request.Request(url, data=payload.encode(), headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            return None

    def subscribe_blocks(self, interval: int = 15) -> None:
        def poll():
            while True:
                if self.chain == "ethereum":
                    result = self._rpc_call("eth_blockNumber", [])
                    if result and "result" in result:
                        with self._lock:
                            self._blocks["latest"] = result["result"]
                time.sleep(interval)
        threading.Thread(target=poll, daemon=True).start()

    def get_latest_block(self) -> Optional[str]:
        with self._lock:
            return self._blocks.get("latest")


class DataConnectorManager:
    """Top-level orchestrator for all data connectors."""

    def __init__(self) -> None:
        self.market = MarketFeedConnector()
        self.news = NewsFeedConnector()
        self.onchain = OnChainDataConnector()
        self._running = False

    def start_all(self) -> None:
        self._running = True
        self.market.connect()
        self.news.subscribe_feed("hackernews", interval=300)
        self.onchain.subscribe_blocks(interval=15)

    def stop_all(self) -> None:
        self._running = False
        self.market.disconnect()

    def get_status(self) -> Dict[str, Any]:
        return {
            "market_connected": self.market.ws.is_connected(),
            "exchange": self.market.exchange,
            "news_headlines": len(self.news.get_headlines()),
            "onchain_latest": self.onchain.get_latest_block(),
            "running": self._running,
        }

    def get_combined_feed(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        feed: Dict[str, Any] = {
            "timestamp": time.time(),
            "market": {},
            "news": [],
            "onchain": {},
        }
        if symbol:
            tick = self.market.get_tick(symbol)
            if tick:
                feed["market"] = tick
        feed["news"] = self.news.get_headlines()[:5]
        feed["onchain"] = {"latest_block": self.onchain.get_latest_block()}
        return feed

    def to_dict(self) -> Dict[str, Any]:
        return self.get_status()
