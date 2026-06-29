"""
copilot_agent_manager_native.py
MAGNATRIX-OS — Copilot Agent Manager

Inspired by awesome-copilot agents:
Create, manage, and run pre-built agent templates for AI development tasks.
Pure Python standard library.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class CopilotAgent:
    agent_id: str
    name: str
    description: str
    system_prompt: str
    capabilities: List[str] = field(default_factory=list)
    status: str = "inactive"
    created_at: str = ""
    last_run: str = ""
    run_count: int = 0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class CopilotAgentManager:
    """Manage pre-built agent templates for AI development tasks."""

    AGENT_TEMPLATES = {
        "code_reviewer": {
            "name": "Code Reviewer",
            "description": "Reviews code for quality, bugs, and best practices",
            "system_prompt": "You are an expert code reviewer. Analyze code for correctness, readability, performance, and security issues. Provide actionable feedback with specific line references.",
            "capabilities": ["review", "lint", "suggest"],
        },
        "test_generator": {
            "name": "Test Generator",
            "description": "Generates unit and integration tests automatically",
            "system_prompt": "You are a test automation expert. Generate comprehensive test cases covering happy paths, edge cases, and error conditions. Use pytest and unittest patterns.",
            "capabilities": ["test", "coverage", "mock"],
        },
        "doc_writer": {
            "name": "Documentation Writer",
            "description": "Writes and maintains documentation from code",
            "system_prompt": "You are a technical documentation expert. Write clear, concise docs with examples, parameter descriptions, and usage patterns. Follow Google and NumPy docstring styles.",
            "capabilities": ["docs", "docstrings", "examples"],
        },
        "security_auditor": {
            "name": "Security Auditor",
            "description": "Audits code for security vulnerabilities",
            "system_prompt": "You are a security auditor. Identify vulnerabilities, injection risks, insecure dependencies, and OWASP Top 10 issues. Suggest mitigations with CWE references.",
            "capabilities": ["audit", "scan", "cwe"],
        },
        "refactor_engineer": {
            "name": "Refactor Engineer",
            "description": "Suggests and applies code refactoring",
            "system_prompt": "You are a refactoring expert. Identify code smells, duplication, and complexity. Propose incremental refactors that preserve behavior while improving maintainability.",
            "capabilities": ["refactor", "smell", "complexity"],
        },
        "debug_assistant": {
            "name": "Debug Assistant",
            "description": "Helps debug errors and exceptions",
            "system_prompt": "You are a debugging expert. Analyze stack traces, error logs, and state dumps. Identify root causes and suggest step-by-step fixes with verification methods.",
            "capabilities": ["debug", "trace", "root_cause"],
        },
        "api_designer": {
            "name": "API Designer",
            "description": "Designs REST and GraphQL APIs",
            "system_prompt": "You are an API design expert. Create RESTful and GraphQL APIs following OpenAPI specs. Design endpoints, schemas, auth, rate limiting, and versioning strategies.",
            "capabilities": ["design", "openapi", "graphql"],
        },
        "devops_engineer": {
            "name": "DevOps Engineer",
            "description": "CI/CD, infrastructure, and deployment automation",
            "system_prompt": "You are a DevOps automation expert. Design CI/CD pipelines, Dockerfiles, Kubernetes manifests, and Terraform configs. Follow GitOps and immutable infrastructure patterns.",
            "capabilities": ["cicd", "docker", "k8s", "terraform"],
        },
    }

    def __init__(self, agents_dir: str = "./copilot_agents"):
        self.agents_dir = Path(agents_dir)
        self.agents_dir.mkdir(exist_ok=True)
        self.agents: Dict[str, CopilotAgent] = {}
        self._load()

    def _load(self) -> None:
        file = self.agents_dir / "agents.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for aid, ad in data.items():
                        self.agents[aid] = CopilotAgent(**ad)
            except Exception:
                pass

    def _save(self) -> None:
        file = self.agents_dir / "agents.json"
        with open(file, "w", encoding="utf-8") as f:
            json.dump({aid: asdict(a) for aid, a in self.agents.items()}, f, indent=2)

    def create_from_template(self, template_id: str, agent_id: str) -> Optional[CopilotAgent]:
        template = self.AGENT_TEMPLATES.get(template_id)
        if not template:
            return None
        agent = CopilotAgent(
            agent_id=agent_id, name=template["name"], description=template["description"],
            system_prompt=template["system_prompt"], capabilities=template.get("capabilities", []),
        )
        self.agents[agent_id] = agent
        self._save()
        return agent

    def create_custom(self, agent_id: str, name: str, description: str,
                      system_prompt: str, capabilities: Optional[List[str]] = None) -> CopilotAgent:
        agent = CopilotAgent(
            agent_id=agent_id, name=name, description=description,
            system_prompt=system_prompt, capabilities=capabilities or [],
        )
        self.agents[agent_id] = agent
        self._save()
        return agent

    def activate(self, agent_id: str) -> bool:
        if agent_id in self.agents:
            self.agents[agent_id].status = "active"
            self._save()
            return True
        return False

    def deactivate(self, agent_id: str) -> bool:
        if agent_id in self.agents:
            self.agents[agent_id].status = "inactive"
            self._save()
            return True
        return False

    def run_agent(self, agent_id: str) -> Dict[str, Any]:
        agent = self.agents.get(agent_id)
        if not agent:
            return {"error": "Agent not found"}
        agent.run_count += 1
        agent.last_run = datetime.now().isoformat()
        self._save()
        return {
            "agent_id": agent_id, "status": agent.status, "capabilities": agent.capabilities,
            "system_prompt_preview": agent.system_prompt[:200] + "...",
        }

    def get_agent(self, agent_id: str) -> Optional[CopilotAgent]:
        return self.agents.get(agent_id)

    def list_agents(self) -> List[CopilotAgent]:
        return list(self.agents.values())

    def list_active(self) -> List[CopilotAgent]:
        return [a for a in self.agents.values() if a.status == "active"]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.agents)
        active = sum(1 for a in self.agents.values() if a.status == "active")
        return {
            "total_agents": total, "active": active, "templates": len(self.AGENT_TEMPLATES),
            "total_runs": sum(a.run_count for a in self.agents.values()),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["CopilotAgentManager", "CopilotAgent"]