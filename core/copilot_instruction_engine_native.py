"""
copilot_instruction_engine_native.py
MAGNATRIX-OS — Copilot Instruction Engine

Inspired by awesome-copilot instructions:
Trigger-pattern matching for dynamic prompt injection and context shaping.
Pure Python standard library.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class Instruction:
    instruction_id: str
    name: str
    description: str
    prompt: str
    trigger_patterns: List[str] = field(default_factory=list)
    priority: int = 50
    is_active: bool = True
    hit_count: int = 0
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class CopilotInstructionEngine:
    """Trigger-pattern matching for dynamic prompt injection."""

    INSTRUCTION_TEMPLATES = {
        "concise_responses": {
            "name": "Concise Responses",
            "description": "Keep responses brief and to the point",
            "prompt": "Be concise. Use bullet points. Avoid fluff. Answer directly.",
            "trigger_patterns": ["concise", "brief", "short", "tl;dr", "summary"],
            "priority": 10,
        },
        "explain_code": {
            "name": "Explain Code",
            "description": "Explain how code works step by step",
            "prompt": "Explain the code line by line. Describe what each section does, why it exists, and what patterns it uses. Use analogies where helpful.",
            "trigger_patterns": ["explain", "how does this work", "walk through", "break down"],
            "priority": 30,
        },
        "generate_tests": {
            "name": "Generate Tests",
            "description": "Generate test cases for code",
            "prompt": "Generate comprehensive test cases. Cover happy paths, edge cases, error conditions, and boundary values. Use pytest with fixtures and parametrization.",
            "trigger_patterns": ["test", "tests", "unit test", "coverage", "pytest"],
            "priority": 40,
        },
        "refactor_code": {
            "name": "Refactor Code",
            "description": "Suggest code improvements",
            "prompt": "Refactor the code to improve readability, performance, and maintainability. Identify code smells, reduce duplication, and simplify complexity. Preserve behavior.",
            "trigger_patterns": ["refactor", "improve", "clean up", "optimize", "rewrite"],
            "priority": 40,
        },
        "security_review": {
            "name": "Security Review",
            "description": "Review for security issues",
            "prompt": "Perform a security review. Check for injection, XSS, CSRF, auth bypass, insecure deserialization, secrets leakage, and OWASP Top 10 issues. Reference CWE IDs.",
            "trigger_patterns": ["security", "secure", "vulnerability", "audit", "owasp"],
            "priority": 20,
        },
        "performance_optimize": {
            "name": "Performance Optimize",
            "description": "Optimize for speed and memory",
            "prompt": "Optimize for performance. Identify algorithmic bottlenecks, reduce memory usage, minimize I/O, use caching, and consider Big-O complexity. Benchmark if possible.",
            "trigger_patterns": ["performance", "optimize", "fast", "slow", "memory", "bottleneck"],
            "priority": 35,
        },
        "add_documentation": {
            "name": "Add Documentation",
            "description": "Generate documentation for code",
            "prompt": "Add comprehensive documentation. Include docstrings (Google/NumPy style), type hints, README sections, and usage examples. Document parameters, returns, and exceptions.",
            "trigger_patterns": ["document", "docstring", "readme", "docs", "comment"],
            "priority": 45,
        },
        "review_pr": {
            "name": "Review PR",
            "description": "Review a pull request",
            "prompt": "Review this PR like a senior engineer. Check correctness, testing, style, security, performance, and backward compatibility. Provide actionable feedback with line references. Approve or request changes.",
            "trigger_patterns": ["pr review", "pull request", "review this", "approve", "request changes"],
            "priority": 25,
        },
    }

    def __init__(self, instructions_dir: str = "./copilot_instructions"):
        self.instructions_dir = Path(instructions_dir)
        self.instructions_dir.mkdir(exist_ok=True)
        self.instructions: Dict[str, Instruction] = {}
        self._load()

    def _load(self) -> None:
        file = self.instructions_dir / "instructions.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for iid, idata in data.items():
                        self.instructions[iid] = Instruction(**idata)
            except Exception:
                pass

    def _save(self) -> None:
        file = self.instructions_dir / "instructions.json"
        with open(file, "w", encoding="utf-8") as f:
            json.dump({iid: asdict(i) for iid, i in self.instructions.items()}, f, indent=2)

    def create_from_template(self, template_id: str, instruction_id: str) -> Optional[Instruction]:
        template = self.INSTRUCTION_TEMPLATES.get(template_id)
        if not template:
            return None
        inst = Instruction(
            instruction_id=instruction_id, name=template["name"], description=template["description"],
            prompt=template["prompt"], trigger_patterns=template.get("trigger_patterns", []),
            priority=template.get("priority", 50),
        )
        self.instructions[instruction_id] = inst
        self._save()
        return inst

    def create_custom(self, instruction_id: str, name: str, description: str,
                      prompt: str, trigger_patterns: Optional[List[str]] = None,
                      priority: int = 50) -> Instruction:
        inst = Instruction(
            instruction_id=instruction_id, name=name, description=description,
            prompt=prompt, trigger_patterns=trigger_patterns or [], priority=priority,
        )
        self.instructions[instruction_id] = inst
        self._save()
        return inst

    def match_instruction(self, query: str) -> Optional[Instruction]:
        q = query.lower()
        matches = []
        for inst in self.instructions.values():
            if not inst.is_active:
                continue
            for pattern in inst.trigger_patterns:
                if re.search(r"\b" + re.escape(pattern.lower()) + r"\b", q):
                    matches.append(inst)
                    break
        if not matches:
            return None
        best = min(matches, key=lambda x: x.priority)
        best.hit_count += 1
        self._save()
        return best

    def build_prompt(self, query: str) -> str:
        inst = self.match_instruction(query)
        if inst:
            return f"[Instruction: {inst.name}]\n{inst.prompt}\n\nQuery: {query}"
        return query

    def activate(self, instruction_id: str) -> bool:
        if instruction_id in self.instructions:
            self.instructions[instruction_id].is_active = True
            self._save()
            return True
        return False

    def deactivate(self, instruction_id: str) -> bool:
        if instruction_id in self.instructions:
            self.instructions[instruction_id].is_active = False
            self._save()
            return True
        return False

    def get_instruction(self, instruction_id: str) -> Optional[Instruction]:
        return self.instructions.get(instruction_id)

    def list_instructions(self) -> List[Instruction]:
        return list(self.instructions.values())

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.instructions)
        active = sum(1 for i in self.instructions.values() if i.is_active)
        total_hits = sum(i.hit_count for i in self.instructions.values())
        return {
            "total_instructions": total, "active": active,
            "templates": len(self.INSTRUCTION_TEMPLATES), "total_hits": total_hits,
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["CopilotInstructionEngine", "Instruction"]