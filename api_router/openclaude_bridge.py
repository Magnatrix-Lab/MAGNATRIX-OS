#!/usr/bin/env python3
"""
OpenClaude Bridge — MAGNATRIX API Router Adapter
===================================================
Bridge to Gitlawb/openclaude: open-source coding-agent CLI and alternative
LLM router (27.4k stars). Provides OpenAI-compatible API routing across
multiple providers.

Keywords: LLM routing, OpenAI-compatible, provider profiles, tool loops,
          MCP integration, streaming, multi-model

Repo: https://github.com/Gitlawb/openclaude
"""
from __future__ import annotations

import os
import json
import asyncio
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, AsyncIterator
from pathlib import Path
from datetime import datetime

import aiohttp

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OPENCLAUDE_BIN = os.getenv("OPENCLAUDE_BIN", "openclaude")
OPENCLAUDE_PROFILE_DIR = Path(os.getenv("OPENCLAUDE_PROFILE_DIR", str(Path.home() / ".openclaude")))
DEFAULT_PROVIDER = os.getenv("OPENCLAUDE_PROVIDER", "openai")

# Provider env map
PROVIDER_ENV = {
    "openai": {"OPENAI_API_KEY": "OPENAI_API_KEY"},
    "openrouter": {"OPENAI_API_KEY": "OPENROUTER_API_KEY", "OPENAI_BASE_URL": "https://openrouter.ai/api/v1"},
    "deepseek": {"OPENAI_API_KEY": "DEEPSEEK_API_KEY", "OPENAI_BASE_URL": "https://api.deepseek.com/v1"},
    "gemini": {"GEMINI_API_KEY": "GEMINI_API_KEY"},
    "github": {"GITHUB_TOKEN": "GITHUB_TOKEN"},
    "ollama": {},
    "codex": {},
    "atomic-chat": {},
}

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class ProviderProfile:
    name: str
    provider: str  # openai | gemini | github | ollama | codex | ...
    model: str
    api_key_env: str = ""
    base_url: str = ""
    extra_env: Dict[str, str] = field(default_factory=dict)
    is_local: bool = False

@dataclass
class ToolCall:
    id: str
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[str] = None

@dataclass
class Message:
    role: str  # system | user | assistant | tool
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    model: str = ""
    latency_ms: float = 0.0

@dataclass
class RoutingDecision:
    provider: str
    model: str
    cost_estimate_usd: float = 0.0
    latency_estimate_ms: float = 0.0
    confidence: float = 1.0
    reason: str = ""

# ---------------------------------------------------------------------------
# Core Client
# ---------------------------------------------------------------------------

class OpenClaudeClient:
    """
    Interface to OpenClaude CLI for headless / scripted usage.
    Also provides direct HTTP routing for provider fallback.
    """

    def __init__(
        self,
        bin_path: str = OPENCLAUDE_BIN,
        profile_dir: Path = OPENCLAUDE_PROFILE_DIR,
    ):
        self.bin_path = bin_path
        self.profile_dir = profile_dir
        self._profiles: Dict[str, ProviderProfile] = {}
        self._session: Optional[aiohttp.ClientSession] = None

    async def _session_instance(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _exec(
        self,
        cmd: List[str],
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        cwd: Optional[Path] = None,
    ) -> str:
        merged_env = {**os.environ, **(env or {})}
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=merged_env,
            cwd=cwd,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError(f"openclaude timed out after {timeout}s")
        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace")[:600]
            raise RuntimeError(f"openclaude failed (rc={proc.returncode}): {err}")
        return stdout.decode("utf-8", errors="replace")

    # --- Provider Profiles ---

    def add_profile(self, profile: ProviderProfile) -> None:
        self._profiles[profile.name] = profile
        profile_path = self.profile_dir / f"{profile.name}.json"
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(
            json.dumps({
                "name": profile.name,
                "provider": profile.provider,
                "model": profile.model,
                "api_key_env": profile.api_key_env,
                "base_url": profile.base_url,
                "extra_env": profile.extra_env,
                "is_local": profile.is_local,
            }, indent=2),
            encoding="utf-8",
        )

    def load_profiles(self) -> None:
        if not self.profile_dir.exists():
            return
        for p in self.profile_dir.glob("*.json"):
            data = json.loads(p.read_text(encoding="utf-8"))
            self._profiles[data["name"]] = ProviderProfile(**data)

    def list_profiles(self) -> List[ProviderProfile]:
        return list(self._profiles.values())

    def get_profile(self, name: str) -> Optional[ProviderProfile]:
        return self._profiles.get(name)

    # --- Headless Execution ---

    async def run(
        self,
        prompt: str,
        profile: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 300.0,
    ) -> str:
        """
        Run a single headless prompt via OpenClaude CLI.
        """
        cmd = [self.bin_path, "--no-stream"]
        if profile:
            prof = self._profiles.get(profile)
            if prof:
                cmd.extend(["--model", prof.model])
        if model:
            cmd.extend(["--model", model])
        cmd.append(prompt)
        env = self._build_env(profile)
        return await self._exec(cmd, env=env, timeout=timeout)

    async def run_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        profile: Optional[str] = None,
        max_tool_loops: int = 10,
        timeout: float = 600.0,
    ) -> Dict[str, Any]:
        """
        Run prompt with explicit tool loop control.
        Returns structured result with tool call chain.
        """
        raw = await self.run(prompt, profile=profile, timeout=timeout)
        parsed_tools = self._extract_tool_calls(raw)
        return {
            "raw": raw,
            "tool_calls": parsed_tools,
            "tool_loop_count": len(parsed_tools),
            "model": self._profiles.get(profile or "", ProviderProfile("", "", "")).model,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _build_env(self, profile_name: Optional[str]) -> Dict[str, str]:
        env: Dict[str, str] = {}
        if not profile_name:
            return env
        prof = self._profiles.get(profile_name)
        if not prof:
            return env
        mapping = PROVIDER_ENV.get(prof.provider, {})
        for env_key, cfg_key in mapping.items():
            val = os.getenv(cfg_key, "")
            if val:
                env[env_key] = val
        if prof.base_url:
            env["OPENAI_BASE_URL"] = prof.base_url
        env.update(prof.extra_env)
        return env

    def _extract_tool_calls(self, raw: str) -> List[ToolCall]:
        """Naive parser for tool call markers in OpenClaude output."""
        calls: List[ToolCall] = []
        import re
        for match in re.finditer(r'🔧\s*Tool:\s*(\w+)\s*\(([^)]*)\)', raw):
            calls.append(ToolCall(
                id=f"tc-{len(calls)}",
                tool_name=match.group(1),
                arguments={"args": match.group(2)},
            ))
        return calls

    # --- Streaming (HTTP Router) ---

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        profile: str,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """
        Stream completions via OpenAI-compatible HTTP endpoint.
        Acts as the LLM routing layer.
        """
        prof = self._profiles.get(profile)
        if not prof:
            raise ValueError(f"Profile '{profile}' not found")

        base_url = prof.base_url or "https://api.openai.com/v1"
        api_key = os.getenv(prof.api_key_env, "")
        if not api_key and not prof.is_local:
            raise RuntimeError(f"API key env {prof.api_key_env} not set")

        payload = {
            "model": prof.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }

        session = await self._session_instance()
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        async with session.post(
            f"{base_url}/chat/completions",
            json=payload,
            headers=headers,
        ) as resp:
            async for line in resp.content:
                line = line.decode("utf-8").strip()
                if line.startswith("data: "):
                    chunk = line[6:]
                    if chunk == "[DONE]":
                        break
                    try:
                        data = json.loads(chunk)
                        delta = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if delta:
                            yield delta
                    except json.JSONDecodeError:
                        pass

    # --- Routing Logic ---

    async def route(
        self,
        prompt: str,
        candidates: Optional[List[str]] = None,
        strategy: str = "cost",  # cost | latency | quality | random
    ) -> RoutingDecision:
        """
        Select the best provider based on strategy.
        """
        candidates = candidates or list(self._profiles.keys())
        scored: List[RoutingDecision] = []
        for name in candidates:
            prof = self._profiles.get(name)
            if not prof:
                continue
            cost = 0.0
            latency = 0.0
            if prof.is_local:
                cost = 0.0
                latency = 50.0
            elif prof.provider in ("openai", "github"):
                cost = 0.005
                latency = 800.0
            elif prof.provider == "deepseek":
                cost = 0.001
                latency = 1200.0
            elif prof.provider == "gemini":
                cost = 0.002
                latency = 600.0
            else:
                cost = 0.003
                latency = 1000.0
            scored.append(RoutingDecision(
                provider=name,
                model=prof.model,
                cost_estimate_usd=cost,
                latency_estimate_ms=latency,
                reason=f"provider={prof.provider}, local={prof.is_local}",
            ))

        if strategy == "cost":
            scored.sort(key=lambda x: x.cost_estimate_usd)
        elif strategy == "latency":
            scored.sort(key=lambda x: x.latency_estimate_ms)
        elif strategy == "quality":
            scored.sort(key=lambda x: (x.latency_estimate_ms > 500, x.cost_estimate_usd))
        else:
            import random
            random.shuffle(scored)

        if scored:
            best = scored[0]
            best.confidence = 1.0 if len(scored) == 1 else 0.9
            return best
        return RoutingDecision(provider="none", model="none", reason="no candidates")

    # --- MCP Integration ---

    async def mcp_list_servers(self) -> List[str]:
        """List MCP server configs known to OpenClaude."""
        config_path = self.profile_dir / "mcp_config.json"
        if not config_path.exists():
            return []
        data = json.loads(config_path.read_text(encoding="utf-8"))
        return list(data.get("mcpServers", {}).keys())

    async def mcp_run_tool(
        self,
        server: str,
        tool: str,
        arguments: Dict[str, Any],
    ) -> str:
        """
        Execute an MCP tool via OpenClaude.
        """
        prompt = f"Run MCP tool '{tool}' on server '{server}' with args: {json.dumps(arguments)}"
        return await self.run(prompt, timeout=60.0)

    # --- Batch / Parallel ---

    async def batch_run(
        self,
        prompts: List[str],
        profile: Optional[str] = None,
        max_concurrency: int = 4,
    ) -> List[str]:
        """Run multiple prompts in parallel."""
        sem = asyncio.Semaphore(max_concurrency)

        async def _one(p: str) -> str:
            async with sem:
                return await self.run(p, profile=profile)

        return await asyncio.gather(*[_one(p) for p in prompts])

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

# ---------------------------------------------------------------------------
# High-Level Bridge
# ---------------------------------------------------------------------------

class OpenClaudeBridge:
    """
    MAGNATRIX adapter for OpenClaude.

    Provides:
    - Multi-provider LLM routing with cost/latency/quality strategies
    - OpenAI-compatible HTTP streaming
    - Tool loop execution with structured output
    - MCP server orchestration
    - Provider profile management
    - Batch parallel execution
    """

    def __init__(
        self,
        bin_path: str = OPENCLAUDE_BIN,
        profile_dir: Path = OPENCLAUDE_PROFILE_DIR,
    ):
        self.client = OpenClaudeClient(bin_path, profile_dir)
        self.client.load_profiles()

    async def __aenter__(self) -> OpenClaudeBridge:
        return self

    async def __aexit__(self, *_) -> None:
        await self.client.close()

    # ---- Provider Management ----

    def register_provider(
        self,
        name: str,
        provider: str,
        model: str,
        api_key_env: str = "",
        base_url: str = "",
        is_local: bool = False,
        extra_env: Optional[Dict[str, str]] = None,
    ) -> None:
        prof = ProviderProfile(
            name=name,
            provider=provider,
            model=model,
            api_key_env=api_key_env,
            base_url=base_url,
            is_local=is_local,
            extra_env=extra_env or {},
        )
        self.client.add_profile(prof)

    def providers(self) -> List[ProviderProfile]:
        return self.client.list_profiles()

    # ---- Chat / Completion ----

    async def chat(
        self,
        messages: List[Dict[str, str]],
        profile: Optional[str] = None,
        stream: bool = False,
    ) -> str | AsyncIterator[str]:
        """
        Send chat messages. If stream=True, returns async iterator.
        """
        if stream and profile:
            return self.client.stream_chat(messages, profile)
        prompt = messages[-1].get("content", "") if messages else ""
        return await self.client.run(prompt, profile=profile)

    # ---- Routing ----

    async def smart_route(
        self,
        prompt: str,
        strategy: str = "cost",
    ) -> str:
        """
        Automatically pick provider and run prompt.
        Returns the generated text.
        """
        decision = await self.client.route(prompt, strategy=strategy)
        print(f"[ROUTE] {decision.provider}/{decision.model} ({decision.reason})")
        return await self.client.run(prompt, profile=decision.provider)

    # ---- Tool Execution ----

    async def execute_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        profile: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self.client.run_with_tools(prompt, tools, profile=profile)

    # ---- Batch ----

    async def batch(
        self,
        prompts: List[str],
        profile: Optional[str] = None,
        max_concurrency: int = 4,
    ) -> List[str]:
        return await self.client.batch_run(prompts, profile=profile, max_concurrency=max_concurrency)

    # ---- MCP ----

    async def mcp_servers(self) -> List[str]:
        return await self.client.mcp_list_servers()

    async def mcp_tool(
        self,
        server: str,
        tool: str,
        arguments: Dict[str, Any],
    ) -> str:
        return await self.client.mcp_run_tool(server, tool, arguments)

# ---------------------------------------------------------------------------
# Demo Block
# ---------------------------------------------------------------------------

async def demo() -> None:
    """
    Demo: register providers, route a prompt, stream a chat,
    run batch, and execute with tools.
    """
    bridge = OpenClaudeBridge()

    # 1. Register providers
    bridge.register_provider(
        name="openai-gpt4o",
        provider="openai",
        model="gpt-4o",
        api_key_env="OPENAI_API_KEY",
    )
    bridge.register_provider(
        name="deepseek-chat",
        provider="deepseek",
        model="deepseek-chat",
        api_key_env="DEEPSEEK_API_KEY",
        base_url="https://api.deepseek.com/v1",
    )
    bridge.register_provider(
        name="ollama-local",
        provider="ollama",
        model="llama3.1:8b",
        is_local=True,
    )
    print(f"[DEMO] Registered providers: {[p.name for p in bridge.providers()]}")

    # 2. Smart routing (cost strategy)
    result = await bridge.smart_route(
        "Write a Python function that computes Fibonacci with memoization.",
        strategy="cost",
    )
    print(f"[DEMO] Routed result preview:
{result[:300]}...
")

    # 3. Batch execution
    prompts = [
        "Explain quantum computing in one sentence.",
        "Explain blockchain in one sentence.",
        "Explain neural networks in one sentence.",
    ]
    batch_results = await bridge.batch(prompts, profile="deepseek-chat", max_concurrency=3)
    print(f"[DEMO] Batch completed: {len(batch_results)} results")
    for i, r in enumerate(batch_results):
        print(f"  [{i+1}] {r[:80]}...")

    # 4. Tool execution
    tools = [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file from disk",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        },
    ]
    tool_result = await bridge.execute_with_tools(
        "Read the file 'config.yaml' and summarize its contents.",
        tools=tools,
        profile="openai-gpt4o",
    )
    print(f"[DEMO] Tool loops: {tool_result['tool_loop_count']}")

    # 5. MCP server list
    servers = await bridge.mcp_servers()
    print(f"[DEMO] MCP servers: {servers}")

    await bridge.client.close()
    print("[DEMO] Bridge closed.")

if __name__ == "__main__":
    print("=" * 60)
    print("OpenClaude Bridge Demo — MAGNATRIX API Router Adapter")
    print("=" * 60)
    print("
Requirements:")
    print("  - OpenClaude CLI installed: npm install -g openclaude")
    print("  - Set provider API keys (OPENAI_API_KEY, DEEPSEEK_API_KEY, etc.)")
    print("
Uncomment asyncio.run(demo()) to run.
")
    # asyncio.run(demo())