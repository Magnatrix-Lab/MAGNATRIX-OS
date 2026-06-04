"""Template Engine - Variable substitution for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import re

@dataclass
class TemplateEngine:
    templates: Dict[str, str] = field(default_factory=dict)
    
    def register(self, name: str, template: str) -> None:
        self.templates[name] = template
    
    def render(self, name: str, variables: Dict[str, str]) -> str:
        template = self.templates.get(name, "")
        for key, value in variables.items():
            template = template.replace(f"{{{key}}}", str(value))
        return template
    
    def stats(self) -> dict:
        return {"templates": len(self.templates)}

def run():
    te = TemplateEngine()
    te.register("greeting", "Hello {name}, you are {age} years old.")
    print(te.render("greeting", {"name": "Alice", "age": "30"}))
    print("Stats:", te.stats())

if __name__ == "__main__": run()
