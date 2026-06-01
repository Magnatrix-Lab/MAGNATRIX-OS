#!/usr/bin/env python3
"""
ai/llm_tools_native.py
MAGNATRIX-OS — Tool Use Engine for the LLM Arena
AMATI pattern: function-calling toolchains (Claude tool use, OpenAI functions, LangChain tools)

Pure Python, stdlib only. Simulates tool registration, schema validation,
safe execution, and result aggregation for LLM function calling.
"""
from __future__ import annotations

import json
import math
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


# ───────────────────────────────────────────────────────────────
# 0. SHARED UTILITIES
# ───────────────────────────────────────────────────────────────

def _now() -> float:
    return time.time()


def _safe_json_loads(text: str) -> Optional[Any]:
    try:
        return json.loads(text)
    except Exception:
        return None


# ───────────────────────────────────────────────────────────────
# 1. TOOL SCHEMA & REGISTRY
# ───────────────────────────────────────────────────────────────

@dataclass
class ToolSchema:
    """JSON-schema-like definition for a tool's parameters."""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON schema properties
    required: List[str] = field(default_factory=list)


@dataclass
class ToolResult:
    """Result of a single tool invocation."""
    tool_name: str
    arguments: Dict[str, Any]
    output: Any
    success: bool
    error: str = ""
    duration_ms: float = 0.0
    timestamp: float = 0.0


class ToolRegistry:
    """Registers and looks up tools by name with schema validation."""

    def __init__(self) -> None:
        self._tools: Dict[str, Tuple[ToolSchema, Callable]] = {}
        self._init_builtins()

    def _init_builtins(self) -> None:
        self.register(
            ToolSchema(
                name="python_code_execution",
                description="Execute Python code in a sandboxed environment and return the output.",
                parameters={
                    "code": {"type": "string", "description": "Python code to execute."},
                    "timeout": {"type": "number", "description": "Execution timeout in seconds.", "default": 5},
                },
                required=["code"],
            ),
            self._exec_python,
        )
        self.register(
            ToolSchema(
                name="shell_command",
                description="Run a shell command safely and return stdout/stderr.",
                parameters={
                    "command": {"type": "string", "description": "Shell command to run."},
                    "timeout": {"type": "number", "description": "Timeout in seconds.", "default": 10},
                },
                required=["command"],
            ),
            self._exec_shell,
        )
        self.register(
            ToolSchema(
                name="web_search",
                description="Search the web for a query and return top results with snippets.",
                parameters={
                    "query": {"type": "string", "description": "Search query."},
                    "num_results": {"type": "number", "description": "Number of results to return.", "default": 5},
                },
                required=["query"],
            ),
            self._exec_web_search,
        )
        self.register(
            ToolSchema(
                name="http_api_call",
                description="Make an HTTP GET/POST request to an API endpoint.",
                parameters={
                    "url": {"type": "string", "description": "Target URL."},
                    "method": {"type": "string", "description": "HTTP method (GET, POST, PUT, DELETE).", "default": "GET"},
                    "headers": {"type": "object", "description": "Optional headers dict.", "default": {}},
                    "body": {"type": "string", "description": "Optional request body for POST/PUT.", "default": ""},
                },
                required=["url"],
            ),
            self._exec_http,
        )
        self.register(
            ToolSchema(
                name="calculator",
                description="Evaluate a mathematical expression safely.",
                parameters={
                    "expression": {"type": "string", "description": "Math expression to evaluate."},
                },
                required=["expression"],
            ),
            self._exec_calculator,
        )
        self.register(
            ToolSchema(
                name="file_read",
                description="Read contents of a file.",
                parameters={
                    "path": {"type": "string", "description": "File path to read."},
                    "max_bytes": {"type": "number", "description": "Max bytes to read.", "default": 65536},
                },
                required=["path"],
            ),
            self._exec_file_read,
        )
        self.register(
            ToolSchema(
                name="file_write",
                description="Write text to a file.",
                parameters={
                    "path": {"type": "string", "description": "File path to write."},
                    "content": {"type": "string", "description": "Content to write."},
                    "append": {"type": "boolean", "description": "Append instead of overwrite.", "default": False},
                },
                required=["path", "content"],
            ),
            self._exec_file_write,
        )

    def register(self, schema: ToolSchema, executor: Callable) -> None:
        self._tools[schema.name] = (schema, executor)

    def get(self, name: str) -> Optional[Tuple[ToolSchema, Callable]]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": s.name,
                "description": s.description,
                "parameters": s.parameters,
                "required": s.required,
            }
            for s, _ in self._tools.values()
        ]

    def describe(self) -> str:
        return json.dumps([{"type": "function", "function": t} for t in self.list_tools()], indent=2)

    # ── Built-in executors (simulated) ──

    def _exec_python(self, code: str, timeout: int = 5) -> str:
        # Simulated sandbox execution
        safe_globals = {"__builtins__": {"len": len, "range": range, "print": print, "str": str, "int": int, "float": float, "list": list, "dict": dict, "set": set, "tuple": tuple, "abs": abs, "min": min, "max": max, "sum": sum, "sorted": sorted, "round": round, "enumerate": enumerate, "zip": zip, "map": map, "filter": filter, "all": all, "any": any, "chr": chr, "ord": ord, "hex": hex, "bin": bin, "pow": pow, "divmod": divmod, "isinstance": isinstance, "type": type, "hasattr": hasattr, "getattr": getattr, "dir": dir}}
        result = {"stdout": "", "stderr": "", "result": None}
        try:
            exec(code, safe_globals, result)
            return f"[EXECUTED] stdout: {result.get('stdout', '')} | result: {result.get('result')}"
        except Exception as e:
            return f"[ERROR] {type(e).__name__}: {e}"

    def _exec_shell(self, command: str, timeout: int = 10) -> str:
        # Simulated shell execution
        return f"[SHELL] Command '{command[:40]}' executed successfully. (simulated)"

    def _exec_web_search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        # Simulated web search results
        results = []
        for i in range(min(num_results, 5)):
            results.append({
                "title": f"Result {i+1} for '{query[:30]}'",
                "url": f"https://example.com/search/{i}",
                "snippet": f"Simulated snippet {i+1} containing relevant information about {query[:20]}...",
            })
        return results

    def _exec_http(self, url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None, body: str = "") -> Dict[str, Any]:
        # Simulated HTTP call
        return {
            "status": 200 if "example" in url else 404,
            "headers": {"Content-Type": "application/json", "X-Simulated": "true"},
            "body": f"{{\"simulated\": true, \"url\": \"{url}\", \"method\": \"{method}\"}}",
        }

    def _exec_calculator(self, expression: str) -> str:
        # Safe math evaluator using a restricted set of operations
        allowed_names = {"math": math, "abs": abs, "round": round, "max": max, "min": min, "sum": sum, "pow": pow, "len": len}
        try:
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return f"[RESULT] {result}"
        except Exception as e:
            return f"[ERROR] {type(e).__name__}: {e}"

    def _exec_file_read(self, path: str, max_bytes: int = 65536) -> str:
        # Simulated file read
        return f"[FILE] Contents of '{path}' (simulated read, max {max_bytes} bytes)."

    def _exec_file_write(self, path: str, content: str, append: bool = False) -> str:
        # Simulated file write
        mode = "append" if append else "write"
        return f"[FILE] {mode.capitalize()} {len(content)} bytes to '{path}' (simulated)."


# ───────────────────────────────────────────────────────────────
# 2. TOOL CALL PARSER
# ───────────────────────────────────────────────────────────────

class ToolCallParser:
    """Parses tool calls from model responses (JSON or markdown code blocks)."""

    @staticmethod
    def parse(text: str) -> List[Dict[str, Any]]:
        """Extract tool calls from raw model output."""
        calls = []

        # Try JSON array of tool calls
        if text.strip().startswith("["):
            data = _safe_json_loads(text)
            if isinstance(data, list):
                calls = data
            elif isinstance(data, dict) and "name" in data:
                calls = [data]

        # Try JSON object single call
        elif text.strip().startswith("{"):
            data = _safe_json_loads(text)
            if isinstance(data, dict):
                if "name" in data or "tool" in data:
                    calls = [data]
                elif "tool_calls" in data:
                    calls = data["tool_calls"]

        # Try markdown code blocks
        else:
            pattern = r"```(?:json)?\s*([\s\S]*?)```"
            matches = re.findall(pattern, text)
            for match in matches:
                data = _safe_json_loads(match.strip())
                if isinstance(data, dict):
                    calls.append(data)
                elif isinstance(data, list):
                    calls.extend(data)

        # Normalize each call
        normalized = []
        for call in calls:
            if not isinstance(call, dict):
                continue
            name = call.get("name") or call.get("tool") or call.get("function", {}).get("name")
            args = call.get("arguments") or call.get("args") or call.get("parameters") or call.get("function", {}).get("arguments", {})
            if isinstance(args, str):
                args = _safe_json_loads(args) or {}
            if name:
                normalized.append({"name": name, "arguments": args if isinstance(args, dict) else {}})

        return normalized

    @staticmethod
    def validate(call: Dict[str, Any], schema: ToolSchema) -> Tuple[bool, str]:
        """Validate arguments against schema. Returns (valid, error_message)."""
        args = call.get("arguments", {})
        missing = [r for r in schema.required if r not in args]
        if missing:
            return False, f"Missing required arguments: {missing}"
        return True, ""


# ───────────────────────────────────────────────────────────────
# 3. FUNCTION EXECUTOR
# ───────────────────────────────────────────────────────────────

class FunctionExecutor:
    """Executes tool calls safely with timeout, output capture, and error handling."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry
        self._call_history: List[ToolResult] = []

    def execute(self, tool_name: str, arguments: Dict[str, Any], timeout: int = 10) -> ToolResult:
        entry = self.registry.get(tool_name)
        if not entry:
            return ToolResult(
                tool_name=tool_name, arguments=arguments,
                output=None, success=False,
                error=f"Tool '{tool_name}' not found in registry.",
                duration_ms=0.0, timestamp=_now(),
            )

        schema, executor = entry
        valid, error = ToolCallParser.validate({"name": tool_name, "arguments": arguments}, schema)
        if not valid:
            return ToolResult(
                tool_name=tool_name, arguments=arguments,
                output=None, success=False,
                error=error, duration_ms=0.0, timestamp=_now(),
            )

        t0 = _now()
        try:
            # Apply timeout simulation
            result = executor(**arguments)
            elapsed = (_now() - t0) * 1000
            tool_result = ToolResult(
                tool_name=tool_name, arguments=arguments,
                output=result, success=True,
                error="", duration_ms=round(elapsed, 2),
                timestamp=_now(),
            )
        except Exception as e:
            elapsed = (_now() - t0) * 1000
            tool_result = ToolResult(
                tool_name=tool_name, arguments=arguments,
                output=None, success=False,
                error=f"{type(e).__name__}: {e}",
                duration_ms=round(elapsed, 2),
                timestamp=_now(),
            )

        self._call_history.append(tool_result)
        return tool_result

    def execute_batch(self, calls: List[Dict[str, Any]], timeout: int = 10) -> List[ToolResult]:
        return [self.execute(c["name"], c.get("arguments", {}), timeout) for c in calls]

    def history(self) -> List[ToolResult]:
        return self._call_history.copy()

    def last_call(self) -> Optional[ToolResult]:
        return self._call_history[-1] if self._call_history else None


# ───────────────────────────────────────────────────────────────
# 4. RESULT AGGREGATOR
# ───────────────────────────────────────────────────────────────

class ResultAggregator:
    """Combines tool results with model reasoning for a final answer."""

    def __init__(self, max_tool_output_chars: int = 2000) -> None:
        self.max_chars = max_tool_output_chars

    def aggregate(self, tool_results: List[ToolResult], reasoning: str = "") -> str:
        parts = []
        if reasoning:
            parts.append(f"[REASONING]\n{reasoning}")

        for tr in tool_results:
            status = "✅" if tr.success else "❌"
            output_str = str(tr.output) if tr.output is not None else "None"
            if len(output_str) > self.max_chars:
                output_str = output_str[: self.max_chars - 3] + "..."
            parts.append(
                f"{status} [{tr.tool_name}]\n"
                f"  args: {json.dumps(tr.arguments)}\n"
                f"  output: {output_str}\n"
                f"  time: {tr.duration_ms:.1f}ms"
                + (f"\n  error: {tr.error}" if tr.error else "")
            )

        if not tool_results:
            parts.append("[NO TOOLS CALLED]")

        return "\n\n".join(parts)

    def to_json(self, tool_results: List[ToolResult], reasoning: str = "") -> Dict[str, Any]:
        return {
            "reasoning": reasoning,
            "tool_calls": [
                {
                    "tool": r.tool_name,
                    "arguments": r.arguments,
                    "success": r.success,
                    "output": r.output,
                    "error": r.error,
                    "duration_ms": r.duration_ms,
                }
                for r in tool_results
            ],
            "all_success": all(r.success for r in tool_results) if tool_results else True,
            "total_duration_ms": sum(r.duration_ms for r in tool_results),
        }


# ───────────────────────────────────────────────────────────────
# 5. TOOL CONTEXT
# ───────────────────────────────────────────────────────────────

class ToolContext:
    """Tracks tool calls across a session for stateful reasoning."""

    def __init__(self, registry: Optional[ToolRegistry] = None) -> None:
        self.registry = registry or ToolRegistry()
        self.executor = FunctionExecutor(self.registry)
        self.aggregator = ResultAggregator()
        self._reasoning_chain: List[str] = []

    def call(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        return self.executor.execute(tool_name, arguments)

    def call_batch(self, calls: List[Dict[str, Any]]) -> List[ToolResult]:
        return self.executor.execute_batch(calls)

    def add_reasoning(self, text: str) -> None:
        self._reasoning_chain.append(text)

    def get_full_reasoning(self) -> str:
        return "\n→ ".join(self._reasoning_chain)

    def get_aggregated_result(self) -> str:
        return self.aggregator.aggregate(self.executor.history(), self.get_full_reasoning())

    def get_json_result(self) -> Dict[str, Any]:
        return self.aggregator.to_json(self.executor.history(), self.get_full_reasoning())

    def stats(self) -> Dict[str, Any]:
        history = self.executor.history()
        return {
            "total_calls": len(history),
            "successful": sum(1 for r in history if r.success),
            "failed": sum(1 for r in history if not r.success),
            "total_duration_ms": round(sum(r.duration_ms for r in history), 2),
            "tools_used": list(set(r.tool_name for r in history)),
        }


# ───────────────────────────────────────────────────────────────
# 6. HIGH-LEVEL ORCHESTRATOR
# ───────────────────────────────────────────────────────────────

class ToolUseEngine:
    """Main orchestrator: parse → validate → execute → aggregate."""

    def __init__(self) -> None:
        self.registry = ToolRegistry()
        self.context = ToolContext(self.registry)

    def run(self, model_response: str, reasoning: str = "") -> Dict[str, Any]:
        """Full pipeline: parse model output, execute tools, return aggregated result."""
        if reasoning:
            self.context.add_reasoning(reasoning)

        calls = ToolCallParser.parse(model_response)
        if not calls:
            return {"success": False, "error": "No tool calls found in model response.", "parsed": None}

        results = self.context.call_batch(calls)
        return {
            "success": all(r.success for r in results),
            "parsed_calls": calls,
            "tool_results": [self._result_to_dict(r) for r in results],
            "aggregated": self.context.get_aggregated_result(),
            "json": self.context.get_json_result(),
            "stats": self.context.stats(),
        }

    def _result_to_dict(self, r: ToolResult) -> Dict[str, Any]:
        return {
            "tool": r.tool_name, "arguments": r.arguments,
            "success": r.success, "output": r.output,
            "error": r.error, "duration_ms": r.duration_ms,
        }

    def available_tools(self) -> List[Dict[str, Any]]:
        return self.registry.list_tools()

    def describe_tools(self) -> str:
        return self.registry.describe()


# ───────────────────────────────────────────────────────────────
# 7. DEMO
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Tool Use Engine Demo")
    print("=" * 60)

    engine = ToolUseEngine()

    print("\n[1] Available Tools")
    for t in engine.available_tools():
        print(f"  • {t['name']}: {t['description'][:50]}...")

    print("\n[2] Single Tool Call — calculator")
    result = engine.run('{"name": "calculator", "arguments": {"expression": "2**10 + 3*7"}}')
    print(f"  success={result['success']}")
    print(f"  output={result['tool_results'][0]['output']}")

    print("\n[3] Single Tool Call — web_search")
    result = engine.run('{"name": "web_search", "arguments": {"query": "MAGNATRIX OS latest features", "num_results": 3}}')
    print(f"  success={result['success']}")
    print(f"  results={len(result['tool_results'][0]['output'])} items")

    print("\n[4] Single Tool Call — file_write")
    result = engine.run('{"name": "file_write", "arguments": {"path": "/tmp/test.txt", "content": "Hello from MAGNATRIX"}}')
    print(f"  success={result['success']}")
    print(f"  output={result['tool_results'][0]['output']}")

    print("\n[5] Multi Tool Call Batch")
    multi_call = json.dumps([
        {"name": "calculator", "arguments": {"expression": "math.sqrt(144)"}},
        {"name": "python_code_execution", "arguments": {"code": "x = [1,2,3,4,5]; result = sum(x)"}},
        {"name": "http_api_call", "arguments": {"url": "https://api.example.com/data", "method": "GET"}},
    ])
    result = engine.run(multi_call, reasoning="User wants: square root, list sum, and API fetch.")
    print(f"  overall_success={result['success']}")
    for r in result["tool_results"]:
        out_str = str(r['output']) if r['output'] is not None else r['error']
        print(f"    {r['tool']}: {out_str[:60]}")

    print("\n[6] Aggregated Result")
    print(result["aggregated"][:500])

    print("\n[7] Stats")
    print(f"  {json.dumps(result['stats'], indent=2)}")

    print("\n" + "=" * 60)
    print("Demo complete. Tool Use Engine ready for LLM Arena.")
    print("=" * 60)
