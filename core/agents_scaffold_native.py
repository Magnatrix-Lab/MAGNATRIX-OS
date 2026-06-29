"""Agents Scaffold - Project scaffolding for ADK agents."""
from __future__ import annotations

import json
import time
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ScaffoldTemplate:
    template_id: str
    name: str
    description: str = ""
    files: Dict[str, str] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    agent_type: str = " conversational"  # conversational, workflow, multi_tool

    def to_dict(self) -> Dict:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "files": self.files,
            "dependencies": self.dependencies,
            "agent_type": self.agent_type,
        }


@dataclass
class ScaffoldProject:
    project_id: str
    name: str
    template_id: str
    output_path: str = ""
    created_at: float = 0.0
    files_generated: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "template_id": self.template_id,
            "output_path": self.output_path,
            "created_at": self.created_at,
            "files_generated": self.files_generated,
        }


class AgentsScaffold:
    """Project scaffolding for Google ADK agents."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "agents_scaffold"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.templates: Dict[str, ScaffoldTemplate] = {}
        self.projects: Dict[str, ScaffoldProject] = {}
        self._init_default_templates()
        self._load_state()

    def _init_default_templates(self) -> None:
        templates = [
            ScaffoldTemplate(
                template_id="basic_conversational",
                name="Basic Conversational Agent",
                description="Single-turn conversational agent with Gemini",
                files={
                    "agent.py": "from google.adk import Agent\n\nagent = Agent(name=\"{name}\", model=\"gemini-2.0-flash\")\n",
                    "requirements.txt": "google-adk\ngoogle-generativeai\n",
                    "README.md": "# {name}\n\nBasic conversational agent built with ADK.\n",
                },
                dependencies=["google-adk", "google-generativeai"],
                agent_type="conversational",
            ),
            ScaffoldTemplate(
                template_id="multi_tool",
                name="Multi-Tool Agent",
                description="Agent with multiple tool integrations",
                files={
                    "agent.py": "from google.adk import Agent, Tool\n\ntools = [Tool(name=\"search\"), Tool(name=\"calculator\")]\nagent = Agent(name=\"{name}\", tools=tools)\n",
                    "tools/__init__.py": "",
                    "requirements.txt": "google-adk\nrequests\n",
                    "README.md": "# {name}\n\nMulti-tool ADK agent.\n",
                },
                dependencies=["google-adk", "requests"],
                agent_type="multi_tool",
            ),
            ScaffoldTemplate(
                template_id="workflow",
                name="Workflow Agent",
                description="Sequential workflow agent with state management",
                files={
                    "agent.py": "from google.adk import WorkflowAgent, State\n\nagent = WorkflowAgent(name=\"{name}\", steps=[])\n",
                    "states/default.yaml": "initial_state: {}\n",
                    "requirements.txt": "google-adk\npyyaml\n",
                    "README.md": "# {name}\n\nWorkflow ADK agent with state persistence.\n",
                },
                dependencies=["google-adk", "pyyaml"],
                agent_type="workflow",
            ),
            ScaffoldTemplate(
                template_id="enterprise",
                name="Enterprise Agent",
                description="Production-ready agent with observability and CI/CD",
                files={
                    "agent.py": "from google.adk import Agent\n\nagent = Agent(name=\"{name}\", model=\"gemini-2.0-flash\")\n",
                    "deploy/cloud_run.yaml": "service: {name}\n\n",
                    "deploy/Dockerfile": "FROM python:3.11-slim\nWORKDIR /app\nCOPY . .\nRUN pip install -r requirements.txt\nCMD [\"python\", \"agent.py\"]\n",
                    "tests/test_agent.py": "import unittest\n\nclass TestAgent(unittest.TestCase):\n    pass\n",
                    "requirements.txt": "google-adk\npytest\npytest-asyncio\n",
                    "README.md": "# {name}\n\nEnterprise ADK agent with deployment configs.\n",
                },
                dependencies=["google-adk", "pytest", "pytest-asyncio"],
                agent_type="enterprise",
            ),
        ]
        for t in templates:
            self.templates[t.template_id] = t

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for p in data.get("projects", []):
                    self.projects[p["project_id"]] = ScaffoldProject(**p)
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {
            "templates": [t.to_dict() for t in self.templates.values()],
            "projects": [p.to_dict() for p in self.projects.values()],
        }
        state_file.write_text(json.dumps(state, indent=2))

    def create_project(self, name: str, template_id: str = "basic_conversational") -> ScaffoldProject:
        """Create a new agent project from template."""
        if template_id not in self.templates:
            raise ValueError(f"Template {template_id} not found")
        template = self.templates[template_id]
        project_id = f"proj_{name}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:6]}"
        output_path = str(self.data_dir / "projects" / project_id)
        Path(output_path).mkdir(parents=True, exist_ok=True)

        files_generated = []
        for filename, content in template.files.items():
            file_path = Path(output_path) / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content.format(name=name))
            files_generated.append(filename)

        project = ScaffoldProject(
            project_id=project_id,
            name=name,
            template_id=template_id,
            output_path=output_path,
            created_at=time.time(),
            files_generated=files_generated,
        )
        self.projects[project_id] = project
        self._save_state()
        return project

    def enhance_project(self, project_id: str, feature: str) -> List[str]:
        """Enhance an existing project with a feature."""
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        project = self.projects[project_id]
        enhancements = []

        if feature == "tests":
            test_path = Path(project.output_path) / "tests" / "test_agent.py"
            test_path.parent.mkdir(parents=True, exist_ok=True)
            test_path.write_text("import unittest\n\nclass TestAgent(unittest.TestCase):\n    def test_basic(self):\n        self.assertTrue(True)\n")
            enhancements.append("tests/test_agent.py")
        elif feature == "deploy":
            deploy_path = Path(project.output_path) / "deploy" / "Dockerfile"
            deploy_path.parent.mkdir(parents=True, exist_ok=True)
            deploy_path.write_text("FROM python:3.11-slim\nWORKDIR /app\nCOPY . .\nRUN pip install -r requirements.txt\n")
            enhancements.append("deploy/Dockerfile")
        elif feature == "observability":
            obs_path = Path(project.output_path) / "observability.py"
            obs_path.write_text("# Cloud Trace and Logging integration\n")
            enhancements.append("observability.py")

        project.files_generated.extend(enhancements)
        self._save_state()
        return enhancements

    def upgrade_template(self, project_id: str, new_template_id: str) -> ScaffoldProject:
        """Upgrade project to new template version."""
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        if new_template_id not in self.templates:
            raise ValueError(f"Template {new_template_id} not found")

        project = self.projects[project_id]
        old_files = set(project.files_generated)
        new_template = self.templates[new_template_id]
        output_path = Path(project.output_path)

        new_files = []
        for filename, content in new_template.files.items():
            file_path = output_path / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content.format(name=project.name))
            new_files.append(filename)

        project.template_id = new_template_id
        project.files_generated = list(set(project.files_generated + new_files))
        self._save_state()
        return project

    def list_templates(self) -> List[Dict]:
        return [t.to_dict() for t in self.templates.values()]

    def get_project(self, project_id: str) -> Optional[ScaffoldProject]:
        return self.projects.get(project_id)

    def get_stats(self) -> Dict:
        return {
            "templates_total": len(self.templates),
            "projects_total": len(self.projects),
            "agent_types": list(set(t.agent_type for t in self.templates.values())),
        }

    def to_dict(self) -> Dict:
        return {
            "templates": self.list_templates(),
            "projects": [p.to_dict() for p in self.projects.values()],
            "stats": self.get_stats(),
        }


__all__ = ["AgentsScaffold", "ScaffoldTemplate", "ScaffoldProject"]
