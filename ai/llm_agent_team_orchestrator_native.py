#!/usr/bin/env python3
"""
MAGNATRIX-OS — Agent Team Orchestrator
ai/llm_agent_team_orchestrator_native.py

Inspired by Auto-Company (github.com/MaxMiksa/Auto-Company)
Pattern: Agent Team Orchestration — persona-based roles, workflow-specific team formation.

Features:
- Agent registry with persona-based roles (14 agent types)
- Workflow routing (which agents for which workflow)
- Team formation (3-5 agents per task, not all 14)
- Role activation scoring (match agent to task by role relevance)
- Workflow pipeline execution (sequential agent handoffs)
- Team performance tracking

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("agent_team_orchestrator")


class AgentLayer(enum.Enum):
    STRATEGY = "strategy"
    PRODUCT = "product"
    ENGINEERING = "engineering"
    BUSINESS = "business"
    INTELLIGENCE = "intelligence"


class AgentStatus(enum.Enum):
    IDLE = "idle"
    ACTIVE = "active"
    BUSY = "busy"
    OFFLINE = "offline"


@dataclass
class AgentRole:
    id: str
    name: str
    persona: str
    layer: AgentLayer
    responsibilities: List[str]
    activation_keywords: List[str]


@dataclass
class Agent:
    role: AgentRole
    status: AgentStatus = AgentStatus.IDLE
    tasks_completed: int = 0
    success_rate: float = 1.0

    @property
    def is_available(self) -> bool:
        return self.status in (AgentStatus.IDLE, AgentStatus.ACTIVE)


@dataclass
class WorkflowStep:
    agent_id: str
    task: str
    output_key: str
    depends_on: Optional[str] = None


@dataclass
class Workflow:
    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    required_layers: List[AgentLayer] = field(default_factory=list)


@dataclass
class Team:
    agents: List[Agent]
    workflow: Workflow
    formed_at: str
    estimated_cycles: int = 1


class AgentRegistry:
    """Registry of 14 persona-based agents (Auto-Company pattern)."""

    DEFAULT_ROLES = [
        AgentRole("ceo-bezos", "CEO", "Jeff Bezos", AgentLayer.STRATEGY,
                  ["new product evaluation", "business model", "pricing", "major strategic choices", "resource allocation"],
                  ["strategy", "evaluate", "decision", "allocate", "prioritize"]),
        AgentRole("cto-vogels", "CTO", "Werner Vogels", AgentLayer.STRATEGY,
                  ["architecture design", "technical selection", "reliability", "performance", "technical debt"],
                  ["architecture", "design", "technical", "reliability", "performance"]),
        AgentRole("critic-munger", "Critic", "Charlie Munger", AgentLayer.STRATEGY,
                  ["challenge feasibility", "identify fatal flaws", "prevent group delusion", "inversion", "pre-mortem"],
                  ["critic", "challenge", "feasibility", "flaw", "pre-mortem", "veto"]),
        AgentRole("product-norman", "Product", "Don Norman", AgentLayer.PRODUCT,
                  ["product feature definition", "usability review", "user confusion analysis", "usability testing"],
                  ["product", "feature", "usability", "user", "review"]),
        AgentRole("ui-duarte", "UI", "Matias Duarte", AgentLayer.PRODUCT,
                  ["layout", "visual style", "design system", "color", "typography", "motion"],
                  ["ui", "design", "layout", "visual", "style", "color"]),
        AgentRole("interaction-cooper", "Interaction", "Alan Cooper", AgentLayer.PRODUCT,
                  ["user flow", "navigation", "persona definition", "interaction patterns"],
                  ["interaction", "flow", "navigation", "persona", "user flow"]),
        AgentRole("fullstack-dhh", "Fullstack", "DHH", AgentLayer.ENGINEERING,
                  ["code implementation", "technical choices", "code review", "refactor", "dev workflow"],
                  ["code", "implement", "build", "develop", "refactor", "review"]),
        AgentRole("qa-bach", "QA", "James Bach", AgentLayer.ENGINEERING,
                  ["test strategy", "quality checks", "bug analysis", "quality risk assessment"],
                  ["test", "qa", "quality", "bug", "release check"]),
        AgentRole("devops-hightower", "DevOps", "Kelsey Hightower", AgentLayer.ENGINEERING,
                  ["deployment pipelines", "CI/CD", "infrastructure", "observability", "incident response"],
                  ["deploy", "devops", "CI/CD", "pipeline", "infrastructure", "monitor"]),
        AgentRole("marketing-godin", "Marketing", "Seth Godin", AgentLayer.BUSINESS,
                  ["positioning", "differentiation", "marketing strategy", "content", "brand building"],
                  ["marketing", "position", "brand", "content", "strategy"]),
        AgentRole("operations-pg", "Operations", "Paul Graham", AgentLayer.BUSINESS,
                  ["user growth", "retention", "community", "operational metrics"],
                  ["growth", "retention", "community", "operations", "metrics"]),
        AgentRole("sales-ross", "Sales", "Aaron Ross", AgentLayer.BUSINESS,
                  ["pricing strategy", "sales model", "conversion", "CAC analysis"],
                  ["sales", "pricing", "conversion", "CAC", "revenue"]),
        AgentRole("cfo-campbell", "CFO", "Patrick Campbell", AgentLayer.BUSINESS,
                  ["pricing", "financial model", "unit economics", "cost control", "revenue tracking"],
                  ["finance", "pricing", "economics", "cost", "revenue", "model"]),
        AgentRole("research-thompson", "Research", "Ben Thompson", AgentLayer.INTELLIGENCE,
                  ["market research", "competitor analysis", "trend analysis", "business model decomposition", "demand validation"],
                  ["research", "market", "competitor", "trend", "analysis", "validate"]),
    ]

    def __init__(self):
        self._agents: Dict[str, Agent] = {}
        for role in self.DEFAULT_ROLES:
            self._agents[role.id] = Agent(role=role)

    def get(self, agent_id: str) -> Optional[Agent]:
        return self._agents.get(agent_id)

    def list_by_layer(self, layer: AgentLayer) -> List[Agent]:
        return [a for a in self._agents.values() if a.role.layer == layer]

    def list_all(self) -> List[Agent]:
        return list(self._agents.values())

    def set_status(self, agent_id: str, status: AgentStatus) -> bool:
        if agent_id in self._agents:
            self._agents[agent_id].status = status
            return True
        return False

    def record_task(self, agent_id: str, success: bool) -> None:
        agent = self._agents.get(agent_id)
        if agent:
            agent.tasks_completed += 1
            agent.success_rate = (agent.success_rate * (agent.tasks_completed - 1) + int(success)) / agent.tasks_completed


class TeamFormationEngine:
    """Form teams of 3-5 agents based on workflow."""

    def __init__(self, registry: AgentRegistry):
        self._registry = registry

    def score_agent(self, agent: Agent, task_keywords: List[str]) -> float:
        """Score agent relevance to task."""
        score = 0.0
        for kw in task_keywords:
            kw_lower = kw.lower()
            for ak in agent.role.activation_keywords:
                if kw_lower in ak.lower() or ak.lower() in kw_lower:
                    score += 0.3
            for resp in agent.role.responsibilities:
                if kw_lower in resp.lower():
                    score += 0.2
        if not agent.is_available:
            score *= 0.1
        return score

    def form_team(self, workflow: Workflow, task_keywords: Optional[List[str]] = None) -> Team:
        """Form a team of 3-5 agents for a workflow."""
        keywords = task_keywords or []
        # Score all agents
        scored = []
        for agent in self._registry.list_all():
            s = self.score_agent(agent, keywords + workflow.name.lower().split())
            scored.append((s, agent))
        scored.sort(key=lambda x: x[0], reverse=True)

        # Select top 3-5
        selected = [agent for _, agent in scored[:5]]
        for agent in selected:
            self._registry.set_status(agent.role.id, AgentStatus.ACTIVE)

        return Team(agents=selected, workflow=workflow, formed_at="now", estimated_cycles=len(workflow.steps))

    def dissolve_team(self, team: Team) -> None:
        for agent in team.agents:
            self._registry.set_status(agent.role.id, AgentStatus.IDLE)


class WorkflowRouter:
    """Route tasks to predefined workflow pipelines."""

    WORKFLOWS = {
        "product_evaluation": Workflow(
            "product_eval", "Product Evaluation",
            "Evaluate new product idea from research to decision",
            [
                WorkflowStep("research-thompson", "Market research and demand validation", "research_output"),
                WorkflowStep("ceo-bezos", "Strategic decision", "strategy_output", "research_output"),
                WorkflowStep("critic-munger", "Pre-mortem and feasibility check", "critic_output", "strategy_output"),
                WorkflowStep("product-norman", "Product feature definition", "product_output", "critic_output"),
                WorkflowStep("cto-vogels", "Technical feasibility", "tech_output", "product_output"),
                WorkflowStep("cfo-campbell", "Financial model and unit economics", "finance_output", "tech_output"),
            ],
            [AgentLayer.STRATEGY, AgentLayer.INTELLIGENCE, AgentLayer.PRODUCT, AgentLayer.ENGINEERING, AgentLayer.BUSINESS],
        ),
        "feature_development": Workflow(
            "feature_dev", "Feature Development",
            "Develop a feature from design to deployment",
            [
                WorkflowStep("interaction-cooper", "User flow design", "flow_output"),
                WorkflowStep("ui-duarte", "UI and visual design", "ui_output", "flow_output"),
                WorkflowStep("fullstack-dhh", "Implementation", "code_output", "ui_output"),
                WorkflowStep("qa-bach", "Testing and quality check", "qa_output", "code_output"),
                WorkflowStep("devops-hightower", "Deployment", "deploy_output", "qa_output"),
            ],
            [AgentLayer.PRODUCT, AgentLayer.ENGINEERING],
        ),
        "product_launch": Workflow(
            "launch", "Product Launch",
            "Launch product from QA to market",
            [
                WorkflowStep("qa-bach", "Final quality check", "qa_output"),
                WorkflowStep("devops-hightower", "Production deployment", "deploy_output", "qa_output"),
                WorkflowStep("marketing-godin", "Marketing campaign", "marketing_output", "deploy_output"),
                WorkflowStep("sales-ross", "Sales strategy", "sales_output", "marketing_output"),
                WorkflowStep("operations-pg", "Growth and operations", "ops_output", "sales_output"),
                WorkflowStep("ceo-bezos", "Final review", "final_output", "ops_output"),
            ],
            [AgentLayer.ENGINEERING, AgentLayer.BUSINESS, AgentLayer.STRATEGY],
        ),
        "pricing_review": Workflow(
            "pricing", "Pricing & Monetization",
            "Review and optimize pricing",
            [
                WorkflowStep("research-thompson", "Market and competitor pricing research", "research_output"),
                WorkflowStep("cfo-campbell", "Financial model and pricing strategy", "finance_output", "research_output"),
                WorkflowStep("sales-ross", "Sales model and conversion optimization", "sales_output", "finance_output"),
                WorkflowStep("critic-munger", "Pricing sanity check", "critic_output", "sales_output"),
                WorkflowStep("ceo-bezos", "Final pricing decision", "final_output", "critic_output"),
            ],
            [AgentLayer.INTELLIGENCE, AgentLayer.BUSINESS, AgentLayer.STRATEGY],
        ),
    }

    def get(self, workflow_id: str) -> Optional[Workflow]:
        return self.WORKFLOWS.get(workflow_id)

    def list_all(self) -> List[Workflow]:
        return list(self.WORKFLOWS.values())

    def find_by_keyword(self, keyword: str) -> List[Workflow]:
        keyword_lower = keyword.lower()
        return [w for w in self.WORKFLOWS.values() if keyword_lower in w.name.lower() or keyword_lower in w.description.lower()]


class AgentTeamOrchestrator:
    """Unified agent team orchestrator."""

    def __init__(self):
        self.registry = AgentRegistry()
        self.formation = TeamFormationEngine(self.registry)
        self.workflows = WorkflowRouter()
        self._teams: List[Team] = []
        self._execution_log: List[Dict[str, Any]] = []

    def execute_workflow(self, workflow_id: str, task_keywords: Optional[List[str]] = None) -> Dict[str, Any]:
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return {"error": f"Workflow {workflow_id} not found"}

        team = self.formation.form_team(workflow, task_keywords)
        self._teams.append(team)

        # Simulate execution
        results = {}
        for step in workflow.steps:
            agent = self.registry.get(step.agent_id)
            if agent and agent.is_available:
                results[step.output_key] = f"{agent.role.name} completed: {step.task}"
                self.registry.record_task(step.agent_id, success=True)
            else:
                results[step.output_key] = f"{step.agent_id} unavailable"

        self.formation.dissolve_team(team)

        log = {
            "workflow": workflow_id,
            "team": [a.role.id for a in team.agents],
            "results": results,
            "steps": len(workflow.steps),
        }
        self._execution_log.append(log)
        return log

    def get_agent_status(self) -> Dict[str, Any]:
        return {
            a.role.id: {"status": a.status.value, "tasks": a.tasks_completed, "success_rate": f"{a.success_rate:.1%}"}
            for a in self.registry.list_all()
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_agents": len(self.registry.list_all()),
            "available_agents": sum(1 for a in self.registry.list_all() if a.is_available),
            "teams_formed": len(self._teams),
            "workflows_executed": len(self._execution_log),
            "workflows": [w.id for w in self.workflows.list_all()],
        }


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Agent Team Orchestrator")
    print("ai/llm_agent_team_orchestrator_native.py")
    print("Pattern: Auto-Company Agent Team Orchestration (14 Personas)")
    print("=" * 60)

    orchestrator = AgentTeamOrchestrator()

    # 1. List all agents
    print("\n[1] All Agents")
    for a in orchestrator.registry.list_all():
        print(f"  {a.role.id} ({a.role.name} — {a.role.persona}) | {a.role.layer.value}")

    # 2. Execute product evaluation workflow
    print("\n[2] Execute Workflow: Product Evaluation")
    result = orchestrator.execute_workflow("product_evaluation", ["market", "strategy"])
    print(f"  Workflow: {result['workflow']}")
    print(f"  Team: {result['team']}")
    print(f"  Steps: {result['steps']}")

    # 3. Execute feature development
    print("\n[3] Execute Workflow: Feature Development")
    result = orchestrator.execute_workflow("feature_development", ["ui", "code", "deploy"])
    print(f"  Team: {result['team']}")
    for key, val in result['results'].items():
        print(f"    {key}: {val}")

    # 4. Agent status after execution
    print("\n[4] Agent Status")
    status = orchestrator.get_agent_status()
    for aid, s in list(status.items())[:5]:
        print(f"  {aid}: {s['status']}, tasks={s['tasks']}, success={s['success_rate']}")

    # 5. Workflows list
    print("\n[5] Available Workflows")
    for w in orchestrator.workflows.list_all():
        print(f"  {w.id}: {w.name} ({len(w.steps)} steps)")

    # 6. Stats
    print("\n[6] Orchestrator Stats")
    stats = orchestrator.get_stats()
    print(f"  {stats}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
