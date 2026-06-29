"""Agents ADK Builder - ADK agent construction with tools, orchestration, callbacks."""
from __future__ import annotations

import json
import time
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any


@dataclass
class ADKTool:
    tool_id: str
    name: str
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    def to_dict(self) -> Dict:
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "enabled": self.enabled,
        }


@dataclass
class ADKAgent:
    agent_id: str
    name: str
    model_id: str = "gemini-2.0-flash"
    tools: List[ADKTool] = field(default_factory=list)
    instructions: str = ""
    callbacks: List[str] = field(default_factory=list)
    state_schema: Dict[str, str] = field(default_factory=dict)
    orchestration_mode: str = "sequential"  # sequential, parallel, conditional

    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "model_id": self.model_id,
            "tools": [t.to_dict() for t in self.tools],
            "instructions": self.instructions,
            "callbacks": self.callbacks,
            "state_schema": self.state_schema,
            "orchestration_mode": self.orchestration_mode,
        }


@dataclass
class ADKState:
    state_id: str
    agent_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    updated_at: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "state_id": self.state_id,
            "agent_id": self.agent_id,
            "data": self.data,
            "version": self.version,
            "updated_at": self.updated_at,
        }


class AgentsADKBuilder:
    """ADK agent builder with tools, orchestration, callbacks, and state management."""

    SUPPORTED_MODELS = [
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-1.5-pro",
    ]

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "agents_adk"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.agents: Dict[str, ADKAgent] = {}
        self.tools: Dict[str, ADKTool] = {}
        self.states: Dict[str, ADKState] = {}
        self._init_default_tools()
        self._load_state()

    def _init_default_tools(self) -> None:
        defaults = [
            ADKTool("tool_search", "web_search", "Search the web for information", {"query": "string"}),
            ADKTool("tool_calc", "calculator", "Perform mathematical calculations", {"expression": "string"}),
            ADKTool("tool_read", "file_reader", "Read file contents", {"path": "string"}),
            ADKTool("tool_write", "file_writer", "Write content to file", {"path": "string", "content": "string"}),
            ADKTool("tool_http", "http_request", "Make HTTP requests", {"url": "string", "method": "string"}),
        ]
        for t in defaults:
            self.tools[t.tool_id] = t

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for a in data.get("agents", []):
                    tools = [ADKTool(**t) for t in a.pop("tools", [])]
                    self.agents[a["agent_id"]] = ADKAgent(tools=tools, **a)
                for t in data.get("tools", []):
                    self.tools[t["tool_id"]] = ADKTool(**t)
                for s in data.get("states", []):
                    self.states[s["state_id"]] = ADKState(**s)
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {
            "agents": [a.to_dict() for a in self.agents.values()],
            "tools": [t.to_dict() for t in self.tools.values()],
            "states": [s.to_dict() for s in self.states.values()],
        }
        state_file.write_text(json.dumps(state, indent=2))

    def create_agent(self, name: str, model_id: str = "gemini-2.0-flash", instructions: str = "") -> ADKAgent:
        """Create a new ADK agent."""
        if model_id not in self.SUPPORTED_MODELS:
            raise ValueError(f"Model {model_id} not supported. Choose from {self.SUPPORTED_MODELS}")
        agent_id = f"adk_agent_{name}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:6]}"
        agent = ADKAgent(
            agent_id=agent_id,
            name=name,
            model_id=model_id,
            instructions=instructions,
        )
        self.agents[agent_id] = agent
        self._save_state()
        return agent

    def add_tool(self, agent_id: str, tool_id: str) -> ADKAgent:
        """Add a tool to an agent."""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
        if tool_id not in self.tools:
            raise ValueError(f"Tool {tool_id} not found")
        agent = self.agents[agent_id]
        tool = self.tools[tool_id]
        if tool not in agent.tools:
            agent.tools.append(tool)
        self._save_state()
        return agent

    def create_tool(self, name: str, description: str, parameters: Dict[str, Any]) -> ADKTool:
        """Create a custom tool."""
        tool_id = f"tool_{name}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:4]}"
        tool = ADKTool(tool_id=tool_id, name=name, description=description, parameters=parameters)
        self.tools[tool_id] = tool
        self._save_state()
        return tool

    def set_callback(self, agent_id: str, callback_name: str) -> ADKAgent:
        """Register a callback for an agent."""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
        agent = self.agents[agent_id]
        if callback_name not in agent.callbacks:
            agent.callbacks.append(callback_name)
        self._save_state()
        return agent

    def set_orchestration(self, agent_id: str, mode: str) -> ADKAgent:
        """Set agent orchestration mode."""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
        if mode not in ("sequential", "parallel", "conditional"):
            raise ValueError("Mode must be sequential, parallel, or conditional")
        agent = self.agents[agent_id]
        agent.orchestration_mode = mode
        self._save_state()
        return agent

    def define_state(self, agent_id: str, schema: Dict[str, str]) -> ADKAgent:
        """Define state schema for an agent."""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
        agent = self.agents[agent_id]
        agent.state_schema = schema
        self._save_state()
        return agent

    def save_state(self, agent_id: str, data: Dict[str, Any]) -> ADKState:
        """Save agent state."""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
        state_id = f"state_{agent_id}_{int(time.time())}"
        state = ADKState(state_id=state_id, agent_id=agent_id, data=data, version=1, updated_at=time.time())
        self.states[state_id] = state
        self._save_state()
        return state

    def load_state(self, state_id: str) -> Optional[ADKState]:
        return self.states.get(state_id)

    def generate_agent_code(self, agent_id: str) -> str:
        """Generate Python code for the agent."""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
        agent = self.agents[agent_id]
        tool_names = [t.name for t in agent.tools]
        code = f"""from google.adk import Agent, Tool
from google.adk.tools import {", ".join(tool_names) if tool_names else "pass"}

agent = Agent(
    name="{agent.name}",
    model="{agent.model_id}",
    tools=[{", ".join(f"Tool('{t.name}')" for t in agent.tools) if agent.tools else ""}],
    instructions="{agent.instructions}",
    orchestration_mode="{agent.orchestration_mode}",
)

# Callbacks: {agent.callbacks}
# State schema: {agent.state_schema}
"""
        return code

    def get_stats(self) -> Dict:
        return {
            "agents_total": len(self.agents),
            "tools_total": len(self.tools),
            "states_total": len(self.states),
            "models_supported": self.SUPPORTED_MODELS,
        }

    def to_dict(self) -> Dict:
        return {
            "agents": [a.to_dict() for a in self.agents.values()],
            "tools": [t.to_dict() for t in self.tools.values()],
            "states": [s.to_dict() for s in self.states.values()],
            "stats": self.get_stats(),
        }


__all__ = ["AgentsADKBuilder", "ADKAgent", "ADKTool", "ADKState"]
