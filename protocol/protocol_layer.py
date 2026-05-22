"""
MAGNATRIX — Protocol Layer
═══════════════════════════
Layer 1: Protocol — komunikasi antar layer & eksternal.

Features:
- gRPC server/client untuk internal communication
- WebSocket gateway untuk real-time streaming
- REST API adapter untuk external integration
- Message serialization (protobuf, JSON, msgpack)
- Rate limiting & request throttling
- Connection pooling

Author: MAGNATRIX-OS
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


class ProtocolFormat(Enum):
    JSON = auto()
    PROTOBUF = auto()
    MSGPACK = auto()


@dataclass
class ProtocolMessage:
    msg_id: str = field(default_factory=lambda: f"msg-{uuid.uuid4().hex[:12]}")
    source: str = ""
    target: str = ""
    action: str = ""  # e.g., "invoke", "query", "broadcast", "response"
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    format: ProtocolFormat = ProtocolFormat.JSON
    headers: Dict[str, str] = field(default_factory=dict)

    def serialize(self) -> bytes:
        if self.format == ProtocolFormat.JSON:
            return json.dumps(asdict(self), default=str).encode("utf-8")
        elif self.format == ProtocolFormat.MSGPACK:
            try:
                import msgpack
                return msgpack.packb(asdict(self), use_bin_type=True)
            except ImportError:
                return json.dumps(asdict(self), default=str).encode("utf-8")
        return json.dumps(asdict(self), default=str).encode("utf-8")

    @classmethod
    def deserialize(cls, data: bytes, fmt: ProtocolFormat = ProtocolFormat.JSON) -> "ProtocolMessage":
        if fmt == ProtocolFormat.MSGPACK:
            try:
                import msgpack
                obj = msgpack.unpackb(data, raw=False)
                return cls(**obj)
            except ImportError:
                obj = json.loads(data.decode("utf-8"))
        else:
            obj = json.loads(data.decode("utf-8"))
        return cls(**{k: v for k, v in obj.items() if k in cls.__dataclass_fields__})


class RateLimiter:
    """Token bucket rate limiter untuk request throttling."""

    def __init__(self, rate: float = 100.0, burst: float = 150.0):
        self.rate = rate  # tokens per second
        self.burst = burst  # max tokens
        self._tokens = burst
        self._last_update = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> bool:
        async with self._lock:
            now = time.time()
            elapsed = now - self._last_update
            self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
            self._last_update = now
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    async def wait(self, tokens: float = 1.0) -> None:
        while not await self.acquire(tokens):
            deficit = tokens - self._tokens
            wait_time = deficit / self.rate
            await asyncio.sleep(wait_time)


class ProtocolServer:
    """gRPC + WebSocket + REST hybrid server."""

    def __init__(self, grpc_port: int = 50051, ws_port: int = 50052, rest_port: int = 50053):
        self.grpc_port = grpc_port
        self.ws_port = ws_port
        self.rest_port = rest_port
        self._handlers: Dict[str, Callable] = {}
        self._limiter = RateLimiter()
        self._connections: Set[Any] = set()
        self._running = False
        self._tasks: List[asyncio.Task] = []

    def register_handler(self, action: str, handler: Callable) -> None:
        self._handlers[action] = handler

    async def start(self) -> None:
        self._running = True
        # gRPC server
        self._tasks.append(asyncio.create_task(self._grpc_server()))
        # WebSocket server
        self._tasks.append(asyncio.create_task(self._ws_server()))
        # REST server
        self._tasks.append(asyncio.create_task(self._rest_server()))

    async def stop(self) -> None:
        self._running = False
        for t in self._tasks:
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass
        self._tasks.clear()

    async def _grpc_server(self) -> None:
        try:
            import grpc
            from concurrent import futures
            server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
            # In production: add servicers here
            server.add_insecure_port(f"[::]:{self.grpc_port}")
            await server.start()
            print(f"[Protocol] gRPC server on :{self.grpc_port}")
            while self._running:
                await asyncio.sleep(1)
            await server.stop(grace_period=5)
        except ImportError:
            print("[Protocol] grpcio not installed, gRPC server skipped")

    async def _ws_server(self) -> None:
        try:
            import websockets
            async def handler(websocket, path):
                self._connections.add(websocket)
                try:
                    async for message in websocket:
                        if not await self._limiter.acquire():
                            await websocket.send(json.dumps({"error": "rate_limited"}))
                            continue
                        try:
                            msg = ProtocolMessage.deserialize(message.encode())
                            resp = await self._dispatch(msg)
                            await websocket.send(resp.serialize())
                        except Exception as e:
                            await websocket.send(json.dumps({"error": str(e)}))
                finally:
                    self._connections.discard(websocket)

            server = await websockets.serve(handler, "0.0.0.0", self.ws_port)
            print(f"[Protocol] WebSocket server on :{self.ws_port}")
            while self._running:
                await asyncio.sleep(1)
            server.close()
            await server.wait_closed()
        except ImportError:
            print("[Protocol] websockets not installed, WebSocket server skipped")

    async def _rest_server(self) -> None:
        try:
            from aiohttp import web
            app = web.Application()
            app.router.add_post("/api/v1/{action}", self._rest_handler)
            app.router.add_get("/health", self._health_handler)
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, "0.0.0.0", self.rest_port)
            await site.start()
            print(f"[Protocol] REST server on :{self.rest_port}")
            while self._running:
                await asyncio.sleep(1)
            await runner.cleanup()
        except ImportError:
            print("[Protocol] aiohttp not installed, REST server skipped")

    async def _rest_handler(self, request) -> Any:
        try:
            if not await self._limiter.acquire():
                return web.json_response({"error": "rate_limited"}, status=429)
            action = request.match_info["action"]
            body = await request.json()
            msg = ProtocolMessage(source="rest", action=action, payload=body)
            resp = await self._dispatch(msg)
            return web.json_response(resp.payload)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def _health_handler(self, request) -> Any:
        from aiohttp import web
        return web.json_response({"status": "ok", "protocol": "MAGNATRIX"})

    async def _dispatch(self, msg: ProtocolMessage) -> ProtocolMessage:
        handler = self._handlers.get(msg.action)
        if not handler:
            return ProtocolMessage(
                source="protocol", target=msg.source, action="response",
                payload={"error": f"Unknown action: {msg.action}"},
            )
        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(msg.payload)
            else:
                result = handler(msg.payload)
            return ProtocolMessage(
                source="protocol", target=msg.source, action="response",
                payload={"result": result},
            )
        except Exception as e:
            return ProtocolMessage(
                source="protocol", target=msg.source, action="response",
                payload={"error": str(e)},
            )

    def healthcheck(self) -> bool:
        return self._running


class ProtocolClient:
    """Client untuk connect ke MAGNATRIX Protocol server."""

    def __init__(self, endpoint: str = "ws://localhost:50052"):
        self.endpoint = endpoint
        self._ws = None

    async def connect(self) -> bool:
        try:
            import websockets
            self._ws = await websockets.connect(self.endpoint)
            return True
        except ImportError:
            return False

    async def send(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        msg = ProtocolMessage(source="client", action=action, payload=payload)
        if self._ws:
            await self._ws.send(msg.serialize())
            resp = await self._ws.recv()
            parsed = ProtocolMessage.deserialize(resp)
            return parsed.payload
        # Fallback: HTTP
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(f"http://localhost:50053/api/v1/{action}", json=payload) as resp:
                    return await resp.json()
        except ImportError:
            return {"error": "No transport available"}

    async def close(self) -> None:
        if self._ws:
            await self._ws.close()
            self._ws = None
