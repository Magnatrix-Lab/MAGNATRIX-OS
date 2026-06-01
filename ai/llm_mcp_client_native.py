#!/usr/bin/env python3
"""
ai/llm_mcp_client_native.py
MAGNATRIX-OS — MCP Client for the LLM Arena
AMATI pattern: Model Context Protocol server connection, tool discovery, request handling

Pure Python, stdlib only. Simulates MCP server connections, tool registry,
and JSON-RPC request/response handling.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ───────────────────────────────────────────────────────────────
# 0. UTILITIES
# ───────────────────────────────────────────────────────────────

def _now() -> float:
    return time.time()


def _jsonrpc_request(method: str, params: Dict[str, Any], req_id: int) -> str:
    return json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": req_id})


def _jsonrpc_response(result: Any, req_id: int) -> str:
    return json.dumps({"jsonrpc": "2.0", "result": result, "id": req_id})


def _jsonrpc_error(error: str, req_id: int) -> str:
    return json.dumps({"jsonrpc": "2.0", "error": {"message": error, "code": -1}, "id": req_id})


# ───────────────────────────────────────────────────────────────
# 1. MCP CONNECTION
# ───────────────────────────────────────────────────────────────

@dataclass
class MCPServer:
    server_id: str
    name: str
    transport: str  # stdio or http
    endpoint: str
    capabilities: List[str] = field(default_factory=list)
    status: str = "disconnected"
    last_ping: float = 0.0


class MCPConnection:
    """Connect to MCP servers via stdio or HTTP simulation."""

    def __init__(self) -> None:
        self._servers: Dict[str, MCPServer] = {}
        self._req_id = 0

    def connect(self, server_id: str, name: str, transport: str, endpoint: str) -> MCPServer:
        server = MCPServer(server_id, name, transport, endpoint, status="connected", last_ping=_now())
        self._servers[server_id] = server
        return server

    def disconnect(self, server_id: str) -> bool:
        if server_id in self._servers:
            self._servers[server_id].status = "disconnected"
            return True
        return False

    def ping(self, server_id: str) -> bool:
        server = self._servers.get(server_id)
        if server and server.status == "connected":
            server.last_ping = _now()
            return True
        return False

    def list_servers(self) -> List[MCPServer]:
        return list(self._servers.values())

    def next_req_id(self) -> int:
        self._req_id += 1
        return self._req_id


# ───────────────────────────────────────────────────────────────
# 2. TOOL REGISTRY
# ───────────────────────────────────────────────────────────────

@dataclass
class MCPTool:
    tool_name: str
    server_id: str
    description: str
    parameters: Dict[str, Any]
    required: List[str] = field(default_factory=list)


class ToolRegistry:
    """Discover and register tools from MCP servers."""

    def __init__(self) -> None:
        self._tools: Dict[str, MCPTool] = {}

    def register(self, tool: MCPTool) -> None:
        self._tools[tool.tool_name] = tool

    def discover(self, server_id: str, simulated_tools: List[Dict[str, Any]]) -> List[MCPTool]:
        tools = []
        for t in simulated_tools:
            tool = MCPTool(
                tool_name=t["name"],
                server_id=server_id,
                description=t.get("description", ""),
                parameters=t.get("parameters", {}),
                required=t.get("required", []),
            )
            self.register(tool)
            tools.append(tool)
        return tools

    def get(self, tool_name: str) -> Optional[MCPTool]:
        return self._tools.get(tool_name)

    def list_tools(self) -> List[MCPTool]:
        return list(self._tools.values())

    def by_server(self, server_id: str) -> List[MCPTool]:
        return [t for t in self._tools.values() if t.server_id == server_id]


# ───────────────────────────────────────────────────────────────
# 3. REQUEST BUILDER
# ───────────────────────────────────────────────────────────────

class RequestBuilder:
    """Build MCP-compliant JSON-RPC requests."""

    def build(self, tool_name: str, arguments: Dict[str, Any], req_id: int) -> str:
        return _jsonrpc_request("tools/call", {"name": tool_name, "arguments": arguments}, req_id)

    def build_discover(self, req_id: int) -> str:
        return _jsonrpc_request("tools/list", {}, req_id)

    def build_ping(self, req_id: int) -> str:
        return _jsonrpc_request("ping", {}, req_id)


# ───────────────────────────────────────────────────────────────
# 4. RESPONSE PARSER
# ───────────────────────────────────────────────────────────────

class ResponseParser:
    """Parse MCP JSON-RPC responses."""

    def parse(self, raw: str) -> Dict[str, Any]:
        try:
            data = json.loads(raw)
            if "error" in data:
                return {"success": False, "error": data["error"]["message"], "id": data.get("id")}
            return {"success": True, "result": data.get("result"), "id": data.get("id")}
        except json.JSONDecodeError as e:
            return {"success": False, "error": str(e), "id": None}

    def parse_tool_result(self, raw: str) -> Dict[str, Any]:
        parsed = self.parse(raw)
        if parsed["success"] and parsed["result"]:
            result = parsed["result"]
            if isinstance(result, dict) and "content" in result:
                return {"success": True, "content": result["content"], "is_error": result.get("isError", False)}
        return parsed


# ───────────────────────────────────────────────────────────────
# 5. SERVER MANAGER
# ───────────────────────────────────────────────────────────────

class ServerManager:
    """Manage multiple MCP server connections with health checks."""

    def __init__(self, connection: MCPConnection) -> None:
        self.connection = connection
        self._health: Dict[str, bool] = {}

    def health_check(self, server_id: str) -> bool:
        healthy = self.connection.ping(server_id)
        self._health[server_id] = healthy
        return healthy

    def health_check_all(self) -> Dict[str, bool]:
        for sid in self.connection._servers:
            self.health_check(sid)
        return self._health.copy()

    def reconnect(self, server_id: str) -> bool:
        server = self.connection._servers.get(server_id)
        if server:
            server.status = "connected"
            server.last_ping = _now()
            return True
        return False

    def get_healthy_servers(self) -> List[str]:
        return [sid for sid, healthy in self._health.items() if healthy]


# ───────────────────────────────────────────────────────────────
# 6. SESSION MANAGER
# ───────────────────────────────────────────────────────────────

class SessionManager:
    """Maintain session state across MCP calls."""

    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def create(self, session_id: str) -> None:
        self._sessions[session_id] = {"created_at": _now(), "calls": 0, "context": {}}

    def update(self, session_id: str, context: Dict[str, Any]) -> None:
        if session_id in self._sessions:
            self._sessions[session_id]["context"].update(context)
            self._sessions[session_id]["calls"] += 1

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._sessions.get(session_id)

    def cleanup(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


# ───────────────────────────────────────────────────────────────
# 7. MCP CLIENT
# ───────────────────────────────────────────────────────────────

class MCPClient:
    """Main orchestrator: connect -> discover -> build -> send -> parse -> manage."""

    def __init__(self) -> None:
        self.connection = MCPConnection()
        self.registry = ToolRegistry()
        self.builder = RequestBuilder()
        self.parser = ResponseParser()
        self.servers = ServerManager(self.connection)
        self.sessions = SessionManager()

    def connect(self, server_id: str, name: str, transport: str, endpoint: str) -> MCPServer:
        return self.connection.connect(server_id, name, transport, endpoint)

    def discover_tools(self, server_id: str, simulated_tools: List[Dict[str, Any]]) -> List[MCPTool]:
        return self.registry.discover(server_id, simulated_tools)

    def call_tool(self, tool_name: str, arguments: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        tool = self.registry.get(tool_name)
        if not tool:
            return {"success": False, "error": f"Tool {tool_name} not found"}

        req_id = self.connection.next_req_id()
        request = self.builder.build(tool_name, arguments, req_id)

        # Simulate sending and receiving
        simulated_response = _jsonrpc_response({
            "content": [{"type": "text", "text": f"Simulated result for {tool_name} with args {arguments}"}],
            "isError": False,
        }, req_id)

        result = self.parser.parse_tool_result(simulated_response)

        if session_id:
            self.sessions.update(session_id, {"tool": tool_name, "args": arguments})

        return result

    def health_check(self) -> Dict[str, bool]:
        return self.servers.health_check_all()

    def stats(self) -> Dict[str, Any]:
        return {
            "servers": len(self.connection.list_servers()),
            "tools": len(self.registry.list_tools()),
            "sessions": len(self.sessions._sessions),
        }


# ───────────────────────────────────────────────────────────────
# 8. DEMO
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS MCP Client Demo")
    print("=" * 60)

    client = MCPClient()

    # Connect to simulated MCP servers
    print("\n[1] Connecting to MCP servers...")
    client.connect("server_1", "File System MCP", "stdio", "fs-mcp")
    client.connect("server_2", "Web Search MCP", "http", "http://search-mcp.local")
    client.connect("server_3", "Database MCP", "stdio", "db-mcp")
    print(f"  Connected: {client.stats()['servers']} servers")

    # Discover tools
    print("\n[2] Discovering tools...")
    fs_tools = [
        {"name": "read_file", "description": "Read file contents", "parameters": {"path": {"type": "string"}}, "required": ["path"]},
        {"name": "write_file", "description": "Write to file", "parameters": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]},
    ]
    search_tools = [
        {"name": "web_search", "description": "Search the web", "parameters": {"query": {"type": "string"}}, "required": ["query"]},
    ]
    db_tools = [
        {"name": "query_db", "description": "Query database", "parameters": {"sql": {"type": "string"}}, "required": ["sql"]},
    ]
    client.discover_tools("server_1", fs_tools)
    client.discover_tools("server_2", search_tools)
    client.discover_tools("server_3", db_tools)
    print(f"  Tools discovered: {client.stats()['tools']}")
    for t in client.registry.list_tools():
        print(f"    - {t.tool_name} ({t.server_id})")

    # Call tools
    print("\n[3] Calling tools...")
    result = client.call_tool("read_file", {"path": "/tmp/test.txt"}, session_id="sess_1")
    print(f"  read_file: {result}")
    result = client.call_tool("web_search", {"query": "Python tutorials"}, session_id="sess_1")
    print(f"  web_search: {result}")
    result = client.call_tool("query_db", {"sql": "SELECT * FROM users"}, session_id="sess_1")
    print(f"  query_db: {result}")

    # Health check
    print("\n[4] Health check...")
    health = client.health_check()
    for sid, status in health.items():
        print(f"  {sid}: {'HEALTHY' if status else 'UNHEALTHY'}")

    print(f"\n[STATS] {json.dumps(client.stats(), indent=2)}")

    print("\n" + "=" * 60)
    print("Demo complete. MCP Client ready for LLM Arena.")
    print("=" * 60)
