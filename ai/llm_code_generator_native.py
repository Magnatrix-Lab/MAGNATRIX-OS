"""LLM Code Generator — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class Language(Enum):
    PYTHON = auto()
    JAVASCRIPT = auto()
    RUST = auto()
    GO = auto()
    BASH = auto()

@dataclass
class CodeSnippet:
    id: str
    language: Language
    code: str
    description: str
    tags: List[str] = field(default_factory=list)

class CodeGenerator:
    def __init__(self) -> None:
        self._templates: Dict[str, Dict[Language, str]] = {}

    def register_template(self, name: str, templates: Dict[Language, str]) -> None:
        self._templates[name] = templates

    def generate(self, template_name: str, language: Language, params: Dict[str, str]) -> str:
        tmpl = self._templates.get(template_name, {}).get(language, "")
        result = tmpl
        for key, value in params.items():
            result = result.replace("{{" + key + "}}", value)
        return result

    def generate_function(self, language: Language, name: str, params: List[str], body: str) -> str:
        if language == Language.PYTHON:
            return "def " + name + "(" + ", ".join(params) + "):\n    " + body.replace("\n", "\n    ")
        elif language == Language.JAVASCRIPT:
            return "function " + name + "(" + ", ".join(params) + ") {\n    " + body.replace("\n", "\n    ") + "\n}"
        elif language == Language.GO:
            return "func " + name + "(" + ", ".join(params) + ") {\n    " + body.replace("\n", "\n    ") + "\n}"
        elif language == Language.BASH:
            return name + "() {\n    " + body.replace("\n", "\n    ") + "\n}"
        return ""

    def get_stats(self) -> Dict[str, Any]:
        return {"templates": len(self._templates), "languages": len(Language)}

def run() -> None:
    print("Code Generator test")
    e = CodeGenerator()
    e.register_template("hello", {Language.PYTHON: "print('Hello {{name}}')", Language.JAVASCRIPT: "console.log('Hello {{name}}');"})
    print("  Python hello: " + e.generate("hello", Language.PYTHON, {"name": "World"}))
    print("  JS hello: " + e.generate("hello", Language.JAVASCRIPT, {"name": "World"}))
    print("  Function:\n" + e.generate_function(Language.PYTHON, "add", ["a", "b"], "return a + b"))
    print("  Stats: " + str(e.get_stats()))
    print("Code Generator test complete.")

if __name__ == "__main__":
    run()
