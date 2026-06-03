"""LLM Data Formatter — Native Python (stdlib only)."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class OutputFormat(Enum):
    JSON = auto()
    CSV = auto()
    MARKDOWN = auto()
    XML = auto()
    YAML = auto()

class DataFormatter:
    def __init__(self) -> None:
        self._templates: Dict[str, str] = {}

    def set_template(self, name: str, template: str) -> None:
        self._templates[name] = template

    def to_json(self, data: Dict[str, Any]) -> str:
        return json.dumps(data, indent=2, ensure_ascii=False)

    def to_csv(self, records: List[Dict[str, Any]]) -> str:
        if not records:
            return ""
        headers = list(records[0].keys())
        lines = [",".join(headers)]
        for r in records:
            lines.append(",".join(str(r.get(h, "")) for h in headers))
        return "\n".join(lines)

    def to_markdown(self, records: List[Dict[str, Any]]) -> str:
        if not records:
            return ""
        headers = list(records[0].keys())
        lines = ["| " + " | ".join(headers) + " |"]
        lines.append("| " + " | ".join("---" for _ in headers) + " |")
        for r in records:
            lines.append("| " + " | ".join(str(r.get(h, "")) for h in headers) + " |")
        return "\n".join(lines)

    def format_with_template(self, template_name: str, data: Dict[str, Any]) -> str:
        tmpl = self._templates.get(template_name, "")
        result = tmpl
        for key, value in data.items():
            result = result.replace("{{" + key + "}}", str(value))
        return result

    def get_stats(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {"records": len(data), "keys": len(data[0]) if data else 0}

def run() -> None:
    print("Data Formatter test")
    e = DataFormatter()
    data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
    print("  JSON:\n" + e.to_json(data[0]))
    print("  CSV:\n" + e.to_csv(data))
    print("  Markdown:\n" + e.to_markdown(data))
    e.set_template("greeting", "Hello {{name}}, you are {{age}} years old.")
    print("  Template: " + e.format_with_template("greeting", data[0]))
    print("Data Formatter test complete.")

if __name__ == "__main__":
    run()
