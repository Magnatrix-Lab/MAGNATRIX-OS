#!/usr/bin/env python3
"""
================================================================================
MAGNATRIX-OS — MCP Server (Layer 1.5 Extension)
Inspired by: itseffi/agentic-os System/mcp/
Model Context Protocol server providing structured tools for AI agents.
JSON-RPC over stdio/HTTP with tool registration, schema validation,
and streaming responses.
================================================================================
Zero-dependency MCP server implementation.
================================================================================
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple


# =============================================================================
# Constants
# =============================================================================
MCP_PROTOCOL_VERSION = "2025-03-26"
DEFAULT_MCP_PORT = 17781


# =============================================================================
# Data Types
# =============================================================================
@dataclass
class ToolSchema:
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)
    returns: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)


@dataclass
class ToolResult:
    call_id: str
    success: bool
    data: Any = None
    error: str = ""
    duration_ms: float = 0.0


# =============================================================================
# Tool Registry
# =============================================================================
class ToolRegistry:
    """Register and discover tools with JSON schema validation."""

    def __init__(self) -> None:
        self._tools: Dict[str, Tuple[ToolSchema, Callable[[Dict[str, Any]], Any]]] = {}
        self._lock = threading.Lock()

    def register(self, schema: ToolSchema, fn: Callable[[Dict[str, Any]], Any]) -> None:
        with self._lock:
            self._tools[schema.name] = (schema, fn)

    def unregister(self, name: str) -> bool:
        with self._lock:
            return self._tools.pop(name, None) is not None

    def get_schema(self, name: str) -> Optional[ToolSchema]:
        with self._lock:
            entry = self._tools.get(name)
            return entry[0] if entry else None

    def list_tools(self) -> List[ToolSchema]:
        with self._lock:
            return [s for s, _ in self._tools.values()]

    def call(self, name: str, arguments: Dict[str, Any]) -> ToolResult:
        t0 = time.perf_counter()
        with self._lock:
            entry = self._tools.get(name)
        if not entry:
            return ToolResult(
                call_id=hashlib.sha256(f"{name}:{time.time()}".encode()).hexdigest()[:12],
                success=False,
                error=f"Tool '{name}' not found",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        schema, fn = entry
        # Validate required args
        missing = [r for r in schema.required if r not in arguments]
        if missing:
            return ToolResult(
                call_id=hashlib.sha256(f"{name}:{time.time()}".encode()).hexdigest()[:12],
                success=False,
                error=f"Missing required arguments: {missing}",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        try:
            result = fn(arguments)
            return ToolResult(
                call_id=hashlib.sha256(f"{name}:{time.time()}".encode()).hexdigest()[:12],
                success=True,
                data=result,
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        except Exception as exc:
            return ToolResult(
                call_id=hashlib.sha256(f"{name}:{time.time()}".encode()).hexdigest()[:12],
                success=False,
                error=str(exc),
                duration_ms=(time.perf_counter() - t0) * 1000,
            )


# =============================================================================
# JSON-RPC Handler
# =============================================================================
class JSONRPCHandler:
    """Handle JSON-RPC 2.0 requests for MCP."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def handle(self, raw: str) -> str:
        try:
            req = json.loads(raw)
        except json.JSONDecodeError:
            return json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})
        if isinstance(req, list):
            return json.dumps([self._handle_single(r) for r in req])
        return json.dumps(self._handle_single(req))

    def _handle_single(self, req: Dict[str, Any]) -> Dict[str, Any]:
        req_id = req.get("id")
        method = req.get("method", "")
        params = req.get("params", {})
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                    "serverInfo": {"name": "magnatrix-mcp", "version": "1.0.0"},
                },
            }
        if method == "tools/list":
            schemas = self.registry.list_tools()
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": [{"name": s.name, "description": s.description, "inputSchema": s.parameters} for s in schemas]},
            }
        if method == "tools/call":
            name = params.get("name", "")
            args = params.get("arguments", {})
            result = self.registry.call(name, args)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result.__dict__, default=str)}],
                    "isError": not result.success,
                },
            }
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }


# =============================================================================
# Streaming Transport
# =============================================================================
class MCPTransport(ABC):
    @abstractmethod
    def start(self, handler: JSONRPCHandler) -> None: ...
    @abstractmethod
    def stop(self) -> None: ...
    @abstractmethod
    def send(self, message: str) -> None: ...


class StdioTransport(MCPTransport):
    """Read JSON-RPC from stdin, write to stdout."""

    def __init__(self) -> None:
        self._handler: Optional[JSONRPCHandler] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self, handler: JSONRPCHandler) -> None:
        self._handler = handler
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def _read_loop(self) -> None:
        import sys
        buffer = ""
        while self._running:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                buffer += line
                # Simple: each line is a JSON-RPC message
                if buffer.strip():
                    resp = self._handler.handle(buffer.strip()) if self._handler else ""
                    if resp:
                        print(resp, flush=True)
                    buffer = ""
            except Exception:
                break

    def stop(self) -> None:
        self._running = False

    def send(self, message: str) -> None:
        print(message, flush=True)


class HTTPTransport(MCPTransport):
    """HTTP server for MCP over REST."""

    def __init__(self, port: int = DEFAULT_MCP_PORT) -> None:
        self.port = port
        self._handler: Optional[JSONRPCHandler] = None
        self._server: Optional[Any] = None
        self._thread: Optional[threading.Thread] = None

    def start(self, handler: JSONRPCHandler) -> None:
        import http.server
        import socketserver
        self._handler = handler
        h = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                pass

            def do_POST(self) -> None:
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len).decode()
                resp = h._handler.handle(body) if h._handler else "{}"
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(resp.encode())

            def do_GET(self) -> None:
                if self.path == "/tools":
                    schemas = handler.registry.list_tools()
                    data = json.dumps({"tools": [s.__dict__ for s in schemas]}, default=str)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(data.encode())
                else:
                    self.send_response(404)
                    self.end_headers()

        self._server = socketserver.ThreadingTCPServer(("0.0.0.0", self.port), Handler)
        self._server.allow_reuse_address = True
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()

    def send(self, message: str) -> None:
        pass


# =============================================================================
# MCP Server
# =============================================================================
class MCPServer:
    """Full MCP server with tool registry and transport."""

    def __init__(self, transport: Optional[MCPTransport] = None) -> None:
        self.registry = ToolRegistry()
        self.handler = JSONRPCHandler(self.registry)
        self.transport = transport or StdioTransport()
        self._running = False

    def add_tool(self, name: str, description: str, fn: Callable[[Dict[str, Any]], Any], parameters: Dict[str, Any] = None, required: List[str] = None) -> None:
        schema = ToolSchema(
            name=name,
            description=description,
            parameters=parameters or {"type": "object", "properties": {}},
            required=required or [],
        )
        self.registry.register(schema, fn)

    def start(self) -> None:
        self._running = True
        self.transport.start(self.handler)

    def stop(self) -> None:
        self._running = False
        self.transport.stop()

    def __enter__(self) -> MCPServer:
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.stop()


# =============================================================================
# Demo Tools
# =============================================================================
def run_demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS MCP Server Demo")
    print("=" * 60)
    server = MCPServer()

    def echo_tool(args: Dict[str, Any]) -> str:
        return f"Echo: {args.get('message', '')}"

    def calc_tool(args: Dict[str, Any]) -> float:
        op = args.get("op", "+")
        a = float(args.get("a", 0))
        b = float(args.get("b", 0))
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if op == "/":
            return a / b if b != 0 else 0
        return 0

    server.add_tool(
        "echo",
        "Echo back a message",
        echo_tool,
        {"type": "object", "properties": {"message": {"type": "string"}}},
        ["message"],
    )
    server.add_tool(
        "calculate",
        "Basic arithmetic",
        calc_tool,
        {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}, "op": {"type": "string"}}},
        ["a", "b", "op"],
    )

    # Simulate JSON-RPC calls
    init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    print(f"Initialize: {server.handler.handle(init_req)}")

    list_req = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    print(f"Tools list: {server.handler.handle(list_req)}")

    call_req = json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "calculate", "arguments": {"a": 10, "b": 5, "op": "*"}}})
    print(f"Tool call: {server.handler.handle(call_req)}")

    print("Demo complete.")


if __name__ == "__main__":
    run_demo()
