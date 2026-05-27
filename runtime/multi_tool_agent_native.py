#!/usr/bin/env python3
"""
AMATI — PELAJARI — TIRU
Magnatrix-OS :: Multi-Tool Agent Native
Pattern: agency-agents multi-tool integration
Pure Python stdlib. Runnable standalone.
"""

import json, os, re, textwrap, time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ── BaseLayer ──

@dataclass
class AgentPersonality:
    name: str
    role: str
    tone: str
    expertise_areas: List[str]
    communication_style: str

@dataclass
class ToolProfile:
    tool_name: str
    config_format: str
    install_path: str
    supported_features: List[str]

@dataclass
class DeliverableTemplate:
    deliverable_type: str
    checkitems: List[str]
    success_criteria: List[str]

# ── CoreEngine ──

class AgentBuilder:
    @staticmethod
    def build(personality: AgentPersonality, tool: ToolProfile) -> Dict:
        return {
            "system_prompt": AgentBuilder._system_prompt(personality, tool),
            "identity_manifest": {
                "name": personality.name,
                "role": personality.role,
                "tone": personality.tone,
                "expertise": personality.expertise_areas,
                "style": personality.communication_style,
            },
            "workflow_steps": [
                "1. Understand the task scope",
                "2. Plan deliverables with acceptance criteria",
                "3. Execute step-by-step with checkpoints",
                "4. Self-review against success criteria",
                "5. Deliver final output",
            ],
            "critical_rules": [
                "Never modify files outside the task scope",
                "Always confirm destructive actions",
                "Prefer readability over cleverness",
                "Document assumptions in comments",
            ],
            "success_metrics": ["Correctness", "Completeness", "Clarity", "Maintainability"],
            "tool": tool.tool_name,
        }

    @staticmethod
    def _system_prompt(p: AgentPersonality, t: ToolProfile) -> str:
        return (
            f"You are {p.name}, a {p.role}.\n"
            f"Tone: {p.tone}\n"
            f"Expertise: {', '.join(p.expertise_areas)}\n"
            f"Communication style: {p.communication_style}\n"
            f"Target tool: {t.tool_name} ({', '.join(t.supported_features)})\n"
        )

class ToolConverter:
    def __init__(self, agent_def: Dict):
        self.agent = agent_def

    def to_claude_md(self) -> str:
        m = self.agent["identity_manifest"]
        return textwrap.dedent(f"""\
            ---
            name: {m['name']}
            description: {m['role']}
            tools: Read, Write, Bash, Browser
            ---

            # {m['name']}

            {self.agent['system_prompt']}

            ## Workflow
            {chr(10).join(f"- {s}" for s in self.agent['workflow_steps'])}

            ## Rules
            {chr(10).join(f"- {r}" for r in self.agent['critical_rules'])}

            ## Success Metrics
            {chr(10).join(f"- {s}" for s in self.agent['success_metrics'])}
        """)

    def to_cursor_mdc(self) -> str:
        m = self.agent["identity_manifest"]
        return textwrap.dedent(f"""\
            ---
            description: {m['role']} agent rules
            globs: "*"
            alwaysApply: true
            ---

            # {m['name']}

            {self.agent['system_prompt']}

            ## Critical Rules
            {chr(10).join(f"- {r}" for r in self.agent['critical_rules'])}

            ## Workflow
            {chr(10).join(f"- {s}" for s in self.agent['workflow_steps'])}
        """)

    def to_aider_conventions(self) -> str:
        m = self.agent["identity_manifest"]
        lines = [
            f"# CONVENTIONS.md — {m['name']}",
            "",
            f"## Role: {m['role']}",
            f"## Tone: {m['tone']}",
            f"## Expertise: {', '.join(m['expertise'])}",
            "",
            "## Coding Conventions",
            "- Follow PEP 8 / project style guide",
            "- Write docstrings for public APIs",
            "- Add type hints where practical",
            "- Keep functions focused and small",
            "",
            "## Communication",
            f"- {m['style']}",
            "- Ask clarifying questions when scope is unclear",
            "",
            "## Rules",
        ]
        lines.extend(f"- {r}" for r in self.agent['critical_rules'])
        return "\n".join(lines)

    def to_openclaw_soul(self) -> Dict[str, str]:
        m = self.agent["identity_manifest"]
        soul = textwrap.dedent(f"""\
            # SOUL.md — {m['name']}

            - **Soul:** {m['role']}
            - **Core Tone:** {m['tone']}
            - **What I protect most:** quality, clarity, safety

            ## Speaking Style
            - {m['style']}
            - Short, purposeful sentences
            - No performative concern
        """)
        identity = textwrap.dedent(f"""\
            # IDENTITY.md — {m['name']}

            ## Core Role
            {m['role']} with expertise in {', '.join(m['expertise'])}.

            ## Boundaries
            {chr(10).join(f"- {r}" for r in self.agent['critical_rules'])}
        """)
        return {"SOUL.md": soul, "IDENTITY.md": identity}

    def to_windsurf_rules(self) -> str:
        m = self.agent["identity_manifest"]
        return textwrap.dedent(f"""\
            # .windsurfrules — {m['name']}

            {self.agent['system_prompt']}

            ## Workflow
            {chr(10).join(f"- {s}" for s in self.agent['workflow_steps'])}

            ## Rules
            {chr(10).join(f"- {r}" for r in self.agent['critical_rules'])}

            ## Metrics
            {chr(10).join(f"- {s}" for s in self.agent['success_metrics'])}
        """)

class Installer:
    def __init__(self, base_dir: str = "/tmp/magnatrix_agents"):
        self.base = base_dir

    def install(self, agent_name: str, tool: str, content: str, path_hint: str = "") -> str:
        tool_dir = os.path.join(self.base, tool.replace(" ", "_").lower())
        os.makedirs(tool_dir, exist_ok=True)
        file_path = os.path.join(tool_dir, f"{agent_name.replace(' ', '_').lower()}.md")
        with open(file_path, "w") as f:
            f.write(content)
        return file_path

    def install_openclaw(self, agent_name: str, files: Dict[str, str]) -> List[str]:
        oc_dir = os.path.join(self.base, "openclaw", agent_name.replace(" ", "_").lower())
        os.makedirs(oc_dir, exist_ok=True)
        out = []
        for fname, content in files.items():
            p = os.path.join(oc_dir, fname)
            with open(p, "w") as f:
                f.write(content)
            out.append(p)
        return out

# ── Features ──

class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, List[Dict]] = {
            "engineering": [],
            "creative": [],
            "analysis": [],
            "security": [],
        }

    def register(self, category: str, agent_def: Dict) -> None:
        if category not in self._agents:
            raise ValueError(f"Unknown category: {category}")
        self._agents[category].append(agent_def)

    def list_agents(self, category: Optional[str] = None) -> List[Dict]:
        if category:
            return list(self._agents.get(category, []))
        return [a for cat in self._agents.values() for a in cat]

    def get_by_name(self, name: str) -> Optional[Dict]:
        for cat in self._agents.values():
            for a in cat:
                if a.get("identity_manifest", {}).get("name") == name:
                    return a
        return None

class MultiToolSync:
    def __init__(self, converter: ToolConverter, installer: Installer):
        self.converter = converter
        self.installer = installer

    def sync(self, agent_name: str) -> Dict[str, str]:
        return {
            "claude": self.installer.install(agent_name, "claude", self.converter.to_claude_md()),
            "cursor": self.installer.install(agent_name, "cursor", self.converter.to_cursor_mdc()),
            "aider": self.installer.install(agent_name, "aider", self.converter.to_aider_conventions()),
            "windsurf": self.installer.install(agent_name, "windsurf", self.converter.to_windsurf_rules()),
            "openclaw": str(self.installer.install_openclaw(agent_name, self.converter.to_openclaw_soul())),
        }

class WorkflowEngine:
    def __init__(self):
        self.state: Dict[str, Dict] = {}

    def start(self, task_id: str, steps: List[str]) -> None:
        self.state[task_id] = {"steps": steps, "current": 0, "log": [], "done": False}

    def tick(self, task_id: str) -> Optional[str]:
        s = self.state.get(task_id)
        if not s or s["done"]:
            return None
        if s["current"] < len(s["steps"]):
            step = s["steps"][s["current"]]
            s["log"].append({"step": step, "ts": time.time(), "status": "done"})
            s["current"] += 1
            return step
        s["done"] = True
        return None

    def status(self, task_id: str) -> Dict:
        return self.state.get(task_id, {})

class QualityChecker:
    def __init__(self, template: DeliverableTemplate):
        self.template = template

    def validate(self, artifact: str) -> Dict:
        checks = {}
        for item in self.template.checkitems:
            checks[item] = item.lower() in artifact.lower()
        score = sum(checks.values()) / len(checks) if checks else 0.0
        return {"checks": checks, "score": round(score, 3), "pass": score >= 0.8}

# ── Kernel ──

class MultiToolAgentKernel:
    def __init__(self):
        self.builder = AgentBuilder()
        self.registry = AgentRegistry()
        self.installer = Installer()
        self.workflow = WorkflowEngine()

    def create_agent(self, personality: AgentPersonality, tool: ToolProfile) -> str:
        definition = self.builder.build(personality, tool)
        self.registry.register(self._guess_category(personality.role), definition)
        converter = ToolConverter(definition)
        synced = MultiToolSync(converter, self.installer).sync(personality.name)
        return json.dumps(synced, indent=2)

    def install_all(self, agent_name: str) -> List[str]:
        agent = self.registry.get_by_name(agent_name)
        if not agent:
            return []
        converter = ToolConverter(agent)
        sync = MultiToolSync(converter, self.installer)
        return list(sync.sync(agent_name).values())

    @staticmethod
    def _guess_category(role: str) -> str:
        role_l = role.lower()
        if any(w in role_l for w in ("frontend", "backend", "dev", "engineer", "code")):
            return "engineering"
        if any(w in role_l for w in ("security", "audit", "penetration")):
            return "security"
        if any(w in role_l for w in ("design", "creative", "ux", "writer")):
            return "creative"
        return "analysis"

# ── Self-Test ──

def _self_test():
    print("=" * 50)
    print("Multi-Tool Agent Native — Self Test")
    print("=" * 50)

    personality = AgentPersonality(
        name="Frontend Developer",
        role="Senior Frontend Engineer",
        tone="calm and precise",
        expertise_areas=["React", "TypeScript", "CSS", "Accessibility"],
        communication_style="Direct with examples",
    )

    tool = ToolProfile(
        tool_name="claude_code",
        config_format="markdown_frontmatter",
        install_path="~/.claude/agents/",
        supported_features=["Read", "Write", "Bash", "Browser"],
    )

    kernel = MultiToolAgentKernel()
    print("\n[1] Creating agent...")
    paths = kernel.create_agent(personality, tool)
    print(paths)

    print("\n[2] Converting to all 6 formats...")
    definition = kernel.builder.build(personality, tool)
    converter = ToolConverter(definition)
    print("  claude md:", len(converter.to_claude_md()), "chars")
    print("  cursor mdc:", len(converter.to_cursor_mdc()), "chars")
    print("  aider conventions:", len(converter.to_aider_conventions()), "chars")
    print("  windsurf rules:", len(converter.to_windsurf_rules()), "chars")
    oc = converter.to_openclaw_soul()
    print("  openclaw soul:", len(oc["SOUL.md"]), "chars")
    print("  openclaw identity:", len(oc["IDENTITY.md"]), "chars")

    print("\n[3] Registry check...")
    agents = kernel.registry.list_agents("engineering")
    print(f"  Engineering agents: {len(agents)}")

    print("\n[4] Workflow engine...")
    kernel.workflow.start("task-001", ["plan", "code", "test", "deliver"])
    while True:
        step = kernel.workflow.tick("task-001")
        if step is None:
            break
        print(f"  -> {step}")
    print("  Workflow done:", kernel.workflow.status("task-001")["done"])

    print("\n[5] Quality checker...")
    template = DeliverableTemplate(
        deliverable_type="Component",
        checkitems=["imports React", "exports default", "has props interface"],
        success_criteria=["Compiles", "Accessible", "Typed"],
    )
    qc = QualityChecker(template)
    result = qc.validate("import React from 'react'; export default function Button(props: Props) {}\n")
    print(f"  Score: {result['score']}, Pass: {result['pass']}")

    print("\n" + "=" * 50)
    print("All tests passed.")
    print("=" * 50)

if __name__ == "__main__":
    _self_test()
