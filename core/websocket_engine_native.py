#!/usr/bin/env python3
"""
WebSocket Real-Time Engine for MAGNATRIX-OS
Native WebSocket server — no external dependencies.
Provides real-time chat, log streaming, metrics push, notifications.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import select
import socket
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


@dataclass
class WSFrame:
    """Parsed WebSocket frame."""
    fin: bool
    opcode: int
    payload: bytes
    masked: bool = False


class WebSocketProtocol:
    """RFC 6455 WebSocket protocol implementation."""

    OPCODE_CONT = 0x0
    OPCODE_TEXT = 0x1
    OPCODE_BINARY = 0x2
    OPCODE_CLOSE = 0x8
    OPCODE_PING = 0x9
    OPCODE_PONG = 0xA

    @staticmethod
    def handshake(request_headers: Dict[str, str]) -> Optional[str]:
        key = request_headers.get("Sec-WebSocket-Key", "")
        if not key:
            return None
        magic = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        accept = base64.b64encode(hashlib.sha1((key + magic).encode()).digest()).decode()
        return (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n"
            "\r\n"
        )

    @staticmethod
    def parse_frame(data: bytes) -> Tuple[Optional[WSFrame], int]:
        if len(data) < 2:
            return None, 0
        b0, b1 = data[0], data[1]
        fin = bool(b0 & 0x80)
        opcode = b0 & 0x0F
        masked = bool(b1 & 0x80)
        payload_len = b1 & 0x7F
        offset = 2
        if payload_len == 126:
            if len(data) < 4:
                return None, 0
            payload_len = struct.unpack(">H", data[2:4])[0]
            offset = 4
        elif payload_len == 127:
            if len(data) < 10:
                return None, 0
            payload_len = struct.unpack(">Q", data[2:10])[0]
            offset = 10
        mask_key = data[offset:offset + 4] if masked else b""
        offset += 4 if masked else 0
        if len(data) < offset + payload_len:
            return None, 0
        payload = data[offset:offset + payload_len]
        if masked and mask_key:
            payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
        return WSFrame(fin, opcode, payload, masked), offset + payload_len

    @staticmethod
    def build_frame(opcode: int, payload: bytes, fin: bool = True) -> bytes:
        b0 = (0x80 if fin else 0x00) | (opcode & 0x0F)
        length = len(payload)
        if length < 126:
            header = bytes([b0, length])
        elif length < 65536:
            header = bytes([b0, 126]) + struct.pack(">H", length)
        else:
            header = bytes([b0, 127]) + struct.pack(">Q", length)
        return header + payload


class WSConnection:
    """Manages a single WebSocket connection."""

    def __init__(self, sock: socket.socket, addr: Tuple[str, int]) -> None:
        self.sock = sock
        self.addr = addr
        self.id = f"{addr[0]}:{addr[1]}_{id(self)}"
        self._buffer = b""
        self._open = True
        self._lock = threading.Lock()
        self._on_message: Optional[Callable[[str], None]] = None
        self._on_binary: Optional[Callable[[bytes], None]] = None
        self._on_close: Optional[Callable[[], None]] = None
        self._subscribed_channels: Set[str] = set()

    def send_text(self, text: str) -> bool:
        try:
            with self._lock:
                if self._open:
                    frame = WebSocketProtocol.build_frame(WebSocketProtocol.OPCODE_TEXT, text.encode("utf-8"))
                    self.sock.sendall(frame)
                    return True
        except Exception:
            pass
        return False

    def send_json(self, data: Any) -> bool:
        return self.send_text(json.dumps(data, ensure_ascii=False))

    def send_binary(self, data: bytes) -> bool:
        try:
            with self._lock:
                if self._open:
                    frame = WebSocketProtocol.build_frame(WebSocketProtocol.OPCODE_BINARY, data)
                    self.sock.sendall(frame)
                    return True
        except Exception:
            pass
        return False

    def close(self, code: int = 1000, reason: str = "") -> None:
        try:
            with self._lock:
                self._open = False
                payload = struct.pack(">H", code) + reason.encode("utf-8")
                frame = WebSocketProtocol.build_frame(WebSocketProtocol.OPCODE_CLOSE, payload)
                self.sock.sendall(frame)
                self.sock.close()
        except Exception:
            pass

    def _read_loop(self) -> None:
        while self._open:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break
                self._buffer += data
                while self._buffer:
                    frame, consumed = WebSocketProtocol.parse_frame(self._buffer)
                    if frame is None:
                        break
                    self._buffer = self._buffer[consumed:]
                    if frame.opcode == WebSocketProtocol.OPCODE_TEXT:
                        if self._on_message:
                            try:
                                self._on_message(frame.payload.decode("utf-8", errors="ignore"))
                            except Exception:
                                pass
                    elif frame.opcode == WebSocketProtocol.OPCODE_BINARY:
                        if self._on_binary:
                            self._on_binary(frame.payload)
                    elif frame.opcode == WebSocketProtocol.OPCODE_CLOSE:
                        self._open = False
                        break
                    elif frame.opcode == WebSocketProtocol.OPCODE_PING:
                        pong = WebSocketProtocol.build_frame(WebSocketProtocol.OPCODE_PONG, frame.payload)
                        self.sock.sendall(pong)
            except Exception:
                break
        self._open = False
        if self._on_close:
            try:
                self._on_close()
            except Exception:
                pass

    def on_message(self, callback: Callable[[str], None]) -> None:
        self._on_message = callback

    def on_binary(self, callback: Callable[[bytes], None]) -> None:
        self._on_binary = callback

    def on_close(self, callback: Callable[[], None]) -> None:
        self._on_close = callback

    def start(self) -> threading.Thread:
        t = threading.Thread(target=self._read_loop, daemon=True, name=f"WS-{self.id}")
        t.start()
        return t


class WebSocketServer:
    """WebSocket server that bridges to MAGNATRIX-OS modules."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765) -> None:
        self.host = host
        self.port = port
        self._sock: Optional[socket.socket] = None
        self._clients: Dict[str, WSConnection] = {}
        self._lock = threading.Lock()
        self._running = False
        self._server_thread: Optional[threading.Thread] = None
        self._channels: Dict[str, List[str]] = {}
        self._on_connect: Optional[Callable[[WSConnection], None]] = None
        self._on_disconnect: Optional[Callable[[WSConnection], None]] = None
        self._handlers: Dict[str, Callable[[WSConnection, Any], None]] = {}

    def _parse_http_headers(self, data: bytes) -> Dict[str, str]:
        headers = {}
        try:
            text = data.decode("utf-8", errors="ignore")
            lines = text.split("\r\n")
            for line in lines[1:]:
                if ":" in line:
                    k, v = line.split(":", 1)
                    headers[k.strip()] = v.strip()
        except Exception:
            pass
        return headers

    def _handle_client(self, client_sock: socket.socket, addr: Tuple[str, int]) -> None:
        try:
            # Read HTTP upgrade request
            client_sock.settimeout(5)
            data = client_sock.recv(4096)
            headers = self._parse_http_headers(data)
            response = WebSocketProtocol.handshake(headers)
            if not response:
                client_sock.close()
                return
            client_sock.sendall(response.encode())
            client_sock.settimeout(None)

            conn = WSConnection(client_sock, addr)
            with self._lock:
                self._clients[conn.id] = conn

            conn.on_message(lambda msg: self._route_message(conn, msg))
            conn.on_close(lambda: self._remove_client(conn))

            if self._on_connect:
                self._on_connect(conn)

            conn.start()
        except Exception:
            client_sock.close()

    def _remove_client(self, conn: WSConnection) -> None:
        with self._lock:
            if conn.id in self._clients:
                del self._clients[conn.id]
            for ch, clients in self._channels.items():
                if conn.id in clients:
                    clients.remove(conn.id)
        if self._on_disconnect:
            self._on_disconnect(conn)

    def _route_message(self, conn: WSConnection, message: str) -> None:
        try:
            data = json.loads(message)
            msg_type = data.get("type", "")
            if msg_type in self._handlers:
                self._handlers[msg_type](conn, data)
            else:
                # Default: echo
                conn.send_json({"type": "echo", "data": data})
        except Exception:
            conn.send_text(message)

    def register_handler(self, msg_type: str, handler: Callable[[WSConnection, Any], None]) -> None:
        self._handlers[msg_type] = handler

    def broadcast(self, message: Any, channel: Optional[str] = None) -> int:
        sent = 0
        with self._lock:
            clients = list(self._clients.values())
        text = json.dumps(message, ensure_ascii=False) if not isinstance(message, str) else message
        for conn in clients:
            if channel and channel not in conn._subscribed_channels:
                continue
            if conn.send_text(text):
                sent += 1
        return sent

    def broadcast_binary(self, data: bytes) -> int:
        sent = 0
        with self._lock:
            clients = list(self._clients.values())
        for conn in clients:
            if conn.send_binary(data):
                sent += 1
        return sent

    def start(self, blocking: bool = False) -> None:
        self._running = True
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen(100)
        print(f"[WebSocket] Server started at ws://{self.host}:{self.port}")

        def _accept_loop():
            while self._running:
                try:
                    self._sock.settimeout(1.0)
                    client, addr = self._sock.accept()
                    threading.Thread(target=self._handle_client, args=(client, addr), daemon=True).start()
                except socket.timeout:
                    continue
                except Exception:
                    break

        if blocking:
            _accept_loop()
        else:
            self._server_thread = threading.Thread(target=_accept_loop, daemon=True, name="WSServer")
            self._server_thread.start()

    def stop(self) -> None:
        self._running = False
        with self._lock:
            for conn in list(self._clients.values()):
                conn.close()
            self._clients.clear()
        if self._sock:
            self._sock.close()

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "host": self.host, "port": self.port,
                "clients": len(self._clients),
                "handlers": list(self._handlers.keys()),
            }


class RealtimeEngine:
    """High-level real-time engine bridging WebSocket to MAGNATRIX-OS."""

    def __init__(self, ws_host: str = "0.0.0.0", ws_port: int = 8765) -> None:
        self.ws = WebSocketServer(ws_host, ws_port)
        self._chat_history: List[Dict[str, Any]] = []
        self._log_buffer: List[Dict[str, Any]] = []
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        # Chat handler
        self.ws.register_handler("chat", self._handle_chat)
        # Subscribe handler
        self.ws.register_handler("subscribe", self._handle_subscribe)
        # Ping handler
        self.ws.register_handler("ping", self._handle_ping)
        # Module control handler
        self.ws.register_handler("module_control", self._handle_module_control)

    def _handle_chat(self, conn: WSConnection, data: Any) -> None:
        msg = data.get("message", "")
        entry = {"id": len(self._chat_history), "sender": "user", "text": msg, "time": time.time()}
        self._chat_history.append(entry)
        # Broadcast to all
        self.ws.broadcast({"type": "chat", "entry": entry})
        # Simulate AI response (real integration would call LLM adapter)
        reply = {"id": len(self._chat_history), "sender": "ai", "text": f"Echo: {msg}", "time": time.time()}
        self._chat_history.append(reply)
        self.ws.broadcast({"type": "chat", "entry": reply})

    def _handle_subscribe(self, conn: WSConnection, data: Any) -> None:
        channels = data.get("channels", [])
        for ch in channels:
            conn._subscribed_channels.add(ch)
        conn.send_json({"type": "subscribed", "channels": list(conn._subscribed_channels)})

    def _handle_ping(self, conn: WSConnection, data: Any) -> None:
        conn.send_json({"type": "pong", "time": time.time()})

    def _handle_module_control(self, conn: WSConnection, data: Any) -> None:
        action = data.get("action", "")
        module = data.get("module", "")
        conn.send_json({"type": "module_control", "action": action, "module": module, "status": "ok"})

    def push_log(self, level: str, message: str) -> None:
        entry = {"time": time.time(), "level": level, "message": message}
        self._log_buffer.append(entry)
        if len(self._log_buffer) > 1000:
            self._log_buffer = self._log_buffer[-500:]
        self.ws.broadcast({"type": "log", "entry": entry}, channel="logs")

    def push_metric(self, metric: str, value: float, unit: str = "") -> None:
        self.ws.broadcast({"type": "metric", "metric": metric, "value": value, "unit": unit, "time": time.time()}, channel="metrics")

    def push_notification(self, title: str, body: str, priority: str = "normal") -> None:
        self.ws.broadcast({"type": "notification", "title": title, "body": body, "priority": priority, "time": time.time()}, channel="notifications")

    def start(self, blocking: bool = False) -> None:
        self.ws.start(blocking)

    def stop(self) -> None:
        self.ws.stop()

    def stats(self) -> Dict[str, Any]:
        return {
            "websocket": self.ws.stats(),
            "chat_messages": len(self._chat_history),
            "log_entries": len(self._log_buffer),
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== WebSocket Real-Time Engine Demo ===\n")
    engine = RealtimeEngine(ws_port=8766)
    engine.start()
    print(f"WebSocket server started. Connect to ws://127.0.0.1:8766")
    print(f"Stats: {engine.stats()}")
    time.sleep(1)
    # Simulate some events
    engine.push_log("INFO", "System started")
    engine.push_metric("cpu", 15.5, "%")
    engine.push_notification("MAGNATRIX-OS", "System is online", "normal")
    print(f"\nAfter events: {engine.stats()}")
    engine.stop()
    print("\nServer stopped.")


if __name__ == "__main__":
    _demo()
