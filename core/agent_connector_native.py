#!/usr/bin/env python3
"""
Agent Connector for MAGNATRIX-OS
Pre-configured connectors for 9 external AI agents with health checks,
authentication, fallback chains, and circuit breaker protection.
Agents: Hermes, OpenClaw, Kimi Claw, AutoClaw, OpenCode, Codex,
Antigravity, Kimi Code, Claude Code.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import json
import time
import urllib.request
import urllib.error
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


class AgentStatus(enum.Enum):
    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class AuthType(enum.Enum):
    NONE = "none"
    API_KEY = "api_key"
    BEARER = "bearer"
    BASIC = "basic"
    X_API_KEY = "x_api_key"


@dataclasses.dataclass
class AgentConfig:
    """Configuration for a single external agent."""
    agent_id: str
    name: str
    description: str
    base_url: str
    endpoint: str
    auth_type: AuthType
    auth_value: str
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    weight: float = 1.0
    capabilities: List[str] = dataclasses.field(default_factory=list)
    headers: Dict[str, str] = dataclasses.field(default_factory=dict)
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class AgentHealth:
    agent_id: str
    status: AgentStatus
    latency_ms: float
    last_check: float
    consecutive_failures: int
    total_requests: int
    total_errors: int
    avg_latency_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "status": self.status.value,
            "latency_ms": self.latency_ms,
            "last_check": self.last_check,
            "consecutive_failures": self.consecutive_failures,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "avg_latency_ms": self.avg_latency_ms,
        }


@dataclasses.dataclass
class AgentResponse:
    agent_id: str
    text: str
    raw: Optional[str] = None
    latency_ms: float = 0.0
    status_code: int = 200
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "text": self.text[:200] + "..." if len(self.text) > 200 else self.text,
            "latency_ms": self.latency_ms,
            "status_code": self.status_code,
            "error": self.error,
        }


class AgentConnector:
    """Connects MAGNATRIX-OS to 9 external AI agents with health monitoring."""

    # ------------------------------------------------------------------
    # Pre-configured agent definitions
    # ------------------------------------------------------------------
    AGENT_DEFS: Dict[str, Dict[str, Any]] = {
        "hermes": {
            "name": "Hermes",
            "description": "General-purpose conversational AI agent. Strong at reasoning, explanations, and multi-turn dialogue.",
            "base_url": "http://localhost:11434",
            "endpoint": "/api/generate",
            "auth_type": "none",
            "capabilities": ["reasoning", "conversation", "analysis", "general"],
        },
        "openclaw": {
            "name": "OpenClaw",
            "description": "Open-source code analysis and review agent. Specialized in code review, refactoring suggestions, and architecture critique.",
            "base_url": "http://localhost:8000",
            "endpoint": "/v1/chat/completions",
            "auth_type": "api_key",
            "capabilities": ["code_review", "refactoring", "architecture", "debugging"],
        },
        "kimi_claw": {
            "name": "Kimi Claw",
            "description": "Kimi AI agent with extended context handling. Specialized in long-document processing, summarization, and cross-reference analysis.",
            "base_url": "https://api.moonshot.cn",
            "endpoint": "/v1/chat/completions",
            "auth_type": "bearer",
            "capabilities": ["long_context", "summarization", "cross_reference", "document_analysis"],
        },
        "autoclaw": {
            "name": "AutoClaw",
            "description": "Autonomous task execution agent. Specialized in workflow automation, task planning, and tool orchestration.",
            "base_url": "http://localhost:8001",
            "endpoint": "/execute",
            "auth_type": "api_key",
            "capabilities": ["automation", "workflow", "planning", "tool_use"],
        },
        "opencode": {
            "name": "OpenCode",
            "description": "Open-source coding assistant with multi-language support. Specialized in code generation, testing, and documentation.",
            "base_url": "http://localhost:8002",
            "endpoint": "/v1/code",
            "auth_type": "none",
            "capabilities": ["code_generation", "testing", "documentation", "multi_language"],
        },
        "codex": {
            "name": "Codex",
            "description": "OpenAI Codex code generation agent. Specialized in complex algorithm design, system architecture, and API design.",
            "base_url": "https://api.openai.com",
            "endpoint": "/v1/chat/completions",
            "auth_type": "bearer",
            "capabilities": ["algorithm", "system_design", "api_design", "advanced_coding"],
        },
        "antigravity": {
            "name": "Antigravity",
            "description": "Unrestricted research and analysis agent. Specialized in deep research, adversarial analysis, and out-of-the-box thinking.",
            "base_url": "http://localhost:8003",
            "endpoint": "/analyze",
            "auth_type": "x_api_key",
            "capabilities": ["research", "adversarial_analysis", "creative_thinking", "unrestricted"],
        },
        "kimi_code": {
            "name": "Kimi Code",
            "description": "Kimi AI code-focused agent. Specialized in Chinese-language code context, Asian tech stack, and local framework support.",
            "base_url": "https://api.moonshot.cn",
            "endpoint": "/v1/code",
            "auth_type": "bearer",
            "capabilities": ["chinese_code", "local_stack", "framework_support", "regional_tech"],
        },
        "claude_code": {
            "name": "Claude Code",
            "description": "Anthropic Claude coding agent. Specialized in safety-conscious code, secure patterns, and ethical AI implementation.",
            "base_url": "https://api.anthropic.com",
            "endpoint": "/v1/messages",
            "auth_type": "x_api_key",
            "capabilities": ["secure_coding", "ethical_ai", "safety_patterns", "code_review"],
        },
    }

    def __init__(self, api_keys: Optional[Dict[str, str]] = None) -> None:
        self._configs: Dict[str, AgentConfig] = {}
        self._health: Dict[str, AgentHealth] = {}
        self._api_keys: Dict[str, str] = api_keys or {}
        self._circuit_breakers: Dict[str, Dict[str, Any]] = {}
        self._default_timeout = 30.0
        self._max_retries = 3
        self._init_agents()

    def _init_agents(self) -> None:
        """Initialize all 9 pre-configured agents."""
        for agent_id, defs in self.AGENT_DEFS.items():
            auth_type = AuthType(defs["auth_type"])
            auth_value = self._api_keys.get(agent_id, "")
            cfg = AgentConfig(
                agent_id=agent_id,
                name=defs["name"],
                description=defs["description"],
                base_url=defs["base_url"],
                endpoint=defs["endpoint"],
                auth_type=auth_type,
                auth_value=auth_value,
                capabilities=defs["capabilities"],
            )
            self._configs[agent_id] = cfg
            self._health[agent_id] = AgentHealth(
                agent_id=agent_id,
                status=AgentStatus.UNKNOWN,
                latency_ms=0.0,
                last_check=0.0,
                consecutive_failures=0,
                total_requests=0,
                total_errors=0,
                avg_latency_ms=0.0,
            )
            self._circuit_breakers[agent_id] = {
                "failures": 0,
                "threshold": 5,
                "open": False,
                "last_failure": 0.0,
                "cooldown": 30.0,
            }

    def set_api_key(self, agent_id: str, key: str) -> None:
        if agent_id in self._configs:
            self._configs[agent_id].auth_value = key

    def set_base_url(self, agent_id: str, url: str) -> None:
        if agent_id in self._configs:
            self._configs[agent_id].base_url = url

    def _build_headers(self, cfg: AgentConfig) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        headers.update(cfg.headers)
        if cfg.auth_type == AuthType.API_KEY:
            headers["Authorization"] = f"Api-Key {cfg.auth_value}"
        elif cfg.auth_type == AuthType.BEARER:
            headers["Authorization"] = f"Bearer {cfg.auth_value}"
        elif cfg.auth_type == AuthType.X_API_KEY:
            headers["x-api-key"] = cfg.auth_value
        elif cfg.auth_type == AuthType.BASIC:
            import base64
            headers["Authorization"] = f"Basic {base64.b64encode(cfg.auth_value.encode()).decode()}"
        return headers

    def _build_request_body(self, cfg: AgentConfig, prompt: str) -> Dict[str, Any]:
        if "openai" in cfg.base_url or "anthropic" in cfg.base_url or "moonshot" in cfg.base_url:
            return {
                "model": cfg.metadata.get("model", "default"),
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2048,
                "temperature": 0.7,
            }
        elif "ollama" in cfg.base_url or ":11434" in cfg.base_url:
            return {
                "model": cfg.metadata.get("model", "llama3"),
                "prompt": prompt,
                "stream": False,
            }
        else:
            return {"prompt": prompt, "context": cfg.metadata}

    def _circuit_check(self, agent_id: str) -> bool:
        cb = self._circuit_breakers[agent_id]
        if cb["open"]:
            if time.time() - cb["last_failure"] > cb["cooldown"]:
                cb["open"] = False
                cb["failures"] = 0
                return True
            return False
        return True

    def _circuit_record(self, agent_id: str, success: bool) -> None:
        cb = self._circuit_breakers[agent_id]
        if success:
            cb["failures"] = max(0, cb["failures"] - 1)
        else:
            cb["failures"] += 1
            cb["last_failure"] = time.time()
            if cb["failures"] >= cb["threshold"]:
                cb["open"] = True

    def health_check(self, agent_id: str) -> AgentHealth:
        cfg = self._configs.get(agent_id)
        health = self._health[agent_id]
        if not cfg:
            health.status = AgentStatus.UNKNOWN
            return health
        start = time.time()
        try:
            url = cfg.base_url + "/health" if not cfg.endpoint.endswith("health") else cfg.base_url + cfg.endpoint
            req = urllib.request.Request(url, headers=self._build_headers(cfg), method="GET")
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                resp.read()
            health.status = AgentStatus.ONLINE
            health.latency_ms = (time.time() - start) * 1000
            health.last_check = time.time()
            health.consecutive_failures = 0
        except Exception as e:
            health.status = AgentStatus.OFFLINE
            health.latency_ms = (time.time() - start) * 1000
            health.last_check = time.time()
            health.consecutive_failures += 1
        return health

    def health_check_all(self) -> Dict[str, AgentHealth]:
        return {aid: self.health_check(aid) for aid in self._configs}

    def send(self, agent_id: str, prompt: str, timeout: Optional[float] = None) -> AgentResponse:
        cfg = self._configs.get(agent_id)
        if not cfg:
            return AgentResponse(agent_id, "", error="Agent not configured")
        health = self._health[agent_id]
        # Circuit breaker check
        if not self._circuit_check(agent_id):
            return AgentResponse(agent_id, "", error="Circuit breaker open", status_code=503)
        start = time.time()
        url = cfg.base_url.rstrip("/") + cfg.endpoint
        headers = self._build_headers(cfg)
        body = json.dumps(self._build_request_body(cfg, prompt)).encode("utf-8")
        last_error = None
        for attempt in range(self._max_retries):
            try:
                req = urllib.request.Request(url, data=body, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=timeout or cfg.timeout) as resp:
                    raw = resp.read().decode("utf-8")
                data = json.loads(raw)
                # Extract text from various response formats
                text = self._extract_text(data, agent_id)
                latency = (time.time() - start) * 1000
                health.total_requests += 1
                health.avg_latency_ms = (health.avg_latency_ms * (health.total_requests - 1) + latency) / health.total_requests
                self._circuit_record(agent_id, True)
                return AgentResponse(agent_id, text, raw, latency, resp.getcode())
            except urllib.error.HTTPError as e:
                last_error = e
                health.total_errors += 1
                if e.code >= 500 and attempt < self._max_retries - 1:
                    time.sleep(cfg.retry_delay * (2 ** attempt))
                    continue
                self._circuit_record(agent_id, False)
                return AgentResponse(agent_id, "", error=str(e), status_code=e.code)
            except Exception as e:
                last_error = e
                health.total_errors += 1
                if attempt < self._max_retries - 1:
                    time.sleep(cfg.retry_delay * (2 ** attempt))
                    continue
                self._circuit_record(agent_id, False)
                return AgentResponse(agent_id, "", error=str(e), status_code=0)
        return AgentResponse(agent_id, "", error=str(last_error), status_code=0)

    def _extract_text(self, data: Dict[str, Any], agent_id: str) -> str:
        if "choices" in data:
            return data["choices"][0].get("message", {}).get("content", "")
        elif "content" in data:
            return "".join(c.get("text", "") for c in data["content"] if c.get("type") == "text")
        elif "response" in data:
            return data["response"]
        elif "result" in data:
            return str(data["result"])
        elif "text" in data:
            return data["text"]
        return json.dumps(data)[:500]

    def send_all(self, prompt: str, filter_by: Optional[List[str]] = None) -> Dict[str, AgentResponse]:
        """Send to all configured agents or filtered subset."""
        agents = filter_by or list(self._configs.keys())
        results = {}
        for aid in agents:
            results[aid] = self.send(aid, prompt)
        return results

    def send_best(self, prompt: str, capability: Optional[str] = None) -> AgentResponse:
        """Send to the best available agent based on capability and health."""
        candidates = []
        for aid, cfg in self._configs.items():
            if capability and capability not in cfg.capabilities:
                continue
            health = self._health[aid]
            if health.status == AgentStatus.ONLINE and not self._circuit_breakers[aid]["open"]:
                candidates.append((aid, health.avg_latency_ms, cfg.weight))
        if not candidates:
            # Fallback: try any agent
            for aid in self._configs:
                if not self._circuit_breakers[aid]["open"]:
                    candidates.append((aid, 9999, 0))
        if not candidates:
            return AgentResponse("none", "", error="All agents offline or circuit breakers open")
        # Select by lowest latency * weight
        best = min(candidates, key=lambda x: x[1] / max(0.1, x[2]))
        return self.send(best[0], prompt)

    def get_capabilities(self, agent_id: str) -> List[str]:
        cfg = self._configs.get(agent_id)
        return cfg.capabilities if cfg else []

    def get_agent_by_capability(self, capability: str) -> List[str]:
        return [aid for aid, cfg in self._configs.items() if capability in cfg.capabilities]

    def get_all_agents(self) -> List[Dict[str, Any]]:
        return [{
            "agent_id": cfg.agent_id,
            "name": cfg.name,
            "description": cfg.description,
            "base_url": cfg.base_url,
            "capabilities": cfg.capabilities,
            "health": self._health[cfg.agent_id].to_dict(),
            "circuit_open": self._circuit_breakers[cfg.agent_id]["open"],
        } for cfg in self._configs.values()]

    def stats(self) -> Dict[str, Any]:
        by_status = {}
        for h in self._health.values():
            by_status[h.status.value] = by_status.get(h.status.value, 0) + 1
        total_reqs = sum(h.total_requests for h in self._health.values())
        total_errors = sum(h.total_errors for h in self._health.values())
        open_circuits = sum(1 for cb in self._circuit_breakers.values() if cb["open"])
        return {
            "agents": len(self._configs),
            "by_status": by_status,
            "total_requests": total_reqs,
            "total_errors": total_errors,
            "open_circuits": open_circuits,
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    conn = AgentConnector()
    print("=== Agent Connector Demo ===\n")
    print("Registered agents:")
    for agent in conn.get_all_agents():
        print(f"  {agent['name']} ({agent['agent_id']})")
        print(f"    Capabilities: {', '.join(agent['capabilities'])}")
    # Health check (all will be offline in demo)
    print(f"\nHealth check (demo env - no real endpoints):")
    health = conn.health_check_all()
    for aid, h in health.items():
        print(f"  {aid}: {h.status.value} ({h.latency_ms:.0f}ms)")
    # Capability search
    print(f"\nAgents with 'code_generation': {conn.get_agent_by_capability('code_generation')}")
    print(f"Agents with 'reasoning': {conn.get_agent_by_capability('reasoning')}")
    # Stats
    print(f"\nStats: {conn.stats()}")


if __name__ == "__main__":
    _demo()
