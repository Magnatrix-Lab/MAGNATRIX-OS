"""Prompt Template Engine — Template management, variable substitution, conditional blocks, versioning.

Modul ini menyediakan:
- PromptTemplate: single template with variable slots
- TemplateEngine: manage multiple templates, versioning, inheritance
- ConditionalBlock: if/else logic within templates
- TemplateValidator: validate required variables and types
- TemplateLibrary: pre-built template collections
"""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum, auto


class TemplateType(Enum):
    SYSTEM = "system"
    USER = "user"
    FEW_SHOT = "few_shot"
    CHAIN_OF_THOUGHT = "cot"
    TOOL_USE = "tool_use"
    REACT = "react"
    CUSTOM = "custom"


@dataclass
class PromptTemplate:
    """Single prompt template with metadata."""
    template_id: str
    name: str
    template_type: TemplateType
    content: str
    description: str = ""
    version: str = "1.0"
    variables: List[str] = field(default_factory=list)
    defaults: Dict[str, str] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    parent_id: Optional[str] = None

    def __post_init__(self):
        if not self.variables:
            self.variables = self._extract_variables()

    def _extract_variables(self) -> List[str]:
        pattern = r"\{\{(\w+)\}\}|\{<(\w+)>\}"
        matches = re.findall(pattern, self.content)
        return sorted(set(m[0] or m[1] for m in matches if m[0] or m[1]))

    def render(self, variables: Optional[Dict[str, Any]] = None, strict: bool = False) -> str:
        """Render template with variable substitution."""
        ctx = dict(self.defaults)
        if variables:
            ctx.update(variables)
        if strict:
            missing = [v for v in self.variables if v not in ctx]
            if missing:
                raise ValueError(f"Missing variables: {missing}")
        result = self.content
        for key, val in ctx.items():
            result = result.replace(f"{{{{ {key} }}}}", str(val))
            result = result.replace(f"{{{{{key}}}}}", str(val))
            result = result.replace(f"{{{{ {key} }}}}".replace(" ", ""), str(val))
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "type": self.template_type.value,
            "version": self.version,
            "variables": self.variables,
            "description": self.description,
            "tags": self.tags
        }


class ConditionalBlock:
    """If/else conditional block within templates."""

    def __init__(self, condition: str, true_branch: str, false_branch: str = ""):
        self.condition = condition
        self.true_branch = true_branch
        self.false_branch = false_branch

    def evaluate(self, variables: Dict[str, Any]) -> str:
        try:
            # Simple evaluation: check if condition variable is truthy
            val = variables.get(self.condition, False)
            if isinstance(val, str):
                val = val.lower() in ("true", "yes", "1", "on")
            return self.true_branch if val else self.false_branch
        except Exception:
            return self.false_branch

    @staticmethod
    def parse(content: str) -> Tuple[str, List[ConditionalBlock]]:
        """Parse conditional blocks from template content."""
        pattern = r"\{% if (\w+) %\}(.*?)\{% else %\}(.*?)\{% endif %\}|\{% if (\w+) %\}(.*?)\{% endif %\}"
        blocks = []
        def replacer(match):
            if match.group(1):
                blocks.append(ConditionalBlock(match.group(1), match.group(2), match.group(3)))
                return f"{{COND_{len(blocks)-1}}}"
            blocks.append(ConditionalBlock(match.group(4), match.group(5), ""))
            return f"{{COND_{len(blocks)-1}}}"
        cleaned = re.sub(pattern, replacer, content, flags=re.DOTALL)
        return cleaned, blocks

    @staticmethod
    def render(content: str, blocks: List[ConditionalBlock], variables: Dict[str, Any]) -> str:
        result = content
        for i, block in enumerate(blocks):
            result = result.replace(f"{{COND_{i}}}", block.evaluate(variables))
        return result


class TemplateValidator:
    """Validate template variables and constraints."""

    def __init__(self):
        self._rules: Dict[str, Callable[[Any], bool]] = {}

    def add_rule(self, variable: str, validator: Callable[[Any], bool]) -> None:
        self._rules[variable] = validator

    def validate(self, template: PromptTemplate, variables: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors = []
        for var in template.variables:
            if var not in variables and var not in template.defaults:
                errors.append(f"Missing variable: {var}")
        for var, rule in self._rules.items():
            if var in variables and not rule(variables[var]):
                errors.append(f"Validation failed for: {var}")
        return len(errors) == 0, errors


class TemplateEngine:
    """Manage template library with versioning and search."""

    def __init__(self):
        self._templates: Dict[str, PromptTemplate] = {}
        self._versions: Dict[str, List[str]] = {}  # name -> list of template_ids
        self._tags: Dict[str, Set[str]] = {}  # tag -> set of template_ids

    def register(self, template: PromptTemplate) -> None:
        self._templates[template.template_id] = template
        self._versions.setdefault(template.name, []).append(template.template_id)
        for tag in template.tags:
            self._tags.setdefault(tag, set()).add(template.template_id)

    def get(self, template_id: str) -> Optional[PromptTemplate]:
        return self._templates.get(template_id)

    def find_by_name(self, name: str) -> List[PromptTemplate]:
        ids = self._versions.get(name, [])
        return [self._templates[i] for i in ids if i in self._templates]

    def find_by_tag(self, tag: str) -> List[PromptTemplate]:
        ids = self._tags.get(tag, set())
        return [self._templates[i] for i in ids if i in self._templates]

    def render(self, template_id: str, variables: Optional[Dict[str, Any]] = None, strict: bool = False) -> str:
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        # Parse conditional blocks
        cleaned, blocks = ConditionalBlock.parse(template.content)
        # Render variables
        temp_template = PromptTemplate("tmp", "tmp", TemplateType.CUSTOM, cleaned, variables=list(template.variables))
        temp_template.defaults = template.defaults
        rendered = temp_template.render(variables, strict)
        # Render conditionals
        return ConditionalBlock.render(rendered, blocks, variables or {})

    def list_all(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._templates.values()]

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "templates": self.list_all(),
                "count": len(self._templates)
            }, f, indent=2)


class TemplateLibrary:
    """Pre-built template collections."""

    @staticmethod
    def system_prompt() -> PromptTemplate:
        return PromptTemplate(
            template_id="sys-1",
            name="system_prompt",
            template_type=TemplateType.SYSTEM,
            content="You are {{ role }}, an AI assistant. You are {{ trait }}. Respond in {{ language }}.",
            description="General system prompt template",
            defaults={"role": "helpful", "trait": "precise and concise", "language": "English"},
            tags=["system", "general"]
        )

    @staticmethod
    def few_shot() -> PromptTemplate:
        return PromptTemplate(
            template_id="fs-1",
            name="few_shot",
            template_type=TemplateType.FEW_SHOT,
            content="Examples:\n{{ examples }}\n\nNow solve: {{ task }}",
            description="Few-shot learning template",
            tags=["few_shot", "learning"]
        )

    @staticmethod
    def chain_of_thought() -> PromptTemplate:
        return PromptTemplate(
            template_id="cot-1",
            name="chain_of_thought",
            template_type=TemplateType.CHAIN_OF_THOUGHT,
            content="Question: {{ question }}\n\nLet's think step by step.\n{% if show_working %}Show all working: {{ working }}{% else %}Provide final answer only.{% endif %}",
            description="Chain of thought reasoning",
            tags=["cot", "reasoning"]
        )

    @staticmethod
    def tool_use() -> PromptTemplate:
        return PromptTemplate(
            template_id="tool-1",
            name="tool_use",
            template_type=TemplateType.TOOL_USE,
            content="Available tools: {{ tools }}\n\nTask: {{ task }}\n{% if use_tool %}Use tool: {{ tool_name }}{% else %}Answer directly.{% endif %}",
            description="Tool use prompt",
            tags=["tool", "agent"]
        )

    @staticmethod
    def react() -> PromptTemplate:
        return PromptTemplate(
            template_id="react-1",
            name="react",
            template_type=TemplateType.REACT,
            content="Question: {{ question }}\nThought: {{ thought }}\nAction: {{ action }}\nObservation: {{ observation }}\n{% if final_answer %}Final Answer: {{ final_answer }}{% endif %}",
            description="ReAct prompting template",
            tags=["react", "agent"]
        )

    @staticmethod
    def load_all(engine: TemplateEngine) -> None:
        for fn in [TemplateLibrary.system_prompt, TemplateLibrary.few_shot,
                   TemplateLibrary.chain_of_thought, TemplateLibrary.tool_use,
                   TemplateLibrary.react]:
            engine.register(fn())


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("PROMPT TEMPLATE ENGINE DEMO")
    print("=" * 70)

    # 1. Basic template rendering
    print("\n[1] Basic Template Rendering")
    template = PromptTemplate(
        "t1", "greeting", TemplateType.CUSTOM,
        "Hello {{ name }}! Welcome to {{ platform }}. You have {{ count }} messages.",
        defaults={"platform": "MAGNATRIX"}
    )
    print(f"  Variables: {template.variables}")
    rendered = template.render({"name": "Alice", "count": 5})
    print(f"  Rendered: {rendered}")

    # 2. Conditional blocks
    print("\n[2] Conditional Blocks")
    cot = TemplateLibrary.chain_of_thought()
    print(f"  Template: {cot.content[:80]}...")
    engine = TemplateEngine()
    engine.register(cot)
    result = engine.render("cot-1", {"question": "2+2", "show_working": True, "working": "2 + 2 = 4"})
    print(f"  With working: {result}")
    result2 = engine.render("cot-1", {"question": "2+2", "show_working": False})
    print(f"  Without working: {result2}")

    # 3. Template library
    print("\n[3] Template Library")
    engine = TemplateEngine()
    TemplateLibrary.load_all(engine)
    print(f"  Registered: {len(engine.list_all())} templates")
    for t in engine.list_all():
        print(f"    {t['name']} ({t['type']}) - vars: {t['variables']}")

    # 4. System prompt rendering
    print("\n[4] System Prompt")
    sys = engine.render("sys-1", {"role": "expert coder", "language": "Indonesian"})
    print(f"  {sys}")

    # 5. Validation
    print("\n[5] Validation")
    validator = TemplateValidator()
    validator.add_rule("count", lambda x: isinstance(x, int) and x >= 0)
    ok, errors = validator.validate(template, {"name": "Bob", "count": 10})
    print(f"  Valid: {ok}, Errors: {errors}")
    ok2, errors2 = validator.validate(template, {"name": "Bob", "count": -1})
    print(f"  Invalid: {ok2}, Errors: {errors2}")

    # 6. Versioning
    print("\n[6] Versioning")
    v1 = PromptTemplate("v1", "prompt", TemplateType.CUSTOM, "V1: {{ x }}", version="1.0")
    v2 = PromptTemplate("v2", "prompt", TemplateType.CUSTOM, "V2: {{ x }} {{ y }}", version="2.0", parent_id="v1")
    engine.register(v1)
    engine.register(v2)
    versions = engine.find_by_name("prompt")
    print(f"  Versions of 'prompt': {len(versions)}")

    # 7. Export
    print("\n[7] Export")
    engine.export("/tmp/templates.json")
    print(f"  Exported to /tmp/templates.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
