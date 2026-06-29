"""
agentic_tool_registry_native.py
MAGNATRIX-OS — Agentic Tool Registry

Inspired by Deer-Flow (ByteDance): Tool registry for agentic workflows.
Register, discover, and execute tools with schema validation. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class ToolSchema:
    tool_id: str
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    returns: Dict[str, Any] = field(default_factory=dict)
    category: str = "general"
    usage_count: int = 0
    success_rate: float = 0.0


class AgenticToolRegistry:
    """Register, discover, and execute tools with schema validation."""

    BUILT_IN_TOOLS = {
        "search_web": {
            "name": "Web Search", "description": "Search the web for information",
            "parameters": {"query": {"type": "string", "required": True}},
            "returns": {"results": {"type": "list"}}, "category": "search",
        },
        "read_file": {
            "name": "Read File", "description": "Read contents of a file",
            "parameters": {"path": {"type": "string", "required": True}},
            "returns": {"content": {"type": "string"}}, "category": "filesystem",
        },
        "write_file": {
            "name": "Write File", "description": "Write content to a file",
            "parameters": {"path": {"type": "string", "required": True}, "content": {"type": "string", "required": True}},
            "returns": {"success": {"type": "boolean"}}, "category": "filesystem",
        },
        "execute_code": {
            "name": "Execute Code", "description": "Execute code in sandbox",
            "parameters": {"code": {"type": "string", "required": True}, "language": {"type": "string", "required": False}},
            "returns": {"output": {"type": "string"}, "exit_code": {"type": "integer"}}, "category": "execution",
        },
        "summarize_text": {
            "name": "Summarize Text", "description": "Summarize long text",
            "parameters": {"text": {"type": "string", "required": True}, "max_length": {"type": "integer", "required": False}},
            "returns": {"summary": {"type": "string"}}, "category": "nlp",
        },
        "calculate": {
            "name": "Calculate", "description": "Perform mathematical calculation",
            "parameters": {"expression": {"type": "string", "required": True}},
            "returns": {"result": {"type": "number"}}, "category": "math",
        },
        "fetch_url": {
            "name": "Fetch URL", "description": "Fetch content from a URL",
            "parameters": {"url": {"type": "string", "required": True}},
            "returns": {"content": {"type": "string"}, "status": {"type": "integer"}}, "category": "network",
        },
        "list_directory": {
            "name": "List Directory", "description": "List files in a directory",
            "parameters": {"path": {"type": "string", "required": True}},
            "returns": {"files": {"type": "list"}}, "category": "filesystem",
        },
    }

    def __init__(self, registry_dir: str = "./tool_registry"):
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(exist_ok=True)
        self.tools: Dict[str, ToolSchema] = {}
        self._load()

    def _load(self) -> None:
        file = self.registry_dir / "tools.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for tid, td in data.items():
                        self.tools[tid] = ToolSchema(**td)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.registry_dir / "tools.json", "w", encoding="utf-8") as f:
            json.dump({tid: asdict(t) for tid, t in self.tools.items()}, f, indent=2)

    def register(self, tool_id: str, name: str, description: str, parameters: Dict[str, Any],
                 returns: Dict[str, Any], category: str = "general") -> ToolSchema:
        tool = ToolSchema(
            tool_id=tool_id, name=name, description=description,
            parameters=parameters, returns=returns, category=category,
        )
        self.tools[tool_id] = tool
        self._save()
        return tool

    def register_builtin(self, tool_id: str) -> Optional[ToolSchema]:
        if tool_id not in self.BUILT_IN_TOOLS:
            return None
        info = self.BUILT_IN_TOOLS[tool_id]
        return self.register(
            tool_id=tool_id, name=info["name"], description=info["description"],
            parameters=info["parameters"], returns=info["returns"], category=info["category"],
        )

    def discover(self, category: Optional[str] = None) -> List[ToolSchema]:
        if category:
            return [t for t in self.tools.values() if t.category == category]
        return list(self.tools.values())

    def get_tool(self, tool_id: str) -> Optional[ToolSchema]:
        return self.tools.get(tool_id)

    def validate_call(self, tool_id: str, args: Dict[str, Any]) -> bool:
        tool = self.tools.get(tool_id)
        if not tool:
            return False
        for param_name, param_info in tool.parameters.items():
            if param_info.get("required", False) and param_name not in args:
                return False
        return True

    def record_usage(self, tool_id: str, success: bool) -> bool:
        tool = self.tools.get(tool_id)
        if not tool:
            return False
        tool.usage_count += 1
        if success:
            tool.success_rate = (tool.success_rate * (tool.usage_count - 1) + 1.0) / tool.usage_count
        else:
            tool.success_rate = (tool.success_rate * (tool.usage_count - 1)) / tool.usage_count
        self._save()
        return True

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.tools)
        categories = {}
        for t in self.tools.values():
            categories[t.category] = categories.get(t.category, 0) + 1
        return {"total_tools": total, "categories": categories, "builtins": len(self.BUILT_IN_TOOLS)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["AgenticToolRegistry", "ToolSchema"]