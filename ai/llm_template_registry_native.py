"""
llm_template_registry_native.py
MAGNATRIX-OS Template Registry Engine
Native Python, stdlib only.
Provides prompt template registration, variable substitution, versioning, and conditional rendering.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Template:
    template_id: str
    name: str
    content: str
    version: str = "1.0"
    variables: List[str] = field(default_factory=list)
    description: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"template_id": self.template_id, "name": self.name, "version": self.version, "variables": self.variables}


class TemplateRegistryEngine:
    """Prompt template registry with variable substitution."""

    def __init__(self) -> None:
        self._templates: Dict[str, Template] = {}
        self._variable_pattern = re.compile(r'\{\{(\w+)\}\}')

    def register(self, template: Template) -> None:
        # Extract variables from content
        template.variables = self._variable_pattern.findall(template.content)
        self._templates[template.template_id] = template

    def get(self, template_id: str) -> Optional[Template]:
        return self._templates.get(template_id)

    def render(self, template_id: str, variables: Optional[Dict[str, Any]] = None,
               conditionals: Optional[Dict[str, bool]] = None) -> Optional[str]:
        template = self._templates.get(template_id)
        if not template:
            return None

        content = template.content
        vars = variables or {}

        # Substitute variables
        for key, value in vars.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))

        # Handle conditionals
        if conditionals:
            for key, condition in conditionals.items():
                if condition:
                    content = re.sub(rf'\[#if {key}\](.*?)\[/if\]', r'\1', content, flags=re.DOTALL)
                else:
                    content = re.sub(rf'\[#if {key}\](.*?)\[/if\]', '', content, flags=re.DOTALL)

        # Remove remaining unprocessed conditional blocks
        content = re.sub(r'\[#if \w+\].*?\[/if\]', '', content, flags=re.DOTALL)

        # Remove unsubstituted variables (optional, leave as is or empty)
        return content

    def validate(self, template_id: str, variables: Dict[str, Any]) -> List[str]:
        template = self._templates.get(template_id)
        if not template:
            return ["Template not found"]
        missing = [v for v in template.variables if v not in variables]
        return [f"Missing variable: {v}" for v in missing]

    def list_templates(self, tag: Optional[str] = None) -> List[Template]:
        templates = list(self._templates.values())
        if tag:
            templates = [t for t in templates if tag in t.tags]
        return templates

    def get_stats(self) -> Dict[str, Any]:
        return {
            "templates": len(self._templates),
            "total_variables": sum(len(t.variables) for t in self._templates.values()),
        }

    def clone(self, template_id: str, new_id: str, version: str = "1.0") -> Optional[Template]:
        template = self._templates.get(template_id)
        if not template:
            return None
        new_template = Template(
            template_id=new_id, name=f"{template.name} (clone)",
            content=template.content, version=version, tags=list(template.tags)
        )
        self.register(new_template)
        return new_template


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Template Registry Engine")
    print("=" * 60)

    engine = TemplateRegistryEngine()

    template = Template(
        template_id="greeting", name="Greeting Template",
        content="Hello {{name}}! Welcome to {{service}}. [#if premium]You have premium access.[/if]",
        tags=["user-facing"]
    )
    engine.register(template)

    print("\n--- Render ---")
    result = engine.render("greeting", {"name": "Alice", "service": "MAGNATRIX"}, {"premium": True})
    print(f"  {result}")

    result = engine.render("greeting", {"name": "Bob", "service": "MAGNATRIX"}, {"premium": False})
    print(f"  {result}")

    print("\n--- Validate ---")
    errors = engine.validate("greeting", {"name": "Alice"})
    print(f"  Validation errors: {errors}")

    print("\n--- Clone ---")
    cloned = engine.clone("greeting", "greeting_v2", version="2.0")
    print(f"  Cloned: {cloned.template_id if cloned else 'failed'}")

    print("\n--- Stats ---")
    print(engine.get_stats())

    print("\nTemplate Registry test complete.")


if __name__ == "__main__":
    run()
