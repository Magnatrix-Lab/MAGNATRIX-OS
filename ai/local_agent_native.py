#!/usr/bin/env python3
"""
MAGNATRIX-OS Layer: AI — Local LLM Agent from Scratch
File: ai/local_agent_native.py
Pattern: AMATI-PELAJARI-TIRU dari FirstFocus15/AI-Agents + agents-from-scratch

Native pure-Python reimplementation of:
  - Pure Python agent using local GGUF model (no frameworks)
  - Manual prompt construction with system/user/assistant roles
  - Simple memory: rolling buffer of recent messages
  - Tool definitions via JSON schema in prompt
  - Manual parsing of tool calls dari LLM output
  - GGUF loader stub (documented how to integrate real one)
  - Evaluation framework: golden dataset for regression testing
  - Telemetry: latency, success rate, token usage tracking

Zero external dependencies. Pure Python standard library.
"""

from __future__ import annotations

import json
import random
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 1.  LOCAL LLM — interface with GGUF stub
# ---------------------------------------------------------------------------

class LocalLLM:
    """
    Interface untuk local LLM. Mock implementation with deterministic responses.
    Real implementation: load GGUF via llama.cpp ctypes FFI.
    """

    def __init__(self, model_path: str = "mock-model.gguf") -> None:
        self.model_path = model_path
        self.loaded = False
        self._calls = 0
        self._tokens_generated = 0

    def load(self) -> bool:
        """Load model. Returns success."""
        # STUB: Real implementation uses llama.cpp via ctypes
        # Example:
        #   import ctypes
        #   lib = ctypes.CDLL("./libllama.so")
        #   ctx = lib.llama_load_model(self.model_path.encode())
        self.loaded = True
        return True

    def generate(self, prompt: str, max_tokens: int = 512,
                 temperature: float = 0.7) -> str:
        """Generate text from prompt."""
        if not self.loaded:
            self.load()
        self._calls += 1
        self._tokens_generated += min(max_tokens, len(prompt) // 4 + 20)

        # Mock: deterministic heuristic responses
        p = prompt.lower()
        if "search" in p or "find" in p:
            return f'{{"tool": "search", "args": "{prompt[:30]}"}}'
        if "write" in p or "save" in p:
            return f'{{"tool": "write_file", "args": "output.txt|{prompt[:50]}"}}'
        if "hello" in p or "hi" in p:
            return "Hello! I am a local LLM agent running entirely on your machine."
        if "calculate" in p or "math" in p or "=" in p:
            return "I can help with calculations. Please provide the expression."
        if "tool" in p and "{" in prompt:
            return "I will use the appropriate tool for this task."
        return f"[LocalLLM] Processed prompt ({len(prompt)} chars). This is a mock response for testing."

    def get_stats(self) -> Dict[str, Any]:
        return {
            "model": self.model_path,
            "calls": self._calls,
            "tokens_generated": self._tokens_generated,
        }


# ---------------------------------------------------------------------------
# 2.  PROMPT BUILDER
# ---------------------------------------------------------------------------

class PromptBuilder:
    """Builds prompts dengan system message, history, and tool definitions."""

    SYSTEM_TEMPLATE = """You are a helpful AI assistant running locally on the user's machine.
You have access to the following tools:
{tools}

When you need to use a tool, respond with a JSON object:
{{"tool": "TOOL_NAME", "args": "arguments"}}

Be concise and accurate."""

    @staticmethod
    def build(system: str, history: List[Dict[str, str]],
              tools: List[Dict[str, Any]]) -> str:
        """Build full prompt."""
        tools_desc = "\n".join(
            f"- {t['name']}: {t.get('description', 'No description')}"
            for t in tools
        )
        system_msg = system or PromptBuilder.SYSTEM_TEMPLATE.format(tools=tools_desc)

        parts = [f"<|system|>\n{system_msg}\n<|end|>"]
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            parts.append(f"<|{role}|>\n{content}\n<|end|>")
        parts.append("<|assistant|>\n")
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# 3.  MESSAGE BUFFER
# ---------------------------------------------------------------------------

class MessageBuffer:
    """Rolling memory buffer."""

    def __init__(self, max_messages: int = 20) -> None:
        self.max_messages = max_messages
        self.messages: List[Dict[str, str]] = []

    def add(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)

    def get_context(self) -> List[Dict[str, str]]:
        return self.messages.copy()

    def clear(self) -> None:
        self.messages = []


# ---------------------------------------------------------------------------
# 4.  TOOL DEFINITIONS
# ---------------------------------------------------------------------------

@dataclass
class Tool:
    name: str
    description: str
    schema: Dict[str, Any] = field(default_factory=dict)
    run_fn: Optional[Callable[..., str]] = None

    def run(self, args: str) -> str:
        if self.run_fn:
            return self.run_fn(args)
        return f"[TOOL] {self.name}({args})"


# ---------------------------------------------------------------------------
# 5.  TOOL PARSER
# ---------------------------------------------------------------------------

@dataclass
class ToolCall:
    tool_name: str
    arguments: str


class ToolParser:
    """Parses tool calls dari LLM output."""

    @staticmethod
    def parse(text: str) -> List[ToolCall]:
        """Extract tool calls dari text."""
        calls = []
        # JSON format: {"tool": "NAME", "args": "..."}
        try:
            # Try to find JSON objects
            pattern = r'\{[^}]*"tool"[^}]*\}'
            matches = re.findall(pattern, text)
            for m in matches:
                data = json.loads(m)
                if "tool" in data:
                    calls.append(ToolCall(data["tool"], data.get("args", "")))
        except Exception:
            pass

        # XML format fallback: <TOOL: NAME>args</TOOL>
        xml_pattern = r'<TOOL:\s*([A-Z_]+)>(.*?)</TOOL>'
        for match in re.finditer(xml_pattern, text, re.DOTALL | re.IGNORECASE):
            calls.append(ToolCall(match.group(1), match.group(2).strip()))

        return calls

    @staticmethod
    def has_tool_call(text: str) -> bool:
        return len(ToolParser.parse(text)) > 0


# ---------------------------------------------------------------------------
# 6.  SIMPLE AGENT
# ---------------------------------------------------------------------------

class SimpleAgent:
    """Agent loop dengan local LLM, memory, tools."""

    def __init__(self, llm: LocalLLM, tools: List[Tool],
                 max_steps: int = 10) -> None:
        self.llm = llm
        self.tools = {t.name: t for t in tools}
        self.memory = MessageBuffer()
        self.max_steps = max_steps
        self.step_count = 0

    def run(self, goal: str) -> str:
        """Execute agent loop."""
        self.memory.add("user", goal)
        response = ""

        while self.step_count < self.max_steps:
            self.step_count += 1

            # Build prompt
            tools_desc = [
                {"name": t.name, "description": t.description}
                for t in self.tools.values()
            ]
            prompt = PromptBuilder.build("", self.memory.get_context(), tools_desc)

            # Generate
            response = self.llm.generate(prompt, max_tokens=256)
            self.memory.add("assistant", response)

            # Check for tool calls
            calls = ToolParser.parse(response)
            if not calls:
                break  # No tool call = done

            # Execute tools
            for call in calls:
                if call.tool_name in self.tools:
                    result = self.tools[call.tool_name].run(call.arguments)
                    self.memory.add("tool", f"{call.tool_name}: {result}")
                else:
                    self.memory.add("tool", f"Unknown tool: {call.tool_name}")

        return response

    def get_history(self) -> List[Dict[str, str]]:
        return self.memory.get_context()


# ---------------------------------------------------------------------------
# 7.  EVALUATOR
# ---------------------------------------------------------------------------

class Evaluator:
    """Evaluate agent against golden dataset."""

    def __init__(self) -> None:
        self.cases: List[Dict[str, Any]] = []

    def add_case(self, input_text: str, expected_keywords: List[str],
                 description: str = "") -> None:
        self.cases.append({
            "input": input_text,
            "expected": expected_keywords,
            "description": description,
        })

    def evaluate(self, agent_factory: Callable[[], SimpleAgent]) -> Dict[str, Any]:
        """Run all test cases."""
        results = []
        for case in self.cases:
            agent = agent_factory()
            response = agent.run(case["input"])
            found = [kw for kw in case["expected"] if kw.lower() in response.lower()]
            score = len(found) / len(case["expected"]) if case["expected"] else 1.0
            results.append({
                "description": case["description"],
                "input": case["input"],
                "score": score,
                "found": found,
                "response_preview": response[:100],
            })

        avg_score = sum(r["score"] for r in results) / len(results) if results else 0
        return {
            "total": len(results),
            "passed": sum(1 for r in results if r["score"] >= 0.5),
            "avg_score": avg_score,
            "details": results,
        }


# ---------------------------------------------------------------------------
# 8.  TELEMETRY
# ---------------------------------------------------------------------------

class Telemetry:
    """Track runtime metrics."""

    def __init__(self) -> None:
        self.metrics: List[Dict[str, Any]] = []

    def record(self, event: str, data: Dict[str, Any]) -> None:
        self.metrics.append({
            "event": event,
            "time": time.time(),
            **data,
        })

    def summary(self) -> Dict[str, Any]:
        if not self.metrics:
            return {}
        latencies = [m.get("latency_ms", 0) for m in self.metrics if "latency_ms" in m]
        successes = sum(1 for m in self.metrics if m.get("success", False))
        total = len(self.metrics)
        return {
            "total_events": total,
            "success_rate": successes / total if total else 0,
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
            "max_latency_ms": max(latencies) if latencies else 0,
        }

    def export(self) -> str:
        return json.dumps(self.metrics, indent=2)


# ---------------------------------------------------------------------------
# 9.  MAIN DEMO & TEST SUITE
# ---------------------------------------------------------------------------

def _test_local_llm() -> None:
    llm = LocalLLM()
    r = llm.generate("Hello there")
    assert "Hello" in r
    assert llm.get_stats()["calls"] == 1
    print("  [OK] LocalLLM")


def _test_prompt_builder() -> None:
    prompt = PromptBuilder.build("", [
        {"role": "user", "content": "hi"},
    ], [{"name": "search", "description": "web search"}])
    assert "search" in prompt
    assert "hi" in prompt
    print("  [OK] PromptBuilder")


def _test_message_buffer() -> None:
    buf = MessageBuffer(max_messages=3)
    buf.add("user", "a")
    buf.add("user", "b")
    buf.add("user", "c")
    buf.add("user", "d")
    assert len(buf.get_context()) == 3
    assert buf.get_context()[0]["content"] == "b"
    print("  [OK] MessageBuffer")


def _test_tool_parser() -> None:
    text = 'Some text {\"tool\": "search\", "args\": "query"} more'
    calls = ToolParser.parse(text)
    assert len(calls) == 1
    assert calls[0].tool_name == "search"
    print("  [OK] ToolParser JSON")

    text2 = "Use <TOOL: WRITE_FILE>path.txt|content</TOOL> please"
    calls2 = ToolParser.parse(text2)
    assert len(calls2) == 1
    assert calls2[0].tool_name == "WRITE_FILE"
    print("  [OK] ToolParser XML")


def _test_simple_agent() -> None:
    llm = LocalLLM()
    tools = [
        Tool("search", "Search the web", run_fn=lambda q: f"Results for {q}"),
        Tool("write_file", "Write to file", run_fn=lambda a: "File written"),
    ]
    agent = SimpleAgent(llm, tools, max_steps=5)
    result = agent.run("Search for Python docs")
    assert agent.step_count >= 1
    assert len(agent.get_history()) >= 2
    print("  [OK] SimpleAgent")


def _test_evaluator() -> None:
    ev = Evaluator()
    ev.add_case("Say hello", ["hello"], "Basic greeting")
    llm = LocalLLM()
    tools = [Tool("echo", "Echo", run_fn=lambda x: x)]
    result = ev.evaluate(lambda: SimpleAgent(llm, tools, max_steps=3))
    assert result["total"] == 1
    print("  [OK] Evaluator")


def _test_telemetry() -> None:
    tel = Telemetry()
    tel.record("inference", {"latency_ms": 100, "success": True})
    tel.record("inference", {"latency_ms": 150, "success": True})
    tel.record("inference", {"latency_ms": 200, "success": False})
    s = tel.summary()
    assert s["total_events"] == 3
    assert s["success_rate"] == 2 / 3
    assert s["avg_latency_ms"] == 150
    print("  [OK] Telemetry")


def _test_gguf_stub_documentation() -> None:
    """Verify that GGUF integration path is documented."""
    import inspect
    src = inspect.getsource(LocalLLM.load)
    assert "llama.cpp" in src or "STUB" in src
    assert "ctypes" in src or "STUB" in src
    print("  [OK] GGUF stub documented")


def _demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Local LLM Agent — Native Demo")
    print("Pattern: AMATI-PELAJARI-TIRU dari agents-from-scratch")
    print("=" * 60)

    print("\n[Unit Tests]")
    _test_local_llm()
    _test_prompt_builder()
    _test_message_buffer()
    _test_tool_parser()
    _test_simple_agent()
    _test_evaluator()
    _test_telemetry()
    _test_gguf_stub_documentation()

    print("\n[Agent Conversation Demo]")
    llm = LocalLLM()
    tools = [
        Tool("search", "Web search", run_fn=lambda q: f"[MOCK] Found 3 results for '{q}'"),
        Tool("calculate", "Calculator", run_fn=lambda expr: f"[RESULT] {expr} = 42"),
    ]
    agent = SimpleAgent(llm, tools, max_steps=5)

    goals = [
        "What is the weather today?",
        "Calculate 100 / 4",
        "Write a summary of AI trends",
    ]

    for goal in goals:
        print(f"\nUser: {goal}")
        response = agent.run(goal)
        print(f"Agent: {response[:100]}...")

    print(f"\nTotal steps: {agent.step_count}")
    print(f"History length: {len(agent.get_history())}")

    print("\n[Evaluation Demo]")
    ev = Evaluator()
    ev.add_case("Say hello", ["Hello"], "Greeting")
    ev.add_case("Search for python", ["search", "python"], "Search task")
    result = ev.evaluate(lambda: SimpleAgent(LocalLLM(), tools, max_steps=3))
    print(f"Passed: {result['passed']}/{result['total']}")
    print(f"Avg score: {result['avg_score']:.2f}")

    print("\n[Telemetry Summary]")
    tel = Telemetry()
    for i in range(5):
        tel.record("inference", {
            "latency_ms": 80 + i * 10 + random.randint(-5, 5),
            "success": i < 4,
        })
    print(json.dumps(tel.summary(), indent=2))

    print("\n" + "=" * 60)
    print("All tests passed. Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    _demo()
