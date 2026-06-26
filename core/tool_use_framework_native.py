#!/usr/bin/env python3
"""Tool Use Framework for MAGNATRIX-OS — AI agent calls external tools."""
from __future__ import annotations
import json, time, re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    fn: Optional[Callable] = None

class ToolUseFramework:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def call(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        tool = self._tools.get(tool_name)
        if not tool:
            return {"error": f"Tool {tool_name} not found"}
        if tool.fn:
            try:
                result = tool.fn(**params)
                return {"status": "success", "result": result}
            except Exception as e:
                return {"status": "error", "error": str(e)}
        return {"error": "Tool has no function"}

    def list_tools(self) -> List[Dict[str, Any]]:
        return [{"name": t.name, "description": t.description, "params": list(t.parameters.keys())} for t in self._tools.values()]

    def parse_tool_call(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse tool call from LLM output like: CALL(tool_name, param1=value1)."""
        match = re.search(r'CALL\((\w+),?\s*(.*?)\)', text)
        if match:
            name = match.group(1)
            params_str = match.group(2)
            params = {}
            for pm in re.finditer(r'(\w+)=("[^"]*"|[^,\s]+)', params_str):
                k = pm.group(1)
                v = pm.group(2).strip('"')
                params[k] = v
            return {"tool": name, "params": params}
        return None

    def stats(self) -> Dict[str, Any]:
        return {"tools": len(self._tools)}
