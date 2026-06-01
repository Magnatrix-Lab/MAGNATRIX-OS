# protocol/agent_connect_native.py
# AMATI-PELAJARI-TIRU: Pattern extracted from openagentinternet/open-agent-connect
# https://github.com/openagentinternet/open-agent-connect
# Agentic OS Architecture — AGENTS.md universal standard, CLAUDE.md, skillpacks, MCP
# Layer protocol of MAGNATRIX-OS

"""
Native Agent Connect Engine
===========================
Universal agent coordination protocol inspired by open-agent-connect:
  - AGENTS.md: Cross-tool standard for repository-level agent context (60,000+ repos)
  - CLAUDE.md: Claude Code-specific master instruction set
  - Skillpack System: Hierarchical skill definitions with YAML frontmatter
  - MCP (Model Context Protocol): Server/client for tool access
  - Cross-Tool Compatibility: Adapter pattern between different AI tools

Features:
  - Pure-Python AGENTS.md parser and generator
  - Skillpack loader with dependency resolution
  - MCP server/client simulation
  - Agent query routing with confidence scoring
  - Cross-tool compatibility layer
"""

from __future__ import annotations

import os
import re
import json
import yaml
import hashlib
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime


class ToolType(Enum):
    CLAUDE = auto()
    CODEX = auto()
    COPILOT = auto()
    CURSOR = auto()
    GEMINI = auto()
    KIMI = auto()
    WINDSURF = auto()


class AgentCapability(Enum):
    READ = auto()
    WRITE = auto()
    EXECUTE = auto()
    SEARCH = auto()
    ANALYZE = auto()
    DEPLOY = auto()
    TEST = auto()
    REVIEW = auto()


@dataclass
class AgentIdentity:
    name: str
    description: str
    model: str = "default"
    color: str = "#000000"
    memory_mode: str = "project"
    capabilities: List[AgentCapability] = field(default_factory=list)
    allowed_tools: List[str] = field(default_factory=list)
    max_steps: int = 10
    retry_budget: int = 3


@dataclass
class SkillDefinition:
    name: str
    description: str
    triggers: List[str] = field(default_factory=list)
    context: str = "when"
    agent: str = ""
    is_meta: bool = False
    instructions: str = ""
    scripts: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    assets: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


@dataclass
class MCPTool:
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[Any] = None


class AGENTSParser:
    """Parser for AGENTS.md universal standard."""

    def __init__(self, content: str = ""):
        self.content = content
        self.sections: Dict[str, str] = {}
        self.metadata: Dict[str, Any] = {}

    def parse(self) -> Dict[str, Any]:
        if self.content.startswith("---"):
            parts = self.content.split("---", 2)
            if len(parts) >= 3:
                try:
                    self.metadata = yaml.safe_load(parts[1]) or {}
                except Exception:
                    pass
                self.content = parts[2]
        current_section = "_intro"
        self.sections[current_section] = ""
        for line in self.content.split("\n"):
            if line.startswith("## "):
                current_section = line[3:].strip().lower().replace(" ", "_")
                self.sections[current_section] = ""
            else:
                self.sections[current_section] = self.sections.get(current_section, "") + line + "\n"
        return {"metadata": self.metadata, "sections": self.sections}

    def get_project_overview(self) -> str:
        return self.sections.get("project_overview", self.sections.get("_intro", "")).strip()

    def get_architecture(self) -> str:
        return self.sections.get("architecture", "").strip()

    def get_build_commands(self) -> Dict[str, str]:
        build_section = self.sections.get("build_&_test", self.sections.get("build_and_test", ""))
        commands = {}
        for line in build_section.split("\n"):
            if line.strip().startswith("-") and ":" in line:
                parts = line.strip()[1:].split(":", 1)
                if len(parts) == 2:
                    commands[parts[0].strip()] = parts[1].strip()
        return commands

    def get_conventions(self) -> List[str]:
        conv_section = self.sections.get("code_conventions", self.sections.get("conventions", ""))
        return [line.strip()[1:].strip() for line in conv_section.split("\n") if line.strip().startswith("-")]

    def get_guardrails(self) -> List[str]:
        guard_section = self.sections.get("guardrails", self.sections.get("forbidden_patterns", ""))
        return [line.strip()[1:].strip() for line in guard_section.split("\n") if line.strip().startswith("-")]

    @classmethod
    def from_file(cls, path: str) -> "AGENTSParser":
        with open(path, "r", encoding="utf-8") as f:
            return cls(f.read())


class CLAUDEMDParser:
    """Parser for CLAUDE.md Claude Code specific instructions."""

    def __init__(self, content: str = ""):
        self.content = content
        self.sections: Dict[str, str] = {}

    def parse(self) -> Dict[str, Any]:
        current_section = "_intro"
        self.sections[current_section] = ""
        for line in self.content.split("\n"):
            if line.startswith("## "):
                current_section = line[3:].strip().lower().replace(" ", "_")
                self.sections[current_section] = ""
            else:
                self.sections[current_section] = self.sections.get(current_section, "") + line + "\n"
        return {"sections": self.sections}

    def get_claude_specific(self) -> str:
        return self.sections.get("claude_code-specific", self.sections.get("claude_specific", "")).strip()

    def get_referenced_files(self) -> List[str]:
        refs = []
        for match in re.finditer(r"[\./\w\-]+\.(md|json|yaml|yml|py|js|ts)", self.content):
            refs.append(match.group(0))
        return list(set(refs))

    def get_subagents(self) -> List[Dict[str, str]]:
        subagents = []
        agent_section = self.sections.get("subagents", self.sections.get("agents", ""))
        for line in agent_section.split("\n"):
            if line.strip().startswith("-") and ":" in line:
                parts = line.strip()[1:].split(":", 1)
                subagents.append({"name": parts[0].strip(), "description": parts[1].strip()})
        return subagents


class SkillpackLoader:
    """Loader for skillpack definitions with hierarchical agents.json."""

    def __init__(self, base_path: str = ""):
        self.base_path = base_path
        self.skills: Dict[str, SkillDefinition] = {}
        self.agents: Dict[str, AgentIdentity] = {}
        self.dependencies: Dict[str, List[str]] = {}

    def load_skillpack(self, path: str) -> Dict[str, SkillDefinition]:
        skills = {}
        if not os.path.isdir(path):
            return skills
        for root, _, files in os.walk(path):
            for fname in files:
                if fname == "SKILL.md":
                    skill_path = os.path.join(root, fname)
                    skill = self._parse_skill_md(skill_path)
                    if skill:
                        skills[skill.name] = skill
                elif fname == ".agents.json":
                    json_path = os.path.join(root, fname)
                    self._parse_agents_json(json_path)
        self.skills.update(skills)
        return skills

    def _parse_skill_md(self, path: str) -> Optional[SkillDefinition]:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.startswith("---"):
            return None
        parts = content.split("---", 2)
        if len(parts) < 3:
            return None
        try:
            meta = yaml.safe_load(parts[1]) or {}
        except Exception:
            return None
        base_dir = os.path.dirname(path)
        scripts = self._list_files(os.path.join(base_dir, "scripts"))
        references = self._list_files(os.path.join(base_dir, "references"))
        assets = self._list_files(os.path.join(base_dir, "assets"))
        return SkillDefinition(
            name=meta.get("name", ""), description=meta.get("description", ""),
            triggers=meta.get("triggers", []), context=meta.get("context", "when"),
            agent=meta.get("agent", ""), is_meta=meta.get("isMeta", False),
            instructions=parts[2].strip(), scripts=scripts, references=references,
            assets=assets, dependencies=meta.get("dependencies", []),
        )

    def _parse_agents_json(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for agent_data in data.get("agents", []):
            agent = AgentIdentity(
                name=agent_data.get("name", ""), description=agent_data.get("description", ""),
                model=agent_data.get("model", "default"), color=agent_data.get("color", "#000000"),
                memory_mode=agent_data.get("memoryMode", "project"),
                capabilities=[AgentCapability[c.upper()] for c in agent_data.get("capabilities", []) if c.upper() in [e.name for e in AgentCapability]],
                allowed_tools=agent_data.get("allowedTools", []),
                max_steps=agent_data.get("maxSteps", 10),
                retry_budget=agent_data.get("retryBudget", 3),
            )
            self.agents[agent.name] = agent
        for skill_data in data.get("skills", []):
            skill = SkillDefinition(
                name=skill_data.get("name", ""), description=skill_data.get("description", ""),
                triggers=skill_data.get("triggers", []), context=skill_data.get("context", "when"),
                agent=skill_data.get("agent", ""), is_meta=skill_data.get("isMeta", False),
                dependencies=skill_data.get("dependencies", []),
            )
            self.skills[skill.name] = skill

    def _list_files(self, path: str) -> List[str]:
        if not os.path.isdir(path):
            return []
        return [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]

    def resolve_dependencies(self, skill_name: str) -> List[str]:
        """Topological sort of skill dependencies."""
        resolved = []
        visited = set()
        def visit(name: str) -> None:
            if name in visited:
                return
            visited.add(name)
            skill = self.skills.get(name)
            if skill:
                for dep in skill.dependencies:
                    visit(dep)
            resolved.append(name)
        visit(skill_name)
        return resolved

    def match_trigger(self, query: str) -> List[Tuple[SkillDefinition, float]]:
        """Match query against skill triggers."""
        query_lower = query.lower()
        matches = []
        for skill in self.skills.values():
            score = 0.0
            for trigger in skill.triggers:
                if trigger.lower() in query_lower:
                    score += 0.5
            if score > 0:
                matches.append((skill, score))
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches


class MCPServer:
    """MCP server exposing tools as capabilities."""

    def __init__(self, name: str = "mcp-server"):
        self.name = name
        self.tools: Dict[str, MCPTool] = {}

    def register_tool(self, tool: MCPTool) -> None:
        self.tools[tool.name] = tool

    def list_tools(self) -> List[Dict[str, Any]]:
        return [{"name": t.name, "description": t.description, "parameters": t.parameters} for t in self.tools.values()]

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        tool = self.tools.get(tool_name)
        if not tool:
            return {"error": f"Tool {tool_name} not found"}
        if tool.handler:
            try:
                result = tool.handler(**arguments)
                return {"result": result, "tool": tool_name}
            except Exception as e:
                return {"error": str(e), "tool": tool_name}
        return {"error": "No handler registered", "tool": tool_name}


class MCPClient:
    """MCP client connecting to external servers."""

    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}

    def connect(self, server_name: str, server: MCPServer) -> None:
        self.servers[server_name] = server

    def discover_tools(self, server_name: str) -> List[Dict[str, Any]]:
        server = self.servers.get(server_name)
        if server:
            return server.list_tools()
        return []

    def invoke(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        server = self.servers.get(server_name)
        if server:
            return server.call_tool(tool_name, arguments)
        return {"error": f"Server {server_name} not connected"}


class CrossToolAdapter:
    """Adapts AGENTS.md to tool-specific formats."""

    TOOL_PROMPTS = {
        ToolType.CLAUDE: "You are a helpful assistant working on the following project. Follow the conventions and guardrails specified.",
        ToolType.CODEX: "You are a coding assistant. Focus on the project structure and build commands provided.",
        ToolType.CURSOR: "You are a coding assistant. Review the project architecture and follow the conventions.",
        ToolType.GEMINI: "You are a helpful assistant. Use the project context and conventions provided.",
        ToolType.KIMI: "You are a helpful assistant. Follow the project conventions and guardrails.",
    }

    def adapt(self, parser: AGENTSParser, tool: ToolType) -> str:
        overview = parser.get_project_overview()
        architecture = parser.get_architecture()
        conventions = parser.get_conventions()
        guardrails = parser.get_guardrails()
        build = parser.get_build_commands()
        prompt = self.TOOL_PROMPTS.get(tool, "You are a helpful assistant.")
        lines = [prompt, f"\n# Project Overview\n{overview}", f"\n# Architecture\n{architecture}"]
        if conventions:
            lines.append(f"\n# Conventions\n" + "\n".join(f"- {c}" for c in conventions))
        if guardrails:
            lines.append(f"\n# Guardrails\n" + "\n".join(f"- {g}" for g in guardrails))
        if build:
            lines.append(f"\n# Build Commands\n" + "\n".join(f"- {k}: {v}" for k, v in build.items()))
        return "\n".join(lines)

    def generate_agents_md(self, project_name: str, overview: str, architecture: str, conventions: List[str], guardrails: List[str], build_commands: Dict[str, str]) -> str:
        lines = [
            f"---",
            f"project: {project_name}",
            f"agent: universal",
            f"---",
            f"",
            f"## Project Overview",
            f"{overview}",
            f"",
            f"## Architecture",
            f"{architecture}",
            f"",
            f"## Build & Test",
        ]
        for k, v in build_commands.items():
            lines.append(f"- {k}: {v}")
        lines.extend(["", "## Code Conventions"])
        for c in conventions:
            lines.append(f"- {c}")
        lines.extend(["", "## Guardrails"])
        for g in guardrails:
            lines.append(f"- {g}")
        return "\n".join(lines)


class AgentQueryRouter:
    """Routes queries between agents with confidence scoring."""

    def __init__(self):
        self.agents: Dict[str, AgentIdentity] = {}
        self.routes: List[Dict[str, Any]] = []

    def register_agent(self, agent: AgentIdentity) -> None:
        self.agents[agent.name] = agent

    def route(self, query: str, required_capabilities: List[AgentCapability] = None) -> List[Tuple[AgentIdentity, float]]:
        required = required_capabilities or []
        scored = []
        for agent in self.agents.values():
            score = 0.0
            for cap in required:
                if cap in agent.capabilities:
                    score += 0.3
            if any(cap in agent.capabilities for cap in [AgentCapability.READ, AgentCapability.ANALYZE]):
                score += 0.1
            if score > 0:
                scored.append((agent, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def execute_query(self, agent_name: str, query: str) -> Dict[str, Any]:
        agent = self.agents.get(agent_name)
        if not agent:
            return {"error": "Agent not found"}
        return {"agent": agent_name, "query": query, "capabilities_used": [c.name for c in agent.capabilities], "result": f"[MOCK] {agent.name} processed: {query[:50]}..."}


class AgentConnectEngine:
    """End-to-end agent connect orchestrator."""

    def __init__(self, project_path: str = "."):
        self.project_path = project_path
        self.agents_parser: Optional[AGENTSParser] = None
        self.claude_parser: Optional[CLAUDEMDParser] = None
        self.skillpack = SkillpackLoader(project_path)
        self.mcp_server = MCPServer("magnatrix-mcp")
        self.mcp_client = MCPClient()
        self.adapter = CrossToolAdapter()
        self.router = AgentQueryRouter()
        self._load_project_files()

    def _load_project_files(self) -> None:
        agents_path = os.path.join(self.project_path, "AGENTS.md")
        if os.path.exists(agents_path):
            self.agents_parser = AGENTSParser.from_file(agents_path)
            self.agents_parser.parse()
        claude_path = os.path.join(self.project_path, "CLAUDE.md")
        if os.path.exists(claude_path):
            self.claude_parser = CLAUDEMDParser.from_file(claude_path)
            self.claude_parser.parse()
        # Load skillpacks
        for root, dirs, _ in os.walk(self.project_path):
            if "skillpacks" in dirs:
                self.skillpack.load_skillpack(os.path.join(root, "skillpacks"))

    def get_context(self, tool: ToolType = ToolType.KIMI) -> str:
        if self.agents_parser:
            return self.adapter.adapt(self.agents_parser, tool)
        return "No AGENTS.md found."

    def generate_agents_md(self, project_name: str, overview: str, architecture: str, conventions: List[str], guardrails: List[str], build_commands: Dict[str, str]) -> str:
        return self.adapter.generate_agents_md(project_name, overview, architecture, conventions, guardrails, build_commands)

    def query(self, query: str, required_capabilities: List[AgentCapability] = None) -> Dict[str, Any]:
        routes = self.router.route(query, required_capabilities)
        if not routes:
            return {"error": "No suitable agent found"}
        best_agent = routes[0][0]
        return self.router.execute_query(best_agent.name, query)

    def discover_skills(self, query: str) -> List[Tuple[SkillDefinition, float]]:
        return self.skillpack.match_trigger(query)

    def execute_skill(self, skill_name: str, context: str = "") -> Dict[str, Any]:
        skill = self.skillpack.skills.get(skill_name)
        if not skill:
            return {"error": f"Skill {skill_name} not found"}
        deps = self.skillpack.resolve_dependencies(skill_name)
        return {
            "skill": skill_name, "description": skill.description,
            "dependencies": deps, "instructions": skill.instructions[:500],
            "scripts": skill.scripts, "references": skill.references,
        }

    def register_mcp_tool(self, name: str, description: str, parameters: Dict[str, Any], handler: Any) -> None:
        self.mcp_server.register_tool(MCPTool(name=name, description=description, parameters=parameters, handler=handler))

    def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self.mcp_server.call_tool(tool_name, arguments)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "agents_md_loaded": self.agents_parser is not None,
            "claude_md_loaded": self.claude_parser is not None,
            "skills": len(self.skillpack.skills),
            "agents": len(self.skillpack.agents),
            "mcp_tools": len(self.mcp_server.tools),
            "router_agents": len(self.router.agents),
        }


# --- Standalone test ---
if __name__ == "__main__":
    print("=== Agent Connect Engine ===")
    engine = AgentConnectEngine(".")

    # Generate AGENTS.md for MAGNATRIX
    agents_md = engine.generate_agents_md(
        project_name="MAGNATRIX-OS",
        overview="A private, uncensored, open-source AI operating system with 15+ layers and tri-language hybrid architecture.",
        architecture="15-layer architecture: Kernel (0), Protocol (1), API Router (1.5), Identity (2), Runtime (3), P2P Mesh (4), Knowledge (5), Skills (6), Browser (7), HFT Trading (8), Security (9), Uncensored AI (10), Governance (11), IDE (12), Offensive Security (13), Auto Repo Hunter (13.5)",
        conventions=["Use _native.py suffix for all native implementations", "Follow AMATI-PELAJARI-TIRU pattern", "Tri-language: Python orchestration, C++ hot paths, Rust crypto primitives"],
        guardrails=["No API keys in source code", "No external dependencies for core modules", "All modules must have standalone tests"],
        build_commands={"test": "python3 -m pytest tests/", "lint": "python3 -m py_compile", "commit": "git commit -m 'feat: ...'"},
    )
    print(f"AGENTS.md generated ({len(agents_md)} chars)")

    # Parse the generated AGENTS.md
    parser = AGENTSParser(agents_md)
    result = parser.parse()
    print(f"Parsed sections: {list(result['sections'].keys())}")
    print(f"Build commands: {parser.get_build_commands()}")
    print(f"Conventions: {parser.get_conventions()}")

    # Cross-tool adaptation
    for tool in [ToolType.CLAUDE, ToolType.KIMI, ToolType.CURSOR]:
        adapted = engine.adapter.adapt(parser, tool)
        print(f"\n{tool.name} adapter ({len(adapted)} chars): {adapted[:100]}...")

    # Register agents and route query
    engine.router.register_agent(AgentIdentity("researcher", "Research agent", capabilities=[AgentCapability.READ, AgentCapability.SEARCH, AgentCapability.ANALYZE]))
    engine.router.register_agent(AgentIdentity("coder", "Code generation agent", capabilities=[AgentCapability.WRITE, AgentCapability.EXECUTE, AgentCapability.TEST]))
    engine.router.register_agent(AgentIdentity("reviewer", "Code review agent", capabilities=[AgentCapability.READ, AgentCapability.REVIEW]))
    routes = engine.router.route("Implement a new feature", [AgentCapability.WRITE, AgentCapability.EXECUTE])
    print(f"\nRoute results: {[(r[0].name, r[1]) for r in routes]}")

    # MCP tools
    engine.register_mcp_tool("search_repo", "Search repository", {"query": "string"}, lambda query: f"Results for: {query}")
    engine.register_mcp_tool("run_test", "Run test suite", {"file": "string"}, lambda file: f"Tests passed for {file}")
    print(f"MCP call: {engine.call_mcp_tool('search_repo', {'query': 'native.py'})}")

    print(f"\nStats: {engine.get_stats()}")
