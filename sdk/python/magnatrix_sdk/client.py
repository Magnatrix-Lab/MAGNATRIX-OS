#!/usr/bin/env python3
"""
client.py — MAGNATRIX Python SDK Client
Unified interface untuk semua MAGNATRIX services.

Usage:
    from magnatrix_sdk import MAGNATRIXClient
    client = MAGNATRIXClient(base_url="http://localhost:8080")
    status = client.status()
    result = client.llm_chat(messages=[{"role": "user", "content": "Hello"}])
"""

import json
import os
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Any


class MAGNATRIXClient:
    """Unified client untuk MAGNATRIX API Gateway dan services."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        self.base_url = (base_url or os.environ.get("MAGNATRIX_API_URL", "http://localhost:8080")).rstrip("/")
        self.api_key = api_key or os.environ.get("MAGNATRIX_API_KEY", "")
        self.timeout = timeout

    def _request(self, method: str, endpoint: str, payload: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request ke MAGNATRIX API."""
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            if payload:
                data = json.dumps(payload).encode()
                req = urllib.request.Request(url, data=data, method=method, headers=headers)
            else:
                req = urllib.request.Request(url, method=method, headers=headers)

            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode()
                return json.loads(body) if body else {"status": "ok"}
        except urllib.error.HTTPError as e:
            try:
                err = json.loads(e.read().decode())
                return {"error": f"HTTP {e.code}", "detail": err}
            except:
                return {"error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # System
    # ------------------------------------------------------------------
    def status(self) -> Dict[str, Any]:
        """Get MAGNATRIX system status."""
        return self._request("GET", "/api/v2/status")

    def health(self) -> Dict[str, Any]:
        """Health check."""
        return self._request("GET", "/health")

    # ------------------------------------------------------------------
    # LLM / FreeLLM Router
    # ------------------------------------------------------------------
    def llm_chat(self, messages: List[Dict[str, str]], model: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Chat completions via FreeLLMRouter atau One-API."""
        payload = {
            "messages": messages,
            "model": model,
            **kwargs,
        }
        return self._request("POST", "/api/v2/llm/chat", payload)

    def llm_models(self) -> List[Dict[str, Any]]:
        """List available LLM models."""
        result = self._request("GET", "/api/v2/llm/models")
        return result.get("data", [])

    def llm_health(self) -> Dict[str, Any]:
        """LLM router health check."""
        return self._request("GET", "/api/v2/llm/health")

    # ------------------------------------------------------------------
    # Swarm / Agents
    # ------------------------------------------------------------------
    def swarm_nodes(self) -> List[Dict[str, Any]]:
        """List swarm nodes."""
        result = self._request("GET", "/api/v2/swarm/nodes")
        return result.get("nodes", [])

    def swarm_spawn(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Spawn new swarm node."""
        return self._request("POST", "/api/v2/swarm/spawn", config)

    def agent_status(self) -> Dict[str, Any]:
        """Get agent registry status."""
        return self._request("GET", "/api/v2/agents/status")

    # ------------------------------------------------------------------
    # Knowledge Graph
    # ------------------------------------------------------------------
    def knowledge_query(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Query knowledge graph."""
        return self._request("POST", "/api/v2/knowledge/query", {"query": query, "limit": limit})

    # ------------------------------------------------------------------
    # Trading
    # ------------------------------------------------------------------
    def trading_status(self) -> Dict[str, Any]:
        """Get trading engine status."""
        return self._request("GET", "/api/v2/trading/status")

    def trading_execute(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trading order."""
        return self._request("POST", "/api/v2/trading/execute", order)

    # ------------------------------------------------------------------
    # Governance
    # ------------------------------------------------------------------
    def constitution(self) -> Dict[str, Any]:
        """Get current constitution."""
        return self._request("GET", "/api/v2/governance/constitution")

    def goals(self) -> Dict[str, Any]:
        """Get active goals."""
        return self._request("GET", "/api/v2/governance/goals")

    # ------------------------------------------------------------------
    # Evolution
    # ------------------------------------------------------------------
    def evolve_trigger(self) -> Dict[str, Any]:
        """Trigger self-improvement cycle."""
        return self._request("POST", "/api/v2/evolve/trigger")

    # ------------------------------------------------------------------
    # Browser
    # ------------------------------------------------------------------
    def browser_capture(self, url: str, selector: Optional[str] = None) -> Dict[str, Any]:
        """Capture browser screenshot/data."""
        return self._request("POST", "/api/v2/browser/capture", {"url": url, "selector": selector})

    # ------------------------------------------------------------------
    # Chat Bridge
    # ------------------------------------------------------------------
    def chat_send(self, message: str, room: str = "default") -> Dict[str, Any]:
        """Send message via chat bridge."""
        return self._request("POST", "/api/v2/chat/send", {"message": message, "room": room})
