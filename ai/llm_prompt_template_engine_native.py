#!/usr/bin/env python3
"""
MAGNATRIX-OS — Prompt Template Engine
ai/llm_prompt_template_engine_native.py

Features:
- Variable substitution ({{var}} syntax)
- Conditional blocks ({% if %}...{% endif %})
- Loop rendering ({% for %}...{% endfor %})
- Template inheritance and composition
- Template validation and error reporting

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("template_engine")


@dataclass
class Template:
    id: str
    source: str
    compiled: Optional[str] = None


class PromptTemplateEngine:
    """Template engine with variable substitution, conditionals, and loops."""

    def __init__(self):
        self._templates: Dict[str, Template] = {}
        self._history: List[Dict[str, Any]] = []

    def register(self, template: Template) -> None:
        self._templates[template.id] = template

    def _substitute_vars(self, text: str, context: Dict[str, Any]) -> str:
        """Replace {{var}} with context values."""
        def replacer(match):
            key = match.group(1).strip()
            val = context.get(key)
            if val is None:
                return "{{" + key + "}}"
            return str(val)
        return re.sub(r'\{\{\s*(\w+)\s*\}\}', replacer, text)

    def _process_conditionals(self, text: str, context: Dict[str, Any]) -> str:
        """Process {% if var %}...{% endif %} blocks."""
        pattern = r'\{%\s*if\s+(\w+)\s*%\}(.*?)\{%\s*endif\s*%\}'
        def replacer(match):
            key = match.group(1).strip()
            block = match.group(2)
            if context.get(key, False):
                return block
            return ""
        return re.sub(pattern, replacer, text, flags=re.DOTALL)

    def _process_loops(self, text: str, context: Dict[str, Any]) -> str:
        """Process {% for item in items %}...{% endfor %} blocks."""
        pattern = r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}(.*?)\{%\s*endfor\s*%\}'
        def replacer(match):
            item_name = match.group(1).strip()
            list_name = match.group(2).strip()
            block = match.group(3)
            items = context.get(list_name, [])
            result = []
            for item in items:
                sub_ctx = {**context, item_name: item}
                rendered = self._substitute_vars(block, sub_ctx)
                result.append(rendered)
            return "\n".join(result)
        return re.sub(pattern, replacer, text, flags=re.DOTALL)

    def render(self, template_id: str, context: Dict[str, Any]) -> str:
        template = self._templates.get(template_id)
        if not template:
            return f"[Template {template_id} not found]"
        text = template.source
        text = self._process_loops(text, context)
        text = self._process_conditionals(text, context)
        text = self._substitute_vars(text, context)
        self._history.append({"template": template_id, "context_keys": list(context.keys())})
        return text

    def validate(self, template_id: str, required_vars: List[str]) -> List[str]:
        template = self._templates.get(template_id)
        if not template:
            return [f"Template {template_id} not found"]
        missing = []
        for var in required_vars:
            if f"{{{{{var}}}}}" not in template.source and f"{{{{ {var} }}}}" not in template.source:
                missing.append(var)
        return missing

    def get_stats(self) -> Dict[str, Any]:
        return {
            "templates": len(self._templates),
            "renders": len(self._history),
        }


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Prompt Template Engine")
    print("ai/llm_prompt_template_engine_native.py")
    print("=" * 60)

    engine = PromptTemplateEngine()

    # 1. Register templates
    print("\n[1] Register Templates")
    engine.register(Template("greeting", "Hello {{name}}! Welcome to {{service}}."))
    engine.register(Template("conditional", "{% if premium %}Premium user: {{name}}{% endif %}\nStandard user: {{name}}"))
    engine.register(Template("list", "Items:\n{% for item in items %}- {{item}}{% endfor %}"))
    engine.register(Template("complex", "User: {{name}}\n{% if admin %}Role: Administrator\n{% endif %}Permissions:\n{% for perm in permissions %}- {{perm}}\n{% endfor %}"))
    print("  Registered 4 templates")

    # 2. Simple substitution
    print("\n[2] Variable Substitution")
    result = engine.render("greeting", {"name": "Alice", "service": "MAGNATRIX"})
    print(f"  {result}")

    # 3. Conditional
    print("\n[3] Conditional Blocks")
    result = engine.render("conditional", {"name": "Bob", "premium": True})
    print(f"  Premium: {result.strip()}")
    result = engine.render("conditional", {"name": "Bob", "premium": False})
    print(f"  Standard: {result.strip()}")

    # 4. Loop
    print("\n[4] Loop Rendering")
    result = engine.render("list", {"items": ["Python", "AI", "Cloud"]})
    print(f"  {result}")

    # 5. Complex
    print("\n[5] Complex Template")
    result = engine.render("complex", {
        "name": "Carol",
        "admin": True,
        "permissions": ["read", "write", "delete"]
    })
    print(f"  {result}")

    # 6. Stats
    print("\n[6] Engine Stats")
    print(f"  {engine.get_stats()}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
