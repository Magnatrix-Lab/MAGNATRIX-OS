#!/usr/bin/env python3
"""
pipeline.py — MAGNATRIX SDK Pipeline Builder
Builder pattern untuk define dan execute multi-step agent pipelines.

Usage:
    from magnatrix_sdk import Pipeline
    pipeline = Pipeline("trading-signal") \
        .step("scan", agent="scout", skill="scan-tokens") \
        .step("analyze", agent="analyst", skill="analyze-signal", depends_on=["scan"]) \
        .step("execute", agent="executor", skill="execute-trade", depends_on=["analyze"])
    
    result = client.pipeline_run(pipeline.to_dict())
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class PipelineStep:
    id: str
    agent: str
    skill: str
    depends_on: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)


class Pipeline:
    """Builder untuk MAGNATRIX multi-step pipeline."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.steps: Dict[str, PipelineStep] = {}

    def step(
        self,
        step_id: str,
        agent: str,
        skill: str,
        depends_on: Optional[List[str]] = None,
        **config,
    ) -> "Pipeline":
        """Add step ke pipeline."""
        self.steps[step_id] = PipelineStep(
            id=step_id,
            agent=agent,
            skill=skill,
            depends_on=depends_on or [],
            config=config,
        )
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Export ke dict untuk API submission."""
        return {
            "name": self.name,
            "description": self.description,
            "steps": [
                {
                    "id": s.id,
                    "agent": s.agent,
                    "skill": s.skill,
                    "depends_on": s.depends_on,
                    "config": s.config,
                }
                for s in self.steps.values()
            ],
        }

    @classmethod
    def from_template(cls, template_name: str) -> "Pipeline":
        """Create pipeline dari template built-in."""
        templates = {
            "trading-signal": {
                "description": "End-to-end trading pipeline",
                "steps": [
                    ("scan", "scout", "scan-tokens", []),
                    ("analyze", "analyst", "analyze-signal", ["scan"]),
                    ("risk_check", "guardian", "check-risk", ["analyze"]),
                    ("execute", "executor", "execute-trade", ["risk_check"]),
                ],
            },
            "security-audit": {
                "description": "Full whitebox security audit",
                "steps": [
                    ("recon", "researcher", "security-audit", []),
                    ("triage", "guardian", "check-risk", ["recon"]),
                    ("report", "writer", "daily-digest", ["triage"]),
                ],
            },
            "content-publish": {
                "description": "Research and publish content",
                "steps": [
                    ("research", "researcher", "content-research-writer", []),
                    ("review", "analyst", "analyze-signal", ["research"]),
                    ("publish", "writer", "daily-digest", ["review"]),
                ],
            },
        }
        t = templates.get(template_name, {"description": "", "steps": []})
        p = cls(template_name, t["description"])
        for sid, agent, skill, deps in t["steps"]:
            p.step(sid, agent, skill, deps)
        return p
