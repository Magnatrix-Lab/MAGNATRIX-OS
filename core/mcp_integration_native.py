#!/usr/bin/env python3
"""mcp_integration_native.py — MAGNATRIX-OS MCP & Channel Integration Engine

Model Context Protocol integration + channel-based external tool abstraction.
Inspired by Agent Reach pattern. Channels: register, health-check, credential-manage.
Pure stdlib (HTTP via urllib, JSON-RPC style).
"""
from __future__ import annotations
import json
import threading
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable


@dataclass
class ChannelConfig:
    name: str
    type: str  # api, cli, browser, mcp
    endpoint: str  # URL for API, command path for CLI, extension ID for browser
    auth_type: str = "none"  # none, api_key, oauth, cookie, browser_reuse
    credentials: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    health_endpoint: str = ""
    enabled: bool = True
    last_health_check: float = 0.0
    health_status: str = "unknown"  # unknown, pass, fail, warning
    health_reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class MCPRequest:
    id: str
    method: str
    params: Dict[str, Any]
    channel: str
    timeout: float = 30.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class MCPResponse:
    id: str
    status: str  # success, error, timeout, unavailable
    result: Any = None
    error: str = ""
    latency: float = 0.0
    channel: str = ""
    timestamp: float = field(default_factory=time.time)


class MCPIntegrationNative:
    """Native MCP + channel integration engine — external tool abstraction."""

    def __init__(self, workspace: str = "./mcp_integration") -> None:
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self._channels: Dict[str, ChannelConfig] = {}
        self._request_log: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self._channels_path = self.workspace / "channels.json"
        self._log_path = self.workspace / "request_log.json"
        self._load()

    def _load(self) -> None:
        if self._channels_path.exists():
            try:
                with open(self._channels_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for name, cd in data.items(): self._channels[name] = ChannelConfig(**cd)
            except Exception: pass
        if self._log_path.exists():
            try:
                with open(self._log_path, "r", encoding="utf-8") as f:
                    self._request_log = json.load(f)
            except Exception: pass

    def _save(self) -> None:
        with open(self._channels_path, "w", encoding="utf-8") as f:
            json.dump({name: asdict(c) for name, c in self._channels.items()}, f, indent=2, default=str)
        with open(self._log_path, "w", encoding="utf-8") as f:
            json.dump(self._request_log[-5000:], f, indent=2, default=str)

    def register_channel(self, name: str, type: str, endpoint: str, auth_type: str = "none", credentials: Optional[Dict[str, str]] = None, headers: Optional[Dict[str, str]] = None, health_endpoint: str = "", metadata: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            self._channels[name] = ChannelConfig(
                name=name, type=type, endpoint=endpoint, auth_type=auth_type,
                credentials=credentials or {}, headers=headers or {},
                health_endpoint=health_endpoint, metadata=metadata or {}
            )
            self._save()

    def remove_channel(self, name: str) -> bool:
        with self._lock:
            if name in self._channels: del self._channels[name]; self._save(); return True
            return False

    def list_channels(self, status: Optional[str] = None) -> List[str]:
        with self._lock:
            names = list(self._channels.keys())
            if status: names = [n for n in names if self._channels[n].health_status == status]
            return names

    def configure_credentials(self, channel_name: str, credentials: Dict[str, str]) -> bool:
        with self._lock:
            if channel_name not in self._channels: return False
            self._channels[channel_name].credentials.update(credentials)
            self._save(); return True

    def health_check(self, channel_name: Optional[str] = None) -> Dict[str, Any]:
        """Run health check on channels. Returns channel -> {status, reason, latency}."""
        with self._lock:
            results = {}
            channels_to_check = [channel_name] if channel_name else list(self._channels.keys())
            for name in channels_to_check:
                if name not in self._channels: continue
                ch = self._channels[name]
                if not ch.enabled: ch.health_status = "warning"; ch.health_reason = "Channel disabled"; ch.last_health_check = time.time(); continue
                start = time.time()
                try:
                    if ch.type == "api":
                        url = ch.health_endpoint or ch.endpoint
                        req = urllib.request.Request(url, headers={**ch.headers, **self._build_auth_headers(ch)}, method="HEAD")
                        with urllib.request.urlopen(req, timeout=10) as resp:
                            ch.health_status = "pass" if resp.status < 400 else "fail"
                            ch.health_reason = f"HTTP {resp.status}" if resp.status >= 400 else "OK"
                    elif ch.type == "mcp":
                        # MCP JSON-RPC health check
                        health_req = {"jsonrpc": "2.0", "id": str(uuid.uuid4())[:8], "method": "health", "params": {}}
                        req = urllib.request.Request(
                            ch.endpoint, data=json.dumps(health_req).encode("utf-8"),
                            headers={"Content-Type": "application/json", **ch.headers, **self._build_auth_headers(ch)},
                            method="POST"
                        )
                        with urllib.request.urlopen(req, timeout=10) as resp:
                            data = json.loads(resp.read().decode("utf-8"))
                            ch.health_status = "pass" if data.get("result") else "fail"
                            ch.health_reason = "MCP health OK" if data.get("result") else "MCP health failed"
                    elif ch.type == "cli":
                        # Check if command exists (placeholder)
                        ch.health_status = "pass"
                        ch.health_reason = "CLI tool available (placeholder)"
                    elif ch.type == "browser":
                        ch.health_status = "pass"
                        ch.health_reason = "Browser extension status check (placeholder)"
                    else:
                        ch.health_status = "warning"
                        ch.health_reason = "Unknown channel type"
                except Exception as e:
                    ch.health_status = "fail"
                    ch.health_reason = str(e)
                ch.last_health_check = time.time()
                ch.metadata["health_latency"] = time.time() - start
                results[name] = {"status": ch.health_status, "reason": ch.health_reason, "latency": ch.metadata["health_latency"]}
            self._save()
            return results

    def _build_auth_headers(self, ch: ChannelConfig) -> Dict[str, str]:
        if ch.auth_type == "api_key" and "api_key" in ch.credentials:
            return {"Authorization": f"Bearer {ch.credentials['api_key']}"}
        elif ch.auth_type == "cookie" and "cookie" in ch.credentials:
            return {"Cookie": ch.credentials["cookie"]}
        return {}

    def call(self, channel_name: str, method: str, params: Dict[str, Any], timeout: float = 30.0) -> MCPResponse:
        """Call a method on a channel. Returns MCPResponse."""
        with self._lock:
            if channel_name not in self._channels:
                return MCPResponse(id=str(uuid.uuid4())[:8], status="unavailable", error="Channel not found", channel=channel_name)
            ch = self._channels[channel_name]
            if not ch.enabled:
                return MCPResponse(id=str(uuid.uuid4())[:8], status="unavailable", error="Channel disabled", channel=channel_name)
            req_id = str(uuid.uuid4())[:8]
            start = time.time()
            try:
                if ch.type == "api" or ch.type == "mcp":
                    payload = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
                    req = urllib.request.Request(
                        ch.endpoint, data=json.dumps(payload).encode("utf-8"),
                        headers={"Content-Type": "application/json", **ch.headers, **self._build_auth_headers(ch)},
                        method="POST"
                    )
                    with urllib.request.urlopen(req, timeout=timeout) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        latency = time.time() - start
                        result = MCPResponse(id=req_id, status="success", result=data.get("result"), error=data.get("error", {}).get("message", ""), latency=latency, channel=channel_name)
                elif ch.type == "cli":
                    # CLI invocation (placeholder)
                    result = MCPResponse(id=req_id, status="success", result={"message": f"CLI call: {method} with {params}"}, latency=time.time() - start, channel=channel_name)
                elif ch.type == "browser":
                    result = MCPResponse(id=req_id, status="success", result={"message": f"Browser call: {method} with {params}"}, latency=time.time() - start, channel=channel_name)
                else:
                    result = MCPResponse(id=req_id, status="error", error="Unknown channel type", channel=channel_name)
            except Exception as e:
                result = MCPResponse(id=req_id, status="error", error=str(e), latency=time.time() - start, channel=channel_name)
            # Log request
            self._request_log.append({"timestamp": time.time(), "req_id": req_id, "channel": channel_name, "method": method, "status": result.status, "latency": result.latency})
            self._save()
            return result

    def broadcast(self, method: str, params: Dict[str, Any], channel_filter: Optional[List[str]] = None, require_all: bool = False) -> Dict[str, MCPResponse]:
        """Broadcast a call to multiple channels. Returns channel -> response."""
        with self._lock:
            channels = channel_filter or list(self._channels.keys())
            results = {}
            for name in channels:
                if name not in self._channels: continue
                results[name] = self.call(name, method, params)
            if require_all and any(r.status != "success" for r in results.values()):
                # All must succeed
                return results
            return results

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._request_log)
            success = sum(1 for r in self._request_log if r.get("status") == "success")
            by_channel = {}
            for r in self._request_log:
                ch = r.get("channel", "unknown")
                if ch not in by_channel: by_channel[ch] = {"total": 0, "success": 0}
                by_channel[ch]["total"] += 1
                if r.get("status") == "success": by_channel[ch]["success"] += 1
            avg_latency = sum(r.get("latency", 0) for r in self._request_log) / total if total else 0
            return {"total_requests": total, "success": success, "error": total - success, "success_rate": round(success / total, 4) if total else 0.0, "avg_latency": round(avg_latency, 4), "by_channel": by_channel, "channels": len(self._channels)}

    def print_summary(self) -> str:
        stats = self.get_stats()
        lines = [
            "=== MCP Integration Summary ===",
            f"Channels: {stats['channels']}",
            f"Total Requests: {stats['total_requests']}",
            f"Success Rate: {stats['success_rate']:.2%}",
            f"Avg Latency: {stats['avg_latency']:.3f}s",
            "
--- Channel Health ---",
        ]
        for name, ch in self._channels.items():
            icon = "✅" if ch.health_status == "pass" else "⚠️" if ch.health_status == "warning" else "❌" if ch.health_status == "fail" else "❓"
            lines.append(f"  {icon} {name} ({ch.type}): {ch.health_status} — {ch.health_reason}")
        return "
".join(lines)

if __name__ == "__main__":
    mcp = MCPIntegrationNative()
    mcp.register_channel("github_api", "api", "https://api.github.com", "api_key", {"api_key": "ghp_xxx"})
    mcp.register_channel("web_search", "mcp", "http://localhost:8000/mcp", "none")
    mcp.register_channel("yt_dlp", "cli", "/usr/bin/yt-dlp", "none")
    mcp.health_check()
    print(mcp.print_summary())
