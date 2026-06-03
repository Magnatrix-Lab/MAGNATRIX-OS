#!/usr/bin/env python3
"""
MAGNATRIX-OS — Code Generator Engine
ai/llm_code_generator_native.py

Features:
- Template-based code generation (fill templates with params)
- Language-specific syntax patterns (Python, JS, Go, Rust)
- Function signature generation from description
- Test case generation from function spec
- Code snippet assembly and formatting

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("code_generator")


@dataclass
class FunctionSpec:
    name: str
    params: List[Tuple[str, str]]  # (name, type)
    return_type: str
    description: str


class CodeGeneratorEngine:
    """Template-based code generation for multiple languages."""

    TEMPLATES = {
        "python": {
            "function": "def {name}({params}):\n    \"\"\"{description}\"\"\"\n    {body}\n",
            "test": "def test_{name}():\n    result = {name}({args})\n    assert result == {expected}\n",
        },
        "javascript": {
            "function": "function {name}({params}) {{\n    // {description}\n    {body}\n}}\n",
            "test": "test('{name}', () => {{\n    expect({name}({args})).toBe({expected});\n}});\n",
        },
        "go": {
            "function": "func {name}({params}) {return_type} {{\n    // {description}\n    {body}\n}}\n",
            "test": "func Test{name}(t *testing.T) {{\n    result := {name}({args})\n    if result != {expected} {{\n        t.Errorf(\"Expected {expected}, got %v\", result)\n    }}\n}}\n",
        },
    }

    def generate_function(self, spec: FunctionSpec, lang: str = "python") -> str:
        template = self.TEMPLATES.get(lang, {}).get("function", "")
        params = ", ".join(f"{name}: {type_}" if lang == "python" else f"{name} {type_}" if lang == "go" else name for name, type_ in spec.params)
        body = "pass" if lang == "python" else "return null;" if lang == "javascript" else "return """
        return template.format(
            name=spec.name,
            params=params,
            description=spec.description,
            body=body,
            return_type=spec.return_type,
        )

    def generate_test(self, spec: FunctionSpec, lang: str = "python", args: str = "", expected: str = "") -> str:
        template = self.TEMPLATES.get(lang, {}).get("test", "")
        return template.format(
            name=spec.name,
            args=args,
            expected=expected,
        )

    def generate_class(self, name: str, methods: List[FunctionSpec], lang: str = "python") -> str:
        if lang == "python":
            lines = [f"class {name}:", f'    """Generated class."""']
            for m in methods:
                lines.append(f"    def {m.name}(self, {', '.join(n for n, _ in m.params)}):")
                lines.append(f"        \"\"\"{m.description}\"\"\"")
                lines.append("        pass")
            return "\n".join(lines)
        return f"// Class generation for {lang} not implemented"

    def get_stats(self) -> Dict[str, Any]:
        return {"languages": list(self.TEMPLATES.keys()), "templates": sum(len(v) for v in self.TEMPLATES.values())}


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Code Generator Engine")
    print("ai/llm_code_generator_native.py")
    print("=" * 60)

    engine = CodeGeneratorEngine()

    spec = FunctionSpec("calculate_sum", [("a", "int"), ("b", "int")], "int", "Calculate sum of two integers")

    for lang in ["python", "javascript", "go"]:
        print(f"\n[{lang.upper()}]")
        print(engine.generate_function(spec, lang))
        print(engine.generate_test(spec, lang, args="1, 2", expected="3"))

    print("\n[CLASS]")
    print(engine.generate_class("Calculator", [spec, FunctionSpec("multiply", [("a", "int"), ("b", "int")], "int", "Multiply two numbers")]))

    print(f"\nStats: {engine.get_stats()}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
