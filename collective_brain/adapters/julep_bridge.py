#!/usr/bin/env python3
"""
Julep Bridge — MAGNATRIX Collective Brain Adapter
=================================================
Bridge to julep-ai/julep: serverless AI agent backend with persistent
memory, multi-step task execution, and tool orchestration.

Keywords: agent memory, multi-step workflows, stateful sessions, RAG

Repo: https://github.com/julep-ai/julep
Docs: https://docs.julep.ai
"""
from __future__ import annotations

import os
import json
import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TypeVar
from pathlib import Path
from datetime import datetime

import aiohttp

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

JULEP_API_KEY = os.getenv("JULEP_API_KEY", "")
JULEP_BASE_URL = os.getenv("JULEP_BASE_URL", "https://api.julep.ai/v1")

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class AgentConfig:
    name: str
    model: str = "gpt-4o"
    about: str = ""
    instructions: List[str] = field(default_factory=list)
    tools: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SessionConfig:
    agent_id: str
    user_id: Optional[str] = None
    situation: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TaskStep:
    step_type: str  # "evaluate", "tool_call", "wait_for_input", "loop", "if", "parallel"
    name: str
    params: Dict[str, Any] = field(default_factory=dict)
    next_steps: List[str] = field(default_factory=list)

@dataclass
class TaskDef:
    name: str
    description: str = ""
    steps: List[TaskStep] = field(default_factory=list)
    input_schema: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DocEntry:
    title: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

# ---------------------------------------------------------------------------
# Core Client
# ---------------------------------------------------------------------------

class JulepClient:
    """Async HTTP client for Julep REST API."""

    def __init__(self, api_key: str = JULEP_API_KEY, base_url: str = JULEP_BASE_URL):
        if not api_key:
            raise RuntimeError("JULEP_API_KEY required. Set env var or pass to constructor.")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._session: Optional[aiohttp.ClientSession] = None

    async def _request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
            )
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        async with self._session.request(method, url, json=payload) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    # --- Agents ---

    async def create_agent(self, config: AgentConfig) -> Dict[str, Any]:
        payload = {
            "name": config.name,
            "model": config.model,
            "about": config.about,
            "instructions": config.instructions,
            "tools": config.tools,
            "metadata": config.metadata,
        }
        return await self._request("POST", "/agents", payload)

    async def list_agents(self) -> List[Dict[str, Any]]:
        data = await self._request("GET", "/agents")
        return data.get("items", [])

    async def get_agent(self, agent_id: str) -> Dict[str, Any]:
        return await self._request("GET", f"/agents/{agent_id}")

    async def update_agent(self, agent_id: str, config: AgentConfig) -> Dict[str, Any]:
        payload = {
            "name": config.name,
            "model": config.model,
            "about": config.about,
            "instructions": config.instructions,
            "tools": config.tools,
            "metadata": config.metadata,
        }
        return await self._request("PUT", f"/agents/{agent_id}", payload)

    async def delete_agent(self, agent_id: str) -> Dict[str, Any]:
        return await self._request("DELETE", f"/agents/{agent_id}")

    # --- Sessions (Memory) ---

    async def create_session(self, config: SessionConfig) -> Dict[str, Any]:
        payload = {
            "agent_id": config.agent_id,
            "situation": config.situation,
            "metadata": config.metadata,
        }
        if config.user_id:
            payload["user_id"] = config.user_id
        return await self._request("POST", "/sessions", payload)

    async def chat(
        self,
        session_id: str,
        message: str,
        recall: bool = True,
    ) -> Dict[str, Any]:
        payload = {
            "messages": [{"role": "user", "content": message}],
            "recall": recall,
        }
        return await self._request("POST", f"/sessions/{session_id}/chat", payload)

    async def list_sessions(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        params = {"agent_id": agent_id} if agent_id else {}
        endpoint = "/sessions"
        if params:
            endpoint += f"?agent_id={agent_id}"
        data = await self._request("GET", endpoint)
        return data.get("items", [])

    # --- Tasks (Multi-step Workflows) ---

    def _task_to_yaml_dict(self, task: TaskDef) -> Dict[str, Any]:
        steps = []
        for s in task.steps:
            step = {"name": s.name, s.step_type: s.params}
            if s.next_steps:
                step["next"] = s.next_steps[0] if len(s.next_steps) == 1 else s.next_steps
            steps.append(step)
        return {
            "name": task.name,
            "description": task.description,
            "input_schema": task.input_schema,
            "main": steps,
            "metadata": task.metadata,
        }

    async def create_task(self, agent_id: str, task: TaskDef) -> Dict[str, Any]:
        payload = self._task_to_yaml_dict(task)
        return await self._request("POST", f"/agents/{agent_id}/tasks", payload)

    async def execute_task(
        self,
        task_id: str,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload = {"input": inputs or {}}
        return await self._request("POST", f"/tasks/{task_id}/executions", payload)

    async def get_execution(self, execution_id: str) -> Dict[str, Any]:
        return await self._request("GET", f"/executions/{execution_id}")

    async def list_executions(self, task_id: str) -> List[Dict[str, Any]]:
        data = await self._request("GET", f"/tasks/{task_id}/executions")
        return data.get("items", [])

    # --- Docs (RAG Memory) ---

    async def create_doc(
        self,
        owner_id: str,
        owner_type: str,  # "agent" | "user"
        doc: DocEntry,
    ) -> Dict[str, Any]:
        payload = {
            "title": doc.title,
            "content": doc.content,
            "metadata": doc.metadata,
        }
        endpoint = f"/{owner_type}s/{owner_id}/docs"
        return await self._request("POST", endpoint, payload)

    async def search_docs(
        self,
        owner_id: str,
        owner_type: str,
        query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        payload = {"text": query, "limit": limit}
        endpoint = f"/{owner_type}s/{owner_id}/docs/search"
        data = await self._request("POST", endpoint, payload)
        return data.get("items", [])

    # --- Tools ---

    async def create_tool(
        self,
        agent_id: str,
        name: str,
        description: str,
        params: Dict[str, Any],
        integration: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = {
            "name": name,
            "description": description,
            "parameters": params,
        }
        if integration:
            payload["integration"] = integration
        return await self._request("POST", f"/agents/{agent_id}/tools", payload)

# ---------------------------------------------------------------------------
# High-Level Bridge
# ---------------------------------------------------------------------------

class JulepBridge:
    """
    MAGNATRIX adapter for Julep.

    Provides:
    - Agent lifecycle (create / update / delete)
    - Stateful sessions with persistent memory
    - Multi-step task execution (declarative workflows)
    - Document store for RAG
    - Tool binding for external capabilities
    """

    def __init__(self, api_key: str = JULEP_API_KEY, base_url: str = JULEP_BASE_URL):
        self.client = JulepClient(api_key, base_url)
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._tasks: Dict[str, Dict[str, Any]] = {}

    async def __aenter__(self) -> JulepBridge:
        return self

    async def __aexit__(self, *_) -> None:
        await self.client.close()

    # ---- Agent Ops ----

    async def spawn_agent(
        self,
        name: str,
        model: str = "gpt-4o",
        instructions: Optional[List[str]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        about: str = "",
    ) -> str:
        """Create an agent and return its ID."""
        cfg = AgentConfig(
            name=name,
            model=model,
            about=about,
            instructions=instructions or [],
            tools=tools or [],
        )
        resp = await self.client.create_agent(cfg)
        agent_id = resp["id"]
        self._agents[agent_id] = resp
        return agent_id

    async def list_agents(self) -> List[Dict[str, Any]]:
        return await self.client.list_agents()

    async def kill_agent(self, agent_id: str) -> None:
        await self.client.delete_agent(agent_id)
        self._agents.pop(agent_id, None)

    # ---- Session / Memory Ops ----

    async def open_session(
        self,
        agent_id: str,
        situation: str = "",
        user_id: Optional[str] = None,
    ) -> str:
        """Open a stateful session. Returns session ID."""
        cfg = SessionConfig(agent_id=agent_id, situation=situation, user_id=user_id)
        resp = await self.client.create_session(cfg)
        sid = resp["id"]
        self._sessions[sid] = resp
        return sid

    async def talk(self, session_id: str, message: str, recall: bool = True) -> str:
        """Send a message to a session and return the agent's reply."""
        resp = await self.client.chat(session_id, message, recall=recall)
        messages = resp.get("messages", resp.get("response", {}).get("messages", []))
        for m in reversed(messages):
            if m.get("role") == "assistant":
                return m.get("content", "")
        return json.dumps(resp, indent=2)

    async def remember(
        self,
        owner_id: str,
        owner_type: str,
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a document in vector memory. Returns doc ID."""
        doc = DocEntry(title=title, content=content, metadata=metadata or {})
        resp = await self.client.create_doc(owner_id, owner_type, doc)
        return resp["id"]

    async def recall(
        self,
        owner_id: str,
        owner_type: str,
        query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search vector memory."""
        return await self.client.search_docs(owner_id, owner_type, query, limit)

    # ---- Task / Workflow Ops ----

    async def define_task(
        self,
        agent_id: str,
        name: str,
        steps: List[TaskStep],
        description: str = "",
        input_schema: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Define a multi-step workflow. Returns task ID."""
        td = TaskDef(
            name=name,
            description=description,
            steps=steps,
            input_schema=input_schema or {},
        )
        resp = await self.client.create_task(agent_id, td)
        tid = resp["id"]
        self._tasks[tid] = resp
        return tid

    async def run_task(
        self,
        task_id: str,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a defined task. Returns execution object."""
        return await self.client.execute_task(task_id, inputs)

    async def poll_execution(self, execution_id: str, interval: float = 1.0) -> Dict[str, Any]:
        """Poll until execution completes."""
        while True:
            exe = await self.client.get_execution(execution_id)
            status = exe.get("status", "queued")
            if status in ("succeeded", "failed", "cancelled"):
                return exe
            await asyncio.sleep(interval)

    # ---- Tool Binding ----

    async def bind_tool(
        self,
        agent_id: str,
        name: str,
        description: str,
        params: Dict[str, Any],
        integration: Optional[str] = None,
    ) -> str:
        """Register a tool on an agent. Returns tool ID."""
        resp = await self.client.create_tool(agent_id, name, description, params, integration)
        return resp["id"]

    # ---- Snapshot / Restore ----

    def snapshot(self, path: str | Path) -> None:
        """Dump internal state to JSON for persistence."""
        payload = {
            "agents": self._agents,
            "sessions": self._sessions,
            "tasks": self._tasks,
            "timestamp": datetime.utcnow().isoformat(),
        }
        Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def restore(self, path: str | Path) -> None:
        """Load internal state from JSON."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self._agents = data.get("agents", {})
        self._sessions = data.get("sessions", {})
        self._tasks = data.get("tasks", {})

# ---------------------------------------------------------------------------
# Utility Builders
# ---------------------------------------------------------------------------

def step_evaluate(name: str, expression: str, next_step: str = "") -> TaskStep:
    """Build an evaluate step (runs code or expression)."""
    params = {"expression": expression}
    return TaskStep(
        step_type="evaluate",
        name=name,
        params=params,
        next_steps=[next_step] if next_step else [],
    )

def step_tool(
    name: str,
    tool_name: str,
    arguments: Dict[str, Any],
    next_step: str = "",
) -> TaskStep:
    """Build a tool_call step."""
    params = {"tool": tool_name, "arguments": arguments}
    return TaskStep(
        step_type="tool_call",
        name=name,
        params=params,
        next_steps=[next_step] if next_step else [],
    )

def step_wait(name: str, prompt: str, next_step: str = "") -> TaskStep:
    """Build a wait_for_input step."""
    params = {"prompt": prompt}
    return TaskStep(
        step_type="wait_for_input",
        name=name,
        params=params,
        next_steps=[next_step] if next_step else [],
    )

def step_loop(
    name: str,
    condition: str,
    body: List[TaskStep],
    next_step: str = "",
) -> TaskStep:
    """Build a loop step."""
    params = {"condition": condition, "body": [s.__dict__ for s in body]}
    return TaskStep(
        step_type="loop",
        name=name,
        params=params,
        next_steps=[next_step] if next_step else [],
    )

def step_if(
    name: str,
    condition: str,
    then_steps: List[TaskStep],
    else_steps: Optional[List[TaskStep]] = None,
    next_step: str = "",
) -> TaskStep:
    """Build a conditional step."""
    params = {
        "condition": condition,
        "then": [s.__dict__ for s in then_steps],
    }
    if else_steps:
        params["else"] = [s.__dict__ for s in else_steps]
    return TaskStep(
        step_type="if",
        name=name,
        params=params,
        next_steps=[next_step] if next_step else [],
    )

def step_parallel(name: str, branches: List[List[TaskStep]], next_step: str = "") -> TaskStep:
    """Build a parallel execution step."""
    params = {"branches": [[s.__dict__ for s in branch] for branch in branches]}
    return TaskStep(
        step_type="parallel",
        name=name,
        params=params,
        next_steps=[next_step] if next_step else [],
    )

# ---------------------------------------------------------------------------
# Demo Block
# ---------------------------------------------------------------------------

async def demo() -> None:
    """Demo: create an agent with memory, chat in a session, run a multi-step task."""
    bridge = JulepBridge()

    agent_id = await bridge.spawn_agent(
        name="MAGNATRIX-Planner",
        model="gpt-4o",
        instructions=[
            "You are a strategic planning agent for MAGNATRIX.",
            "Always think step-by-step before acting.",
        ],
        about="Handles project planning and task decomposition.",
    )
    print(f"[DEMO] Agent created: {agent_id}")

    session_id = await bridge.open_session(
        agent_id=agent_id,
        situation="Planning a new microservice architecture.",
    )
    print(f"[DEMO] Session opened: {session_id}")

    reply1 = await bridge.talk(session_id, "List 3 services we need for a real-time analytics pipeline.")
    print(f"[DEMO] Agent reply:
{reply1}
")

    reply2 = await bridge.talk(session_id, "Add monitoring and alerting to each.")
    print(f"[DEMO] Agent reply (with memory):
{reply2}
")

    doc_id = await bridge.remember(
        owner_id=agent_id,
        owner_type="agent",
        title="MAGNATRIX Architecture Guidelines",
        content="""
        All MAGNATRIX services must:
        - Expose OpenAPI specs
        - Use async message queues for cross-service comms
        - Log structured JSON to centralized Loki
        - Run health checks on /healthz
        """,
    )
    print(f"[DEMO] Doc stored: {doc_id}")

    hits = await bridge.recall(agent_id, "agent", "What are the logging requirements?")
    print(f"[DEMO] Recall hits: {len(hits)}")
    for h in hits:
        print(f"  - {h.get('title')}: {h.get('content', '')[:120]}...")

    task_id = await bridge.define_task(
        agent_id=agent_id,
        name="onboard-service",
        description="Onboard a new microservice into MAGNATRIX.",
        steps=[
            step_evaluate("validate-name", "is_valid(input.service_name)", "generate-spec"),
            step_tool("generate-spec", "generate_openapi", {"service": "{{input.service_name}}"}, "create-repo"),
            step_tool("create-repo", "github_create_repo", {"name": "{{input.service_name}}"}, "notify-team"),
            step_tool("notify-team", "slack_post", {"channel": "#dev", "text": "New service {{input.service_name}} onboarded."}),
        ],
        input_schema={
            "type": "object",
            "properties": {"service_name": {"type": "string"}},
            "required": ["service_name"],
        },
    )
    print(f"[DEMO] Task defined: {task_id}")

    execution = await bridge.run_task(task_id, {"service_name": "magnatrix-ledger"})
    print(f"[DEMO] Execution started: {execution.get('id')}")

    result = await bridge.poll_execution(execution["id"], interval=2.0)
    print(f"[DEMO] Execution finished with status: {result.get('status')}")

    bridge.snapshot("julep_state.json")
    print("[DEMO] State snapshot saved to julep_state.json")

    await bridge.client.close()

if __name__ == "__main__":
    print("=" * 60)
    print("Julep Bridge Demo — MAGNATRIX Collective Brain Adapter")
    print("=" * 60)
    print("
Set JULEP_API_KEY env var before running.
")
    # asyncio.run(demo())  # Uncomment when API key is ready
