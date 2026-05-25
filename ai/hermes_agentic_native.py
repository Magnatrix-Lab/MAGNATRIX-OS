#!/usr/bin/env python3
"""
ai/hermes_agentic_native.py
===========================
Layer 10 Extension — Hermes Agentic Integration

MAGNATRIX-OS interface to Hermes Agentic API.
Hermes 3 / Hermes 2 Pro — function-calling capable models.

Usage:
  from ai.hermes_agentic_native import HermesAgentic
  hermes = HermesAgentic(api_key="...")
  response = hermes.chat("What is 2+2?", tools=[calc_tool])
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class HermesMessage:
    role: str
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    name: Optional[str] = None


@dataclass
class HermesTool:
    name: str
    description: str
    parameters: Dict[str, Any]
    fn: Optional[Callable[..., Any]] = None


class HermesAgentic:
    """Hermes Agentic API client — pure Python, zero external deps."""

    def __init__(self, api_key: Optional[str] = None,
                 base_url: str = "https://api.fireworks.ai/inference/v1",
                 model: str = "accounts/fireworks/models/hermes-3-llama-3-1-8b",
                 timeout: float = 30.0) -> None:
        self.api_key = api_key or os.environ.get("HERMES_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._tools: Dict[str, HermesTool] = {}
        self._history: List[Dict[str, Any]] = []

    def register_tool(self, tool: HermesTool) -> None:
        self._tools[tool.name] = tool

    def _format_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self._tools.values()
        ]

    def _execute_tool(self, call: Dict[str, Any]) -> str:
        name = call.get("function", {}).get("name", "")
        arguments = json.loads(call.get("function", {}).get("arguments", "{}"))
        tool = self._tools.get(name)
        if not tool or not tool.fn:
            return f"Error: tool '{name}' not found"
        try:
            result = tool.fn(**arguments)
            return str(result)
        except Exception as e:
            return f"Error executing {name}: {e}"

    def chat(self, message: str, system: str = "",
             enable_tools: bool = True) -> Dict[str, Any]:
        """Send chat message with optional tool calling."""
        self._history.append({"role": "user", "content": message})
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.extend(self._history)

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048,
        }
        if enable_tools and self._tools:
            payload["tools"] = self._format_tools()
            payload["tool_choice"] = "auto"

        # Pure-Python HTTP (no requests/httpx dependency)
        response = self._http_post(f"{self.base_url}/chat/completions", payload)

        if "error" in response:
            return response

        choice = response.get("choices", [{}])[0]
        assistant_msg = choice.get("message", {})
        content = assistant_msg.get("content", "")
        tool_calls = assistant_msg.get("tool_calls", [])

        # Execute tool calls and append results
        if tool_calls:
            self._history.append({
                "role": "assistant",
                "content": content or "",
                "tool_calls": tool_calls,
            })
            for call in tool_calls:
                result = self._execute_tool(call)
                self._history.append({
                    "role": "tool",
                    "tool_call_id": call.get("id", ""),
                    "name": call.get("function", {}).get("name", ""),
                    "content": result,
                })
            # Re-call with tool results
            return self.chat("", system=system, enable_tools=False)

        self._history.append({"role": "assistant", "content": content})
        return {"content": content, "role": "assistant", "model": self.model}

    def _http_post(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Minimal HTTP POST using urllib (zero dependency)."""
        import urllib.request
        import urllib.error
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"error": str(e)}

    def reset(self) -> None:
        self._history.clear()

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "history_len": len(self._history),
            "tools_registered": len(self._tools),
        }


def demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS  |  HERMES AGENTIC")
    print("=" * 60)
    hermes = HermesAgentic()
    print(f"Stats: {hermes.stats}")
    print("Usage: hermes.chat('question', system='...')")
    print("Set HERMES_API_KEY env var for live API calls")
    print("=" * 60)


if __name__ == "__main__":
    demo()
