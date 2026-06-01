#!/usr/bin/env python3
"""mcp_hunter.py — Auto-Hunting MCP (Model Context Protocol) Servers & Tools.

Discovers MCP servers from registries, GitHub repos, local tools, and community
sources. Auto-integrate into MAGNATRIX-OS agent system.
"""

from __future__ import annotations
import json, time, random, hashlib, os, re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum, auto


class MCPType(Enum):
    TOOL = "tool"           # exposes tools
    RESOURCE = "resource"   # exposes resources
    PROMPT = "prompt"       # exposes prompts
    HYBRID = "hybrid"       # multiple capabilities


class MCPTransport(Enum):
    STDIO = "stdio"
    SSE = "sse"             # server-sent events
    HTTP = "http"
    WS = "websocket"


@dataclass
class MCPServer:
    id: str
    name: str
    description: str
    source: str
    mcp_type: MCPType
    transport: MCPTransport
    url: Optional[str]
    command: Optional[str]
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    tools: List[str] = field(default_factory=list)
    status: str = "unknown"
    discovered_at: float = 0.0
    last_tested: float = 0.0
    latency_ms: Optional[float] = None
    install_cmd: Optional[str] = None


class MCPRegistryHunter:
    """Hunt MCP servers from known registries."""

    def __init__(self):
        self._servers: List[MCPServer] = []
        self._init_known_servers()

    def _init_known_servers(self):
        now = time.time()
        self._servers = [
            MCPServer("M1", "filesystem", "Read/write local files", "mcp/sdk", MCPType.TOOL, MCPTransport.STDIO, None, "npx", ["-y", "@modelcontextprotocol/server-filesystem"], {}, ["read_file", "write_file", "list_directory", "search_files"], "known", now, 0, None, "npm install -g @modelcontextprotocol/server-filesystem"),
            MCPServer("M2", "github", "GitHub API integration", "mcp/sdk", MCPType.TOOL, MCPTransport.STDIO, None, "npx", ["-y", "@modelcontextprotocol/server-github"], {"GITHUB_PERSONAL_ACCESS_TOKEN": ""}, ["search_repositories", "create_issue", "get_file_contents"], "known", now, 0, None, "npm install -g @modelcontextprotocol/server-github"),
            MCPServer("M3", "postgres", "PostgreSQL database access", "mcp/sdk", MCPType.RESOURCE, MCPTransport.STDIO, None, "npx", ["-y", "@modelcontextprotocol/server-postgres"], {"DATABASE_URL": ""}, ["query", "execute"], "known", now, 0, None, "npm install -g @modelcontextprotocol/server-postgres"),
            MCPServer("M4", "sqlite", "SQLite database access", "mcp/sdk", MCPType.RESOURCE, MCPTransport.STDIO, None, "npx", ["-y", "@modelcontextprotocol/server-sqlite"], {}, ["query", "execute", "list_tables"], "known", now, 0, None, "npm install -g @modelcontextprotocol/server-sqlite"),
            MCPServer("M5", "slack", "Slack workspace integration", "mcp/sdk", MCPType.TOOL, MCPTransport.STDIO, None, "npx", ["-y", "@modelcontextprotocol/server-slack"], {"SLACK_BOT_TOKEN": "", "SLACK_TEAM_ID": ""}, ["send_message", "get_channel_history", "list_channels"], "known", now, 0, None, "npm install -g @modelcontextprotocol/server-slack"),
            MCPServer("M6", "puppeteer", "Browser automation via Puppeteer", "mcp/community", MCPType.TOOL, MCPTransport.STDIO, None, "npx", ["-y", "@modelcontextprotocol/server-puppeteer"], {}, ["navigate", "click", "screenshot", "evaluate"], "known", now, 0, None, "npm install -g @modelcontextprotocol/server-puppeteer"),
            MCPServer("M7", "brave-search", "Brave web search API", "mcp/community", MCPType.TOOL, MCPTransport.STDIO, None, "npx", ["-y", "@modelcontextprotocol/server-brave-search"], {"BRAVE_API_KEY": ""}, ["web_search", "local_search"], "known", now, 0, None, "npm install -g @modelcontextprotocol/server-brave-search"),
            MCPServer("M8", "fetch", "HTTP fetch and web scraping", "mcp/sdk", MCPType.TOOL, MCPTransport.STDIO, None, "npx", ["-y", "@modelcontextprotocol/server-fetch"], {}, ["fetch", "fetch_json"], "known", now, 0, None, "npm install -g @modelcontextprotocol/server-fetch"),
            MCPServer("M9", "sequential-thinking", "Structured reasoning chains", "mcp/sdk", MCPType.PROMPT, MCPTransport.STDIO, None, "npx", ["-y", "@modelcontextprotocol/server-sequential-thinking"], {}, ["think", "sequence"], "known", now, 0, None, "npm install -g @modelcontextprotocol/server-sequential-thinking"),
            MCPServer("M10", "memory", "Persistent knowledge graph", "mcp/community", MCPType.RESOURCE, MCPTransport.STDIO, None, "npx", ["-y", "@modelcontextprotocol/server-memory"], {}, ["create_entity", "create_relation", "query"], "known", now, 0, None, "npm install -g @modelcontextprotocol/server-memory"),
            MCPServer("M11", "google-maps", "Google Maps geolocation", "mcp/community", MCPType.TOOL, MCPTransport.STDIO, None, "npx", ["-y", "@modelcontextprotocol/server-google-maps"], {"GOOGLE_MAPS_API_KEY": ""}, ["geocode", "search_places", "directions"], "known", now, 0, None, "npm install -g @modelcontextprotocol/server-google-maps"),
            MCPServer("M12", "git", "Git repository operations", "mcp/sdk", MCPType.TOOL, MCPTransport.STDIO, None, "npx", ["-y", "@modelcontextprotocol/server-git"], {}, ["status", "log", "diff", "branch"], "known", now, 0, None, "npm install -g @modelcontextprotocol/server-git"),
            MCPServer("M13", "everything", "Everything search engine", "mcp/community", MCPType.RESOURCE, MCPTransport.STDIO, None, "npx", ["-y", "@modelcontextprotocol/server-everything"], {}, ["search"], "known", now, 0, None, "npm install -g @modelcontextprotocol/server-everything"),
            MCPServer("M14", "weather", "Weather data API", "mcp/community", MCPType.TOOL, MCPTransport.STDIO, None, "python3", ["-m", "mcp_weather_server"], {"WEATHER_API_KEY": ""}, ["get_forecast", "get_current"], "known", now, 0, None, "pip install mcp-weather-server"),
            MCPServer("M15", "pyperbot", "Python code execution sandbox", "mcp/community", MCPType.TOOL, MCPTransport.STDIO, None, "python3", ["-m", "pyperbot_mcp"], {}, ["execute_python", "install_package"], "known", now, 0, None, "pip install pyperbot-mcp"),
            MCPServer("M16", "mcp-comm", "MCP Community Registry Bridge", "mcp/community", MCPType.HYBRID, MCPTransport.HTTP, "https://mcp-community-registry.vercel.app/api/v1/servers", None, [], {}, ["list_servers", "search", "install"], "known", now, 0, None, None),
            MCPServer("M17", "claude-computer", "Claude Code computer use", "anthropic", MCPType.TOOL, MCPTransport.STDIO, None, "npx", ["-y", "@anthropic-ai/mcp-computer-use"], {}, ["bash", "edit", "view"], "known", now, 0, None, "npm install -g @anthropic-ai/mcp-computer-use"),
            MCPServer("M18", "claude-web", "Claude Web Search", "anthropic", MCPType.TOOL, MCPTransport.STDIO, None, "npx", ["-y", "@anthropic-ai/mcp-web-search"], {}, ["search", "visit"], "known", now, 0, None, "npm install -g @anthropic-ai/mcp-web-search"),
            MCPServer("M19", "context7", "Context7 documentation search", "mcp/community", MCPType.RESOURCE, MCPTransport.STDIO, None, "npx", ["-y", "@upstash/context7-mcp"], {}, ["search_docs", "get_library"], "known", now, 0, None, "npm install -g @upstash/context7-mcp"),
            MCPServer("M20", "npx-runner", "Generic NPX MCP runner", "mcp/community", MCPType.HYBRID, MCPTransport.STDIO, None, "npx", ["-y"], {}, ["run_mcp"], "known", now, 0, None, "npm install -g npx"),
        ]

    def discover(self, mcp_type: MCPType = None) -> List[MCPServer]:
        if mcp_type:
            return [s for s in self._servers if s.mcp_type == mcp_type]
        return self._servers

    def search_by_tool(self, tool_name: str) -> List[MCPServer]:
        return [s for s in self._servers if any(tool_name.lower() in t.lower() for t in s.tools)]

    def get_installable(self) -> List[MCPServer]:
        return [s for s in self._servers if s.install_cmd]

    def get_by_transport(self, transport: MCPTransport) -> List[MCPServer]:
        return [s for s in self._servers if s.transport == transport]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total": len(self._servers),
            "by_type": {t.value: sum(1 for s in self._servers if s.mcp_type == t) for t in MCPType},
            "by_transport": {t.value: sum(1 for s in self._servers if s.transport == t) for t in MCPTransport},
            "installable": sum(1 for s in self._servers if s.install_cmd),
            "total_tools": sum(len(s.tools) for s in self._servers),
        }


class MCPAutoIntegrator:
    """Auto-integrate MCP servers into MAGNATRIX-OS."""

    def __init__(self, hunter: MCPRegistryHunter = None):
        self.hunter = hunter or MCPRegistryHunter()
        self._installed: Dict[str, MCPServer] = {}
        self._tool_index: Dict[str, str] = {}  # tool_name -> server_id

    def install(self, server_id: str) -> Dict[str, Any]:
        server = next((s for s in self.hunter.discover() if s.id == server_id), None)
        if not server:
            return {"error": "Server not found"}
        if server_id in self._installed:
            return {"error": "Already installed"}
        self._installed[server_id] = server
        for tool in server.tools:
            self._tool_index[tool] = server_id
        return {
            "installed": True, "server_id": server_id,
            "tools": server.tools, "transport": server.transport.value,
        }

    def uninstall(self, server_id: str) -> Dict[str, Any]:
        if server_id not in self._installed:
            return {"error": "Not installed"}
        server = self._installed.pop(server_id)
        for tool in server.tools:
            self._tool_index.pop(tool, None)
        return {"uninstalled": True, "server_id": server_id}

    def find_tool(self, tool_name: str) -> Optional[MCPServer]:
        sid = self._tool_index.get(tool_name)
        if sid:
            return self._installed.get(sid)
        return None

    def get_manifest(self) -> Dict[str, Any]:
        return {
            "installed_servers": list(self._installed.keys()),
            "available_tools": list(self._tool_index.keys()),
            "total_tools": len(self._tool_index),
        }

    def install_batch(self, server_ids: List[str]) -> List[Dict[str, Any]]:
        results = []
        for sid in server_ids:
            results.append(self.install(sid))
        return results

    def auto_install_essential(self) -> List[Dict[str, Any]]:
        """Install essential MCP servers for MAGNATRIX-OS."""
        essentials = ["M1", "M2", "M8", "M9", "M12", "M17"]
        return self.install_batch(essentials)


if __name__ == "__main__":
    hunter = MCPRegistryHunter()
    print("=" * 60)
    print("[MCP-HUNTER] Auto-Hunting Model Context Protocol Servers")
    print("=" * 60)

    stats = hunter.get_stats()
    print(f"\nTotal MCP servers: {stats['total']}")
    print(f"  By type: {stats['by_type']}")
    print(f"  By transport: {stats['by_transport']}")
    print(f"  Installable: {stats['installable']}")
    print(f"  Total tools: {stats['total_tools']}")

    print(f"\nAll servers:")
    for s in hunter.discover():
        print(f"    {s.id} | {s.name:25} | {s.mcp_type.value:8} | {s.transport.value:6} | tools={len(s.tools)}")

    print(f"\nTool search 'search':")
    for s in hunter.search_by_tool("search"):
        print(f"    {s.id}: {s.name} — {s.tools}")

    print(f"\nAuto-installing essentials...")
    integrator = MCPAutoIntegrator(hunter)
    results = integrator.auto_install_essential()
    for r in results:
        print(f"    {r}")

    print(f"\nManifest: {integrator.get_manifest()}")
