"""
MAGNATRIX — Hostinger MCP Bridge
══════════════════════════════════
Integration dengan Hostinger API via Model Context Protocol (MCP).

Hostinger MCP server: npx hostinger-api-mcp@latest
Connect via stdio transport — semua API calls ke Hostinger (VPS, DNS, domain, etc.)
dapat diakses oleh MAGNATRIX agents sebagai native tools.

Features:
- MCP stdio client connection
- Auto-discovery Hostinger tools (list_vps, restart_vps, get_metrics, etc.)
- Native integration dengan DynamicToolForge — Hostinger tools jadi agent tools
- VPS lifecycle management via natural language delegation
- Auto-deploy integration: agent bisa trigger deploy sendiri via MCP

Author: MAGNATRIX-OS
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class HostingerMCPConfig:
    """Konfigurasi koneksi ke Hostinger MCP server."""
    api_token: str
    server_name: str = "hostinger-mcp"
    command: str = "npx"
    package: str = "hostinger-api-mcp@latest"
    timeout: float = 30.0

    @classmethod
    def from_env(cls) -> "HostingerMCPConfig":
        token = os.environ.get("HOSTINGER_MCP_API_TOKEN") or os.environ.get("HOSTINGER_API_TOKEN")
        if not token:
            raise ValueError("HOSTINGER_MCP_API_TOKEN tidak ditemukan di environment")
        return cls(api_token=token)


@dataclass
class MCPRequest:
    """JSON-RPC request untuk MCP server."""
    jsonrpc: str = "2.0"
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    method: str = ""
    params: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps({
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": self.method,
            "params": self.params,
        }) + "\n"


@dataclass
class MCPResponse:
    """JSON-RPC response dari MCP server."""
    id: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

    @property
    def success(self) -> bool:
        return self.error is None and self.result is not None


class HostingerMCPBridge:
    """Bridge ke Hostinger MCP server via stdio transport.

    Menghubungkan MAGNATRIX agents dengan Hostinger API untuk:
    - VPS management (list, start, stop, restart, scale)
    - Domain & DNS management
    - Resource monitoring (CPU, RAM, disk, bandwidth)
    - Auto-deploy trigger
    """

    def __init__(self, config: Optional[HostingerMCPConfig] = None):
        self.config = config or HostingerMCPConfig.from_env()
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._lock = asyncio.Lock()
        self._tools: List[Dict[str, Any]] = []
        self._connected = False
        self._buffer = ""

    # ── Lifecycle ───────────────────────────────────────────────────────

    async def connect(self) -> Dict[str, Any]:
        """Start Hostinger MCP server via stdio dan initialize."""
        async with self._lock:
            if self._connected:
                return {"success": True, "status": "already_connected"}

            try:
                self._proc = await asyncio.create_subprocess_exec(
                    self.config.command,
                    self.config.package,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env={
                        **os.environ,
                        "API_TOKEN": self.config.api_token,
                    },
                )

                # Initialize MCP session
                init_req = MCPRequest(method="initialize", params={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "magnatrix-hostinger-bridge", "version": "1.0.0"},
                })
                await self._send_raw(init_req.to_json())
                resp = await self._read_response(timeout=10.0)

                if resp and resp.success:
                    self._connected = True
                    # Discover available tools
                    await self._discover_tools()
                    return {
                        "success": True,
                        "status": "connected",
                        "tools_discovered": len(self._tools),
                        "tools": [t.get("name") for t in self._tools],
                    }
                else:
                    return {"success": False, "error": "MCP initialize failed", "response": resp}

            except Exception as e:
                return {"success": False, "error": str(e)}

    async def disconnect(self) -> None:
        async with self._lock:
            if self._proc:
                self._proc.stdin.write_eof() if self._proc.stdin else None
                try:
                    await asyncio.wait_for(self._proc.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    self._proc.kill()
                self._proc = None
                self._connected = False
                self._tools = []

    # ── Tool Execution ──────────────────────────────────────────────────

    async def call(self, method: str, params: Optional[Dict[str, Any]] = None) -> MCPResponse:
        """Panggil method Hostinger API via MCP."""
        async with self._lock:
            if not self._connected or not self._proc:
                raise RuntimeError("Not connected to Hostinger MCP server")

            req = MCPRequest(method=method, params=params or {})
            await self._send_raw(req.to_json())
            resp = await self._read_response(timeout=self.config.timeout)
            return resp or MCPResponse(id=req.id, error={"message": "No response"})

    async def list_vps(self) -> Dict[str, Any]:
        """List semua VPS di akun Hostinger."""
        resp = await self.call("list_vps")
        if resp.success:
            return {"success": True, "vps_list": resp.result}
        return {"success": False, "error": resp.error}

    async def get_vps_status(self, vps_id: str) -> Dict[str, Any]:
        """Get status detail satu VPS."""
        resp = await self.call("get_vps_status", {"vps_id": vps_id})
        if resp.success:
            return {"success": True, "status": resp.result}
        return {"success": False, "error": resp.error}

    async def restart_vps(self, vps_id: str) -> Dict[str, Any]:
        """Restart VPS."""
        resp = await self.call("restart_vps", {"vps_id": vps_id})
        return {
            "success": resp.success,
            "result": resp.result if resp.success else None,
            "error": resp.error if not resp.success else None,
        }

    async def get_metrics(self, vps_id: str, period: str = "1h") -> Dict[str, Any]:
        """Get resource metrics (CPU, RAM, disk, bandwidth)."""
        resp = await self.call("get_metrics", {"vps_id": vps_id, "period": period})
        if resp.success:
            return {"success": True, "metrics": resp.result}
        return {"success": False, "error": resp.error}

    async def list_domains(self) -> Dict[str, Any]:
        """List semua domain di akun Hostinger."""
        resp = await self.call("list_domains")
        if resp.success:
            return {"success": True, "domains": resp.result}
        return {"success": False, "error": resp.error}

    async def update_dns_record(self, domain: str, record_type: str, name: str, value: str) -> Dict[str, Any]:
        """Update DNS record untuk domain."""
        resp = await self.call("update_dns", {
            "domain": domain,
            "type": record_type,
            "name": name,
            "value": value,
        })
        return {
            "success": resp.success,
            "result": resp.result if resp.success else None,
            "error": resp.error if not resp.success else None,
        }

    async def deploy_website(self, vps_id: str, repo_url: str, branch: str = "main") -> Dict[str, Any]:
        """Trigger deploy website ke VPS via Hostinger API."""
        resp = await self.call("deploy_website", {
            "vps_id": vps_id,
            "repo_url": repo_url,
            "branch": branch,
        })
        return {
            "success": resp.success,
            "deployment": resp.result if resp.success else None,
            "error": resp.error if not resp.success else None,
        }

    # ── Tool Schema untuk DynamicToolForge ───────────────────────────────

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Generate JSON schema untuk setiap Hostinger tool — bisa diregister ke DynamicToolForge."""
        return [
            {
                "name": "hostinger_list_vps",
                "description": "List all VPS instances in Hostinger account",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "hostinger_get_vps_status",
                "description": "Get detailed status of a specific VPS",
                "parameters": {
                    "type": "object",
                    "properties": {"vps_id": {"type": "string", "description": "VPS identifier"}},
                    "required": ["vps_id"],
                },
            },
            {
                "name": "hostinger_restart_vps",
                "description": "Restart a VPS instance",
                "parameters": {
                    "type": "object",
                    "properties": {"vps_id": {"type": "string", "description": "VPS identifier"}},
                    "required": ["vps_id"],
                },
            },
            {
                "name": "hostinger_get_metrics",
                "description": "Get resource metrics (CPU, RAM, disk, bandwidth) for a VPS",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "vps_id": {"type": "string"},
                        "period": {"type": "string", "enum": ["1h", "24h", "7d", "30d"], "default": "1h"},
                    },
                    "required": ["vps_id"],
                },
            },
            {
                "name": "hostinger_list_domains",
                "description": "List all domains in Hostinger account",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "hostinger_update_dns",
                "description": "Update a DNS record for a domain",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "domain": {"type": "string"},
                        "record_type": {"type": "string", "enum": ["A", "AAAA", "CNAME", "MX", "TXT", "NS"]},
                        "name": {"type": "string"},
                        "value": {"type": "string"},
                    },
                    "required": ["domain", "record_type", "name", "value"],
                },
            },
            {
                "name": "hostinger_deploy_website",
                "description": "Deploy a website from a git repository to a VPS",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "vps_id": {"type": "string"},
                        "repo_url": {"type": "string"},
                        "branch": {"type": "string", "default": "main"},
                    },
                    "required": ["vps_id", "repo_url"],
                },
            },
        ]

    async def register_to_forge(self, forge: Any) -> Dict[str, Any]:
        """Register semua Hostinger tools ke DynamicToolForge."""
        schemas = self.get_tool_schemas()
        registered = []
        for schema in schemas:
            tool_name = schema["name"]
            # Generate dynamic wrapper code
            method_name = tool_name.replace("hostinger_", "").replace("_", "_")
            code = f'''
def run(**kwargs) -> dict:
    import asyncio
    bridge = _HOSTINGER_BRIDGE_INSTANCE
    method = "{method_name}"
    # Map ke method yang sesuai
    coro = getattr(bridge, method, None)
    if coro is None:
        # Fallback: direct MCP call
        coro = lambda **kw: bridge.call(method.replace("_", "."), kw)
    try:
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(coro(**kwargs))
    except RuntimeError:
        result = asyncio.run(coro(**kwargs))
    return result if isinstance(result, dict) else {{"success": True, "result": result}}
'''
            try:
                sig = await forge.forge_tool(tool_name, code, description=schema["description"])
                registered.append(tool_name)
            except Exception as e:
                pass  # skip duplikat atau error
        return {"registered": registered, "count": len(registered)}

    # ── Internal Transport ─────────────────────────────────────────────

    async def _send_raw(self, data: str) -> None:
        self._proc.stdin.write(data.encode("utf-8"))
        await self._proc.stdin.drain()

    async def _read_response(self, timeout: float = 30.0) -> Optional[MCPResponse]:
        """Baca JSON-RPC response dari stdout MCP server."""
        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            try:
                data = await asyncio.wait_for(
                    self._proc.stdout.readline(),
                    timeout=min(1.0, deadline - asyncio.get_event_loop().time()),
                )
                if not data:
                    continue
                line = data.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                    return MCPResponse(
                        id=parsed.get("id", "unknown"),
                        result=parsed.get("result"),
                        error=parsed.get("error"),
                    )
                except json.JSONDecodeError:
                    continue
            except asyncio.TimeoutError:
                continue
        return None

    async def _discover_tools(self) -> None:
        """Discover available tools dari Hostinger MCP server."""
        try:
            resp = await self.call("tools/list")
            if resp.success and resp.result:
                self._tools = resp.result.get("tools", [])
        except Exception:
            # Fallback: gunakan hardcoded schemas
            self._tools = self.get_tool_schemas()


# ═══════════════════════════════════════════════════════════════════════════
# Auto-Deploy Integration — Agent bisa deploy MAGNATRIX sendiri via MCP
# ═══════════════════════════════════════════════════════════════════════════

class HostingerAutoDeployer:
    """Agent-triggered deploy ke Hostinger VPS via MCP bridge.

    Agent Zero bisa: \"Deploy MAGNATRIX ke VPS sekarang\" →
    → HostingerAutoDeployer handle via HostingerMCPBridge
    """

    def __init__(self, bridge: HostingerMCPBridge):
        self.bridge = bridge

    async def deploy_magnatrix(
        self,
        vps_id: Optional[str] = None,
        repo_url: str = "https://github.com/Magnatrix-Lab/MAGNATRIX-OS.git",
        branch: str = "main",
    ) -> Dict[str, Any]:
        """Full deploy pipeline: pull latest, build, restart container."""
        # Jika vps_id tidak diberikan, list dan pilih yang aktif
        if not vps_id:
            vps_list = await self.bridge.list_vps()
            if not vps_list.get("success"):
                return {"success": False, "error": "Cannot list VPS"}
            vps_instances = vps_list.get("vps_list", [])
            if not vps_instances:
                return {"success": False, "error": "No VPS found in Hostinger account"}
            vps_id = vps_instances[0].get("id")

        # Step 1: Deploy website (pull repo)
        deploy_result = await self.bridge.deploy_website(vps_id, repo_url, branch)
        if not deploy_result.get("success"):
            return deploy_result

        # Step 2: Get post-deploy status
        status = await self.bridge.get_vps_status(vps_id)

        return {
            "success": True,
            "vps_id": vps_id,
            "deployment": deploy_result.get("deployment"),
            "vps_status": status.get("status") if status.get("success") else None,
            "message": "MAGNATRIX deployed via Hostinger MCP",
        }

    async def restart_service(self, vps_id: str, service: str = "magnatrix-core") -> Dict[str, Any]:
        """Restart service di VPS."""
        resp = await self.bridge.call("execute_command", {
            "vps_id": vps_id,
            "command": f"docker restart {service}",
        })
        return {
            "success": resp.success,
            "result": resp.result if resp.success else None,
            "error": resp.error if not resp.success else None,
        }

    async def get_health_report(self, vps_id: str) -> Dict[str, Any]:
        """Generate health report untuk VPS MAGNATRIX."""
        metrics = await self.bridge.get_metrics(vps_id, period="1h")
        status = await self.bridge.get_vps_status(vps_id)

        report = {
            "timestamp": asyncio.get_event_loop().time(),
            "vps_id": vps_id,
            "vps_status": status.get("status") if status.get("success") else "unknown",
            "metrics": metrics.get("metrics") if metrics.get("success") else None,
            "healthy": status.get("success") and metrics.get("success"),
        }
        return {"success": True, "report": report}


# ═══════════════════════════════════════════════════════════════════════════
# Standalone Demo
# ═══════════════════════════════════════════════════════════════════════════

async def demo_hostinger_mcp():
    print("═" * 60)
    print("MAGNATRIX — Hostinger MCP Bridge Demo")
    print("═" * 60)

    try:
        config = HostingerMCPConfig.from_env()
        print(f"[1] Config loaded — token: {config.api_token[:8]}...")
    except ValueError as e:
        print(f"[SKIP] {e}")
        print("Set HOSTINGER_MCP_API_TOKEN environment variable untuk demo penuh.")
        return

    bridge = HostingerMCPBridge(config)

    # Connect
    connect_result = await bridge.connect()
    print(f"[2] Connect: {connect_result}")

    if not connect_result.get("success"):
        print("[SKIP] Cannot connect to MCP server")
        return

    # List VPS
    vps = await bridge.list_vps()
    print(f"[3] VPS list: {vps}")

    # List domains
    domains = await bridge.list_domains()
    print(f"[4] Domains: {domains}")

    # Tool schemas
    schemas = bridge.get_tool_schemas()
    print(f"[5] Tool schemas: {len(schemas)} tools available")
    for s in schemas:
        print(f"    - {s['name']}: {s['description']}")

    # Auto deployer
    deployer = HostingerAutoDeployer(bridge)
    report = await deployer.get_health_report("demo-vps-id")
    print(f"[6] Health report template: {report}")

    await bridge.disconnect()
    print("[7] Disconnected")
    print("═" * 60)


if __name__ == "__main__":
    asyncio.run(demo_hostinger_mcp())
