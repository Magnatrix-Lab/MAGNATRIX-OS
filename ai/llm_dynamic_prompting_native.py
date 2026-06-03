"""LLM Dynamic Prompting — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class PromptTemplate:
    id: str
    template: str
    variables: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class DynamicPromptingEngine:
    def __init__(self) -> None:
        self._templates: Dict[str, PromptTemplate] = {}

    def register(self, template: PromptTemplate) -> None:
        self._templates[template.id] = template

    def render(self, template_id: str, context: Dict[str, Any], history: Optional[List[str]] = None) -> str:
        tmpl = self._templates.get(template_id)
        if not tmpl:
            raise ValueError("Template not found: " + template_id)
        text = tmpl.template
        for key, value in context.items():
            text = text.replace("{{" + key + "}}", str(value))
        if history:
            history_text = "\n".join("- " + h for h in history)
            text = text.replace("{{history}}", history_text)
        return text

    def get_stats(self) -> Dict[str, Any]:
        return {"templates": len(self._templates)}

def run() -> None:
    print("Dynamic Prompting test")
    e = DynamicPromptingEngine()
    e.register(PromptTemplate("greeting", "Hello {{name}}! How can I help you today?", ["name"]))
    e.register(PromptTemplate("qa", "Context: {{context}}\nQuestion: {{question}}\nHistory: {{history}}", ["context", "question", "history"]))
    print("  " + e.render("greeting", {"name": "Alice"}))
    print("  " + e.render("qa", {"context": "Paris is the capital of France", "question": "What is the capital?"}, ["User: Hello", "Assistant: Hi there"]))
    print("Dynamic Prompting test complete.")

if __name__ == "__main__":
    run()
