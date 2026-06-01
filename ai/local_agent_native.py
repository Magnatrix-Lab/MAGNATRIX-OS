# local_agent_native.py
# AMATI-PELAJARI-TIRU: Pure Python Local LLM Agent (no LangChain, no LlamaIndex)
# Manual prompt construction, tool parsing, rolling memory, GGUF loader stub.
# Pure Python, standard library only.

from __future__ import annotations
import json, re, time, dataclasses, typing, os, hashlib
from collections import deque
from typing import List, Dict, Optional, Callable, Any

# ---------------------------------------------------------------------------
# GGUF Loader Stub (real implementation via ctypes to llama.cpp)
# ---------------------------------------------------------------------------

class GGUFLoader:
    """Stub for GGUF model loading. Documented integration point for llama.cpp via ctypes."""

    def __init__(self, path: str):
        self.path = path
        self.loaded = False

    def load(self) -> bool:
        # STUB: real implementation would use ctypes to load llama.cpp shared library
        # and call llama_load_model_from_file(path, params)
        if os.path.exists(self.path) or self.path.endswith(".gguf"):
            self.loaded = True
        return self.loaded

    def generate(self, prompt: str, max_tokens: int = 256, temperature: float = 0.7) -> str:
        if not self.loaded:
            return "[Model not loaded]"
        # STUB: real implementation would call llama.cpp inference
        return f"[GGUF stub response for: {prompt[:40]}...]"

# ---------------------------------------------------------------------------
# Local LLM Interface
# ---------------------------------------------------------------------------

class LocalLLM:
    """Interface for local model. Swappable between real GGUF and mock."""

    def __init__(self, model_path: Optional[str] = None, mock: bool = True):
        self.mock = mock
        self.gguf = None
        if not mock and model_path:
            self.gguf = GGUFLoader(model_path)
            self.gguf.load()

    def generate(self, prompt: str, max_tokens: int = 256) -> str:
        if self.mock:
            return self._mock_generate(prompt, max_tokens)
        if self.gguf:
            return self.gguf.generate(prompt, max_tokens)
        return "[No model loaded]"

    def _mock_generate(self, prompt: str, max_tokens: int) -> str:
        # Deterministic heuristic based on prompt keywords
        if "tool" in prompt.lower() or "function" in prompt.lower():
            return json.dumps({"name": "search", "arguments": {"query": "hello"}})
        if "calculate" in prompt.lower() or "math" in prompt.lower():
            return "42"
        if "hello" in prompt.lower() or "hi" in prompt.lower():
            return "Hello! I am a local AI agent."
        return "This is a mock local LLM response."

# ---------------------------------------------------------------------------
# Prompt Builder
# ---------------------------------------------------------------------------

class PromptBuilder:
    """Manual prompt construction with system/user/assistant roles and tool schemas."""

    def __init__(self, system_prompt: str = "You are a helpful AI assistant."):
        self.system_prompt = system_prompt

    def build(self, history: List[Dict[str, str]], tools: List[Dict[str, Any]], user_message: str) -> str:
        lines = [f"<system>\n{self.system_prompt}\n</system>"]
        if tools:
            lines.append("<tools>")
            for tool in tools:
                lines.append(json.dumps(tool, indent=2))
            lines.append("</tools>")
        for msg in history:
            role = msg["role"]
            content = msg["content"]
            lines.append(f"<{role}>\n{content}\n</{role}>")
        lines.append(f"<user>\n{user_message}\n</user>")
        lines.append("<assistant>")
        return "\n".join(lines)

# ---------------------------------------------------------------------------
# Message Buffer (Rolling Memory)
# ---------------------------------------------------------------------------

class MessageBuffer:
    """Rolling buffer of recent messages."""

    def __init__(self, max_messages: int = 20):
        self.max_messages = max_messages
        self.buffer: deque = deque(maxlen=max_messages)

    def add(self, role: str, content: str):
        self.buffer.append({"role": role, "content": content, "timestamp": time.time()})

    def get_context(self, n: Optional[int] = None) -> List[Dict[str, str]]:
        msgs = list(self.buffer)
        if n:
            msgs = msgs[-n:]
        return [{"role": m["role"], "content": m["content"]} for m in msgs]

    def clear(self):
        self.buffer.clear()

    def to_dict(self) -> List[Dict[str, Any]]:
        return list(self.buffer)

# ---------------------------------------------------------------------------
# Tool Definition & Parser
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class ToolCall:
    tool_name: str
    arguments: Dict[str, Any]

class Tool:
    def __init__(self, name: str, schema: Dict[str, Any], run: Callable):
        self.name = name
        self.schema = schema
        self._run = run

    def run(self, arguments: Dict[str, Any]) -> Any:
        return self._run(**arguments)

class ToolParser:
    """Parse tool calls from LLM output (JSON or XML format)."""

    def parse(self, response: str) -> List[ToolCall]:
        calls = []
        # Try JSON
        try:
            data = json.loads(response)
            if isinstance(data, dict) and "name" in data:
                calls.append(ToolCall(data["name"], data.get("arguments", {})))
                return calls
            if isinstance(data, list):
                for item in data:
                    calls.append(ToolCall(item["name"], item.get("arguments", {})))
                return calls
        except json.JSONDecodeError:
            pass
        # Try XML: <tool_name>args</tool_name> or <TOOL: name>args</TOOL>
        xml_pattern = re.findall(r'<(\w+)>\s*(.*?)\s*</\1>', response, re.DOTALL)
        for name, args_text in xml_pattern:
            if name in ("system", "user", "assistant", "tools"):
                continue
            try:
                args = json.loads(args_text)
            except json.JSONDecodeError:
                args = {"query": args_text.strip()}
            calls.append(ToolCall(name, args))
        return calls

# ---------------------------------------------------------------------------
# Simple Agent
# ---------------------------------------------------------------------------

class SimpleAgent:
    """Loop with local LLM, memory, and tools."""

    def __init__(self, llm: LocalLLM, tools: List[Tool], system_prompt: str = "You are a helpful AI assistant.", max_steps: int = 5):
        self.llm = llm
        self.tools = {t.name: t for t in tools}
        self.memory = MessageBuffer()
        self.prompt_builder = PromptBuilder(system_prompt)
        self.max_steps = max_steps
        self.tool_parser = ToolParser()

    def run(self, goal: str) -> str:
        self.memory.add("user", goal)
        for _ in range(self.max_steps):
            history = self.memory.get_context()
            tool_schemas = [t.schema for t in self.tools.values()]
            prompt = self.prompt_builder.build(history, tool_schemas, goal)
            response = self.llm.generate(prompt, max_tokens=256)
            self.memory.add("assistant", response)
            # Parse tool calls
            calls = self.tool_parser.parse(response)
            if not calls:
                # No tool call, return as final answer
                return response
            # Execute tool calls
            for call in calls:
                tool = self.tools.get(call.tool_name)
                if tool:
                    try:
                        result = tool.run(call.arguments)
                        self.memory.add("system", f"Tool {call.tool_name} result: {result}")
                    except Exception as e:
                        self.memory.add("system", f"Tool {call.tool_name} error: {e}")
                else:
                    self.memory.add("system", f"Unknown tool: {call.tool_name}")
        # Return last assistant message if max steps reached
        history = self.memory.get_context()
        for msg in reversed(history):
            if msg["role"] == "assistant":
                return msg["content"]
        return "[No response generated]"

# ---------------------------------------------------------------------------
# Evaluator (Golden Dataset Regression Testing)
# ---------------------------------------------------------------------------

class Evaluator:
    """Compare agent output against golden answers."""

    def __init__(self, test_cases: List[Dict[str, Any]]):
        self.test_cases = test_cases

    def run(self, agent: SimpleAgent) -> Dict[str, Any]:
        results = []
        for case in self.test_cases:
            actual = agent.run(case["input"])
            expected = case["expected"]
            score = self._score(actual, expected)
            results.append({
                "input": case["input"],
                "expected": expected,
                "actual": actual,
                "score": score,
            })
        avg_score = sum(r["score"] for r in results) / len(results) if results else 0.0
        return {"results": results, "average_score": avg_score, "pass_rate": sum(1 for r in results if r["score"] >= 0.8) / len(results)}

    def _score(self, actual: str, expected: str) -> float:
        # Simple keyword overlap scoring
        a_words = set(re.findall(r'\w+', actual.lower()))
        e_words = set(re.findall(r'\w+', expected.lower()))
        if not e_words:
            return 1.0 if not a_words else 0.0
        overlap = len(a_words & e_words) / len(e_words)
        return overlap

# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------

class Telemetry:
    """Track latency, success rate, token usage."""

    def __init__(self):
        self.calls: List[Dict[str, Any]] = []
        self.total_tokens = 0

    def record(self, prompt: str, response: str, latency_ms: float, success: bool):
        self.calls.append({
            "prompt_length": len(prompt),
            "response_length": len(response),
            "latency_ms": latency_ms,
            "success": success,
            "timestamp": time.time(),
        })

    def export(self) -> Dict[str, Any]:
        total = len(self.calls)
        successes = sum(1 for c in self.calls if c["success"])
        avg_latency = sum(c["latency_ms"] for c in self.calls) / total if total else 0.0
        return {
            "total_calls": total,
            "success_count": successes,
            "success_rate": successes / total if total else 0.0,
            "average_latency_ms": avg_latency,
            "calls": self.calls,
        }

    def reset(self):
        self.calls.clear()
        self.total_tokens = 0

# ---------------------------------------------------------------------------
# Test Suite
# ---------------------------------------------------------------------------

def _test_gguf_loader():
    loader = GGUFLoader("dummy.gguf")
    assert loader.load() == True
    assert "stub" in loader.generate("hello").lower()
    print("[PASS] gguf loader stub")

def _test_local_llm():
    llm = LocalLLM(mock=True)
    assert "mock" in llm.generate("test").lower() or "42" in llm.generate("calculate")
    print("[PASS] local llm")

def _test_prompt_builder():
    pb = PromptBuilder("You are a test assistant.")
    prompt = pb.build([{"role": "user", "content": "hi"}], [], "hello")
    assert "system" in prompt
    assert "hello" in prompt
    print("[PASS] prompt builder")

def _test_message_buffer():
    buf = MessageBuffer(max_messages=3)
    buf.add("user", "a")
    buf.add("user", "b")
    buf.add("user", "c")
    buf.add("user", "d")
    assert len(buf.get_context()) == 3
    assert buf.get_context()[0]["content"] == "b"
    print("[PASS] message buffer")

def _test_tool_parser():
    parser = ToolParser()
    json_resp = '{"name": "search", "arguments": {"query": "cats"}}'
    calls = parser.parse(json_resp)
    assert len(calls) == 1
    assert calls[0].tool_name == "search"
    xml_resp = '<search>{"query": "dogs"}</search>'
    calls2 = parser.parse(xml_resp)
    assert calls2[0].tool_name == "search"
    print("[PASS] tool parser")

def _test_simple_agent():
    llm = LocalLLM(mock=True)
    search_tool = Tool("search", {"name": "search", "parameters": {"query": "string"}}, lambda query: f"Results for {query}")
    agent = SimpleAgent(llm, [search_tool])
    result = agent.run("What is the weather?")
    assert result
    print("[PASS] simple agent")

def _test_evaluator():
    cases = [{"input": "hello", "expected": "hello world"}]
    llm = LocalLLM(mock=True)
    agent = SimpleAgent(llm, [])
    ev = Evaluator(cases)
    report = ev.run(agent)
    assert "average_score" in report
    print("[PASS] evaluator")

def _test_telemetry():
    tel = Telemetry()
    tel.record("hi", "hello", 120.0, True)
    tel.record("test", "fail", 50.0, False)
    report = tel.export()
    assert report["total_calls"] == 2
    assert report["success_rate"] == 0.5
    print("[PASS] telemetry")

if __name__ == "__main__":
    _test_gguf_loader()
    _test_local_llm()
    _test_prompt_builder()
    _test_message_buffer()
    _test_tool_parser()
    _test_simple_agent()
    _test_evaluator()
    _test_telemetry()
    print("\n[OK] local_agent_native.py — all 8 tests passed")
