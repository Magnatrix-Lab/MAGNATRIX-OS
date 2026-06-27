#!/usr/bin/env python3
"""
Cross-Domain Skill Transfer for MAGNATRIX-OS
============================================
Auto composition of skills across domains (trading → coding → research).
Pure stdlib.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations
import json, re, time
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


@dataclass
class Skill:
    """A transferable skill."""
    skill_id: str
    name: str
    domain: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    implementation: str = ""
    confidence: float = 0.0
    usage_count: int = 0
    success_rate: float = 0.0
    created_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["implementation"] = self.implementation[:200] if self.implementation else ""
        return d


@dataclass
class SkillComposition:
    """A composed pipeline of skills."""
    composition_id: str
    name: str
    steps: List[Tuple[str, str]] = field(default_factory=list)  # (skill_id, output_name)
    source_domain: str = ""
    target_domain: str = ""
    success_rate: float = 0.0
    usage_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SkillRegistry:
    """Registry of all skills."""

    def __init__(self) -> None:
        self.skills: Dict[str, Skill] = {}
        self.compositions: Dict[str, SkillComposition] = {}
        self._counter = 0

    def register(self, skill: Skill) -> None:
        self.skills[skill.skill_id] = skill

    def get(self, skill_id: str) -> Optional[Skill]:
        return self.skills.get(skill_id)

    def find_by_domain(self, domain: str) -> List[Skill]:
        return [s for s in self.skills.values() if s.domain == domain]

    def find_by_output(self, output_type: str) -> List[Skill]:
        return [s for s in self.skills.values() if output_type in s.outputs]

    def find_by_input(self, input_type: str) -> List[Skill]:
        return [s for s in self.skills.values() if input_type in s.inputs]

    def get_domains(self) -> Set[str]:
        return set(s.domain for s in self.skills.values())

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_skills": len(self.skills),
            "total_compositions": len(self.compositions),
            "domains": sorted(self.get_domains()),
            "avg_success_rate": sum(s.success_rate for s in self.skills.values()) / len(self.skills) if self.skills else 0.0,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skills": {k: v.to_dict() for k, v in self.skills.items()},
            "compositions": {k: v.to_dict() for k, v in self.compositions.items()},
        }


class SkillComposer:
    """Composes skills into pipelines."""

    def __init__(self, registry: SkillRegistry) -> None:
        self.registry = registry

    def compose(self, source_domain: str, target_domain: str, input_data: str = "", max_steps: int = 5) -> Optional[SkillComposition]:
        """Find a path of skills from source to target domain."""
        source_skills = self.registry.find_by_domain(source_domain)
        target_skills = self.registry.find_by_domain(target_domain)
        if not source_skills or not target_skills:
            return None

        # BFS to find shortest path
        queue = [(s.skill_id, [s.skill_id]) for s in source_skills]
        visited = set()
        while queue:
            current_id, path = queue.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)
            current_skill = self.registry.get(current_id)
            if not current_skill:
                continue
            # Check if any target skill can be reached
            for out in current_skill.outputs:
                for target in target_skills:
                    if out in target.inputs or out in target.tags:
                        # Found path
                        steps = [(sid, self.registry.get(sid).outputs[0] if self.registry.get(sid).outputs else "") for sid in path + [target.skill_id]]
                        comp = SkillComposition(
                            composition_id=f"comp_{int(time.time())}",
                            name=f"{source_domain}_to_{target_domain}",
                            steps=steps,
                            source_domain=source_domain,
                            target_domain=target_domain,
                        )
                        self.registry.compositions[comp.composition_id] = comp
                        return comp
            # Extend search
            if len(path) < max_steps:
                for out in current_skill.outputs:
                    for next_skill in self.registry.find_by_input(out):
                        if next_skill.skill_id not in visited:
                            queue.append((next_skill.skill_id, path + [next_skill.skill_id]))
        return None

    def auto_compose(self, task_description: str) -> Optional[SkillComposition]:
        """Auto-compose skills based on task description."""
        # Extract domains from description
        words = set(w.lower() for w in re.findall(r'[a-zA-Z]+', task_description))
        domains = [d for d in self.registry.get_domains() if any(d.lower() in w for w in words)]
        if len(domains) >= 2:
            return self.compose(domains[0], domains[-1])
        # Try single domain
        if domains:
            skills = self.registry.find_by_domain(domains[0])
            if skills:
                steps = [(s.skill_id, s.outputs[0] if s.outputs else "") for s in skills[:3]]
                comp = SkillComposition(
                    composition_id=f"auto_{int(time.time())}",
                    name=f"auto_{domains[0]}",
                    steps=steps,
                    source_domain=domains[0],
                    target_domain=domains[0],
                )
                self.registry.compositions[comp.composition_id] = comp
                return comp
        return None


class SkillTransferLearner:
    """Transfers knowledge between domains."""

    def __init__(self, registry: SkillRegistry) -> None:
        self.registry = registry
        self.transfer_history: List[Dict[str, Any]] = []

    def transfer(self, skill_id: str, target_domain: str) -> Optional[Skill]:
        """Transfer a skill to a new domain."""
        source = self.registry.get(skill_id)
        if not source:
            return None
        new_skill = Skill(
            skill_id=f"{source.skill_id}_{target_domain}_{int(time.time())}",
            name=f"{source.name}_{target_domain}",
            domain=target_domain,
            inputs=source.inputs.copy(),
            outputs=source.outputs.copy(),
            implementation=f"# Transferred from {source.domain}\n{source.implementation}",
            confidence=source.confidence * 0.8,
            tags=source.tags + ["transferred", source.domain],
        )
        self.registry.register(new_skill)
        self.transfer_history.append({
            "source": skill_id,
            "target": new_skill.skill_id,
            "target_domain": target_domain,
            "timestamp": time.time(),
        })
        return new_skill

    def evaluate_transfer(self, transferred_skill_id: str, success: bool) -> None:
        skill = self.registry.get(transferred_skill_id)
        if not skill:
            return
        skill.usage_count += 1
        if success:
            skill.success_rate = (skill.success_rate * (skill.usage_count - 1) + 1.0) / skill.usage_count
            skill.confidence = min(1.0, skill.confidence + 0.05)
        else:
            skill.success_rate = (skill.success_rate * (skill.usage_count - 1)) / skill.usage_count
            skill.confidence = max(0.0, skill.confidence - 0.1)

    def get_transfer_stats(self) -> Dict[str, Any]:
        return {
            "total_transfers": len(self.transfer_history),
            "successful_transfers": sum(1 for s in self.registry.skills.values() if "transferred" in s.tags and s.success_rate > 0.5),
            "domains_connected": len(set(t["target_domain"] for t in self.transfer_history)),
        }


class CrossDomainTransfer:
    """Top-level orchestrator for cross-domain skill transfer."""

    def __init__(self) -> None:
        self.registry = SkillRegistry()
        self.composer = SkillComposer(self.registry)
        self.learner = SkillTransferLearner(self.registry)
        self._seed_skills()

    def _seed_skills(self) -> None:
        # Trading domain skills
        self.registry.register(Skill(
            skill_id="trading_ma",
            name="MovingAverageAnalysis",
            domain="trading",
            inputs=["price_series"],
            outputs=["ma_signal"],
            implementation="def ma(prices, period=20): return sum(prices[-period:])/period",
            tags=["technical", "indicator"],
        ))
        self.registry.register(Skill(
            skill_id="trading_risk",
            name="RiskAssessment",
            domain="trading",
            inputs=["position", "market_data"],
            outputs=["risk_score"],
            implementation="def risk(pos, market): return pos.size * market.volatility",
            tags=["risk", "management"],
        ))
        # Coding domain skills
        self.registry.register(Skill(
            skill_id="coding_parse",
            name="CodeParser",
            domain="coding",
            inputs=["source_code"],
            outputs=["ast_tree"],
            implementation="import ast; def parse(code): return ast.parse(code)",
            tags=["parsing", "analysis"],
        ))
        self.registry.register(Skill(
            skill_id="coding_optimize",
            name="CodeOptimizer",
            domain="coding",
            inputs=["ast_tree"],
            outputs=["optimized_code"],
            implementation="def optimize(tree): return ast.unparse(tree)",
            tags=["optimization", "refactoring"],
        ))
        # Research domain skills
        self.registry.register(Skill(
            skill_id="research_search",
            name="LiteratureSearch",
            domain="research",
            inputs=["query"],
            outputs=["paper_list"],
            implementation="def search(q): return [p for p in papers if q in p.title]",
            tags=["search", "literature"],
        ))
        self.registry.register(Skill(
            skill_id="research_summarize",
            name="PaperSummarizer",
            domain="research",
            inputs=["paper_text"],
            outputs=["summary"],
            implementation="def summarize(text): return text[:500] + '...'",
            tags=["nlp", "summarization"],
        ))
        # Cross-domain bridging skills
        self.registry.register(Skill(
            skill_id="bridge_signal_to_code",
            name="SignalToCode",
            domain="bridge",
            inputs=["ma_signal"],
            outputs=["source_code"],
            implementation="def signal_to_code(signal): return f'def strategy(): return {signal}'",
            tags=["bridge", "trading", "coding"],
        ))
        self.registry.register(Skill(
            skill_id="bridge_code_to_paper",
            name="CodeToPaper",
            domain="bridge",
            inputs=["source_code"],
            outputs=["paper_text"],
            implementation="def code_to_paper(code): return f'Algorithm description: {code[:200]}'",
            tags=["bridge", "coding", "research"],
        ))

    def compose(self, source: str, target: str) -> Optional[SkillComposition]:
        return self.composer.compose(source, target)

    def auto_compose(self, task: str) -> Optional[SkillComposition]:
        return self.composer.auto_compose(task)

    def transfer(self, skill_id: str, target_domain: str) -> Optional[Skill]:
        return self.learner.transfer(skill_id, target_domain)

    def evaluate(self, skill_id: str, success: bool) -> None:
        self.learner.evaluate_transfer(skill_id, success)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "registry": self.registry.get_stats(),
            "transfer": self.learner.get_transfer_stats(),
            "compositions": len(self.registry.compositions),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()
