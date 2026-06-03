"""LLM Email Template Engine — Native Python (stdlib only)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class EmailTemplateEngine:
    def __init__(self) -> None:
        self._templates: Dict[str, str] = {}

    def register(self, name: str, template: str) -> None:
        self._templates[name] = template

    def render(self, name: str, variables: Dict[str, Any]) -> str:
        template = self._templates.get(name, "")
        result = template
        for key, value in variables.items():
            result = result.replace("{{" + key + "}}", str(value))
            result = result.replace("{{" + key + "|upper}}", str(value).upper())
            result = result.replace("{{" + key + "|lower}}", str(value).lower())
        result = re.sub(r'\{\{\w+\}\}', '', result)
        return result

    def render_batch(self, name: str, variable_sets: List[Dict[str, Any]]) -> List[str]:
        return [self.render(name, vars) for vars in variable_sets]

    def get_variables(self, template: str) -> List[str]:
        return re.findall(r'\{\{(\w+)(?:\|[^}]*)?\}\}', template)

    def get_stats(self) -> Dict[str, Any]:
        return {"templates": len(self._templates)}

def run() -> None:
    print("Email Template Engine test")
    e = EmailTemplateEngine()
    e.register("welcome", "Hello {{name}},\n\nWelcome to {{company}}!\n\nBest regards,\n{{sender}}")
    e.register("notification", "Dear {{name|upper}},\n\nYour {{item}} is ready.\n\nStatus: {{status}}")
    print("  Rendered:\n" + e.render("welcome", {"name": "Alice", "company": "TechCorp", "sender": "Team"}))
    print("  Variables: " + str(e.get_variables(e._templates["welcome"])))
    print("  Stats: " + str(e.get_stats()))
    print("Email Template Engine test complete.")

if __name__ == "__main__":
    run()
