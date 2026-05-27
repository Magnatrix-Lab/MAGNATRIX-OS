#!/usr/bin/env python3
"""
MAGNATRIX-OS Layer: AI — Meta Agent Framework
File: ai/meta_agent_native.py
Pattern: AMATI-PELAJARI-TIRU dari matthiasgeihs/agent

Native pure-Python reimplementation of:
  - Minimalist agent framework: everything prompt-driven
  - XML tool protocol: <TOOL: TOOL_NAME>args</TOOL>
  - Variable JSON system: all prompts stored as JSON arrays ["content"]
  - Pluggable: tool_detection, end_detection, memory_management
  - StreamingLogger: real-time file + stdout output
  - Agent optimization via variable variations testing
  - Directory-based agent organization

Zero external dependencies. Pure Python standard library.
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import os
import re
import sys
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

# LLM bridge for real backend integration
from ai.mock_to_unified_bridge import MockToUnifiedBridge


# ---------------------------------------------------------------------------
# 1.  STREAMING LOGGER — real-time tee stdout + file
# ---------------------------------------------------------------------------

class StreamingLogger:
    """Logger yang writes to both file dan stdout in real-time."""

    def __init__(self, log_path: str, mode: str = "w") -> None:
        self.terminal = sys.stdout
        self.log_file = open(log_path, mode)
        self._start_time = time.time()

    def write(self, message: str) -> None:
        self.terminal.write(message)
        self.log_file.write(message)
        self.terminal.flush()
        self.log_file.flush()

    def flush(self) -> None:
        self.terminal.flush()
        self.log_file.flush()

    def close(self) -> None:
        self.log_file.close()

    def __enter__(self) -> StreamingLogger:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


# ---------------------------------------------------------------------------
# 2.  VARIABLE STORE — JSON array prompt management
# ---------------------------------------------------------------------------

class VariableStore:
    """
    Manages runtime variables dari JSON array format.
    Each file: ["content"]  (bukan dict)
    """

    def __init__(self, var_dir: str) -> None:
        self.var_dir = var_dir
        self._cache: Dict[str, str] = {}
        self._load_all()

    def _load_all(self) -> None:
        if not os.path.isdir(self.var_dir):
            return
        for fname in os.listdir(self.var_dir):
            if fname.endswith(".json"):
                path = os.path.join(self.var_dir, fname)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list) and len(data) > 0:
                            self._cache[fname[:-5]] = data[0]
                except Exception:
                    pass

    def get(self, name: str, default: str = "") -> str:
        return self._cache.get(name, default)

    def set(self, name: str, value: str) -> None:
        self._cache[name] = value
        path = os.path.join(self.var_dir, f"{name}.json")
        os.makedirs(self.var_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([value], f, ensure_ascii=False)

    def all(self) -> Dict[str, str]:
        return self._cache.copy()

    def __contains__(self, name: str) -> bool:
        return name in self._cache


# ---------------------------------------------------------------------------
# 3.  TOOL REGISTRY — discover / register tools
# ---------------------------------------------------------------------------

class ToolRegistry:
    """Registry untuk agent tools."""

    def __init__(self) -> None:
        self._tools: Dict[str, Callable[[str], str]] = {}

    def register(self, name: str, fn: Callable[[str], str]) -> None:
        self._tools[name] = fn

    def get(self, name: str) -> Optional[Callable[[str], str]]:
        return self._tools.get(name)

    def list(self) -> List[str]:
        return list(self._tools.keys())

    def unregister(self, name: str) -> bool:
        if name in self._tools:
            del self._tools[name]
            return True
        return False


# ---------------------------------------------------------------------------
# 4.  META AGENT — core agent class
# ---------------------------------------------------------------------------

class MetaAgent:
    """
    Flexible agent framework yang manages conversations with LLM
    sambil handling tool calls dan memory management.

    Pattern dari matthiasgeihs/agent — minimal, prompt-driven, tunable.
    """

    def __init__(
        self,
        manifesto: str,
        model_name: str = "mock",
        memory: str = "",
        tools: Optional[Dict[str, Callable[[str], str]]] = None,
        end_detection: Optional[Callable[[str, str], bool]] = None,
        tool_detection: Optional[Callable[[str], Tuple[Optional[str], Optional[str]]]] = None,
        memory_management: Optional[Callable[[str], Optional[str]]] = None,
        memory_tracing: bool = False,
        max_steps: int = 20,
    ):
        self.manifesto = manifesto
        self.memory = memory
        self.model_name = model_name
        self.max_steps = max_steps
        self.step_count = 0
        self.memory_tracing = memory_tracing
        self._memory_trace: List[str] = []
        self._last_tool_called: Optional[str] = None
        self._log_handler: Callable[[str], None] = lambda msg: print(msg)

        # Built-in tools merged dengan user tools
        self.tools = {
            "ASK_USER": self._ask_user_builtin,
            "TELL_USER": self._tell_user_builtin,
            "SEARCH": self._search_builtin,
            "WRITE_FILE": self._write_file_builtin,
            "READ_FILE": self._read_file_builtin,
            **(tools or {}),
        }

        # Detection callbacks
        self._end_detection_fn = end_detection
        self._tool_detection_fn = tool_detection
        self._memory_mgmt_fn = memory_management

    # ----- Built-in tools -------------------------------------------------

    def _ask_user_builtin(self, question: str) -> str:
        """Ask user via stdin."""
        try:
            return input(f"{question}\nYour response: ")
        except EOFError:
            return ""

    def _tell_user_builtin(self, message: str) -> str:
        """Tell user via log handler."""
        self._log_handler(message)
        return "Message delivered."

    def _search_builtin(self, query: str) -> str:
        """Mock search — returns placeholder."""
        return f"[SEARCH RESULT] Mock results for: {query}"

    def _write_file_builtin(self, params: str) -> str:
        """Write file. Params format: path|content"""
        try:
            parts = params.split("|", 1)
            if len(parts) != 2:
                return "Error: format must be path|content"
            path, content = parts
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"File written: {path}"
        except Exception as e:
            return f"Error: {e}"

    def _read_file_builtin(self, path: str) -> str:
        """Read file contents."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading {path}: {e}"

    # ----- Public API -----------------------------------------------------

    def override_log_handler(self, fn: Callable[[str], None]) -> None:
        self._log_handler = fn

    def update_memory(self, text: str) -> None:
        if self.memory_tracing:
            self._memory_trace.append(self.memory)
        if callable(self._memory_mgmt_fn):
            result = self._memory_mgmt_fn(text)
            if result is not None:
                self.memory = result
        else:
            self.memory = text

    def get_memory_trace(self) -> List[str]:
        return self._memory_trace.copy()

    def compose_request(self) -> str:
        return self.manifesto + "\n\n" + self.memory

    def llm_call(self, prompt: str) -> str:
        """Mock LLM call — override untuk real LLM."""
        # Simple heuristic responses untuk demo
        p = prompt.lower()
        if "search" in p or "find" in p:
            return "<TOOL: SEARCH>query</TOOL>"
        if "write" in p or "save" in p:
            return "<TOOL: WRITE_FILE>path.txt|content</TOOL>"
        if "task completed" in p or "done" in p or "selesai" in p:
            return "Task completed successfully."
        if "<tool:" in p or "tool:" in p:
            return "I will use the appropriate tool to complete this task."
        return f"[LLM response for prompt length {len(prompt)}]"

    def detect_tool(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        if callable(self._tool_detection_fn):
            return self._tool_detection_fn(text)
        # Default: XML detection
        pattern = r"<TOOL:\s*([A-Z_]+)>(.*?)</TOOL>"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1), match.group(2).strip()
        return None, None

    def should_end(self) -> bool:
        if callable(self._end_detection_fn):
            return self._end_detection_fn(self.manifesto, self.memory)
        if self._last_tool_called is None:
            return True
        if "<TASK_COMPLETED>" in self.memory or "<DONE>" in self.memory:
            return True
        return False

    def run(self, goal: Optional[str] = None) -> str:
        """
        Agent loop: plan → llm_call → detect tool → execute → update memory → check end.
        """
        if goal:
            self.memory = f"Goal: {goal}\n"

        while self.step_count < self.max_steps:
            self.step_count += 1
            self._last_tool_called = None

            # 1. Compose request dan call LLM
            request = self.compose_request()
            response = self.llm_call(request)

            # 2. Update memory dengan response
            self.update_memory(self.memory + f"\nAgent: {response}")

            # 3. Detect dan execute tool
            tool_name, tool_args = self.detect_tool(response)
            if tool_name:
                tool_fn = self.tools.get(tool_name)
                if tool_fn:
                    self._last_tool_called = tool_name
                    try:
                        result = tool_fn(tool_args)
                    except Exception as e:
                        result = f"Tool error: {e}"
                    self.update_memory(self.memory + f"\nTool ({tool_name}): {result}")
                else:
                    self.update_memory(self.memory + f"\nTool Not Found: {tool_name}")

            # 4. Check end condition
            if self.should_end():
                break

        return self.memory


# ---------------------------------------------------------------------------
# 5.  AGENT FACTORY — discover agents dari directory
# ---------------------------------------------------------------------------

class AgentFactory:
    """Discover dan load agents dari directory structure."""

    @staticmethod
    def discover_agents(agents_dir: str) -> List[Tuple[str, Optional[str]]]:
        """Discover all agents in agents_dir."""
        agents = []
        if not os.path.isdir(agents_dir):
            return agents
        for item in sorted(os.listdir(agents_dir)):
            agent_path = os.path.join(agents_dir, item)
            if os.path.isdir(agent_path) and not item.startswith("__"):
                agents.append((item, None))
        return agents

    @staticmethod
    def load_agent_module(agent_dir: str) -> Optional[Type[MetaAgent]]:
        """Load agent class dari agent_dir/agent.py"""
        agent_py = os.path.join(agent_dir, "agent.py")
        if not os.path.isfile(agent_py):
            return None
        try:
            spec = importlib.util.spec_from_file_location("agent_module", agent_py)
            if spec is None or spec.loader is None:
                return None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, MetaAgent) and obj is not MetaAgent:
                    return obj
        except Exception:
            pass
        return None

    @staticmethod
    def load_variables(agent_dir: str) -> VariableStore:
        var_dir = os.path.join(agent_dir, "variables")
        return VariableStore(var_dir)


# ---------------------------------------------------------------------------
# 6.  AGENT OPTIMIZER — test N prompt variations
# ---------------------------------------------------------------------------

class AgentOptimizer:
    """
    Optimize agent dengan testing N prompt variations.
    Pattern dari matthiasgeihs/agent optimization system.
    """

    def __init__(self, agent_class: Type[MetaAgent], variables: VariableStore) -> None:
        self.agent_class = agent_class
        self.variables = variables
        self.results: List[Dict[str, Any]] = []

    def run_variation(self, manifesto: str, test_goal: str,
                      score_fn: Optional[Callable[[str], float]] = None) -> Dict[str, Any]:
        """Run one variation dan return result + score."""
        agent = self.agent_class(manifesto=manifesto)
        try:
            result = agent.run(test_goal)
            score = score_fn(result) if score_fn else len(result)
            return {"manifesto": manifesto, "result": result, "score": score, "steps": agent.step_count}
        except Exception as e:
            return {"manifesto": manifesto, "error": str(e), "score": 0.0, "steps": 0}

    def optimize(self, base_manifesto: str, test_goal: str,
                 variations: List[str],
                 score_fn: Optional[Callable[[str], float]] = None) -> Dict[str, Any]:
        """Test multiple manifesto variations dan return best."""
        best: Optional[Dict[str, Any]] = None
        for i, var in enumerate(variations):
            print(f"Testing variation {i + 1}/{len(variations)}...")
            result = self.run_variation(var, test_goal, score_fn)
            self.results.append(result)
            if best is None or result.get("score", 0) > best.get("score", 0):
                best = result
        return best or {}


# ---------------------------------------------------------------------------
# 7.  EXAMPLE AGENTS (built-in)
# ---------------------------------------------------------------------------

class ResearchAgent(MetaAgent):
    """Agent untuk web research (mock)."""

    def __init__(self, manifesto: str = "", memory: str = ""):
        if not manifesto:
            manifesto = (
                "You are a research agent. You search for information and summarize findings.\n"
                "Available tools: SEARCH, TELL_USER, ASK_USER, WRITE_FILE\n"
                "Tool format: <TOOL: TOOL_NAME>arguments</TOOL>\n"
                "End with <TASK_COMPLETED> when done."
            )
        super().__init__(manifesto=manifesto, memory=memory)


class SummaryAgent(MetaAgent):
    """Agent untuk summarizing text (mock)."""

    def __init__(self, manifesto: str = "", memory: str = "", chunk_size: int = 1000):
        self.chunk_size = chunk_size
        if not manifesto:
            manifesto = (
                "You are a summary agent. You break large text into chunks and summarize each.\n"
                "Available tools: TELL_USER, WRITE_FILE\n"
                "Tool format: <TOOL: TOOL_NAME>arguments</TOOL>\n"
                "End with <TASK_COMPLETED> when done."
            )
        super().__init__(manifesto=manifesto, memory=memory)

    def chunk_text(self, text: str) -> List[str]:
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
        chunks: List[str] = []
        current = ""
        for sent in sentences:
            if len(current) + len(sent) > self.chunk_size:
                if current:
                    chunks.append(current.strip())
                current = sent
            else:
                current += " " + sent
        if current:
            chunks.append(current.strip())
        return chunks if chunks else [text]


class CodeAgent(MetaAgent):
    """Agent untuk generating / reviewing code (mock)."""

    def __init__(self, manifesto: str = "", memory: str = ""):
        if not manifesto:
            manifesto = (
                "You are a code agent. You write, review, and refactor code.\n"
                "Available tools: WRITE_FILE, READ_FILE, TELL_USER\n"
                "Tool format: <TOOL: TOOL_NAME>arguments</TOOL>\n"
                "End with <TASK_COMPLETED> when done."
            )
        super().__init__(manifesto=manifesto, memory=memory)


# ---------------------------------------------------------------------------
# 8.  MAIN DEMO & TEST SUITE
# ---------------------------------------------------------------------------

def _test_streaming_logger() -> None:
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
        path = f.name
    try:
        logger = StreamingLogger(path)
        logger.write("Test line 1\n")
        logger.write("Test line 2\n")
        logger.close()
        with open(path, "r") as f:
            content = f.read()
        assert "Test line 1" in content
        assert "Test line 2" in content
        print("  [OK] StreamingLogger")
    finally:
        os.unlink(path)


def _test_variable_store() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        vs = VariableStore(tmpdir)
        vs.set("manifesto", "You are a test agent.")
        assert "manifesto" in vs
        assert vs.get("manifesto") == "You are a test agent."
        print("  [OK] VariableStore")


def _test_tool_registry() -> None:
    reg = ToolRegistry()
    reg.register("ECHO", lambda x: x)
    assert reg.get("ECHO") is not None
    assert "ECHO" in reg.list()
    reg.unregister("ECHO")
    assert reg.get("ECHO") is None
    print("  [OK] ToolRegistry")


def _test_meta_agent_loop() -> None:
    agent = MetaAgent(
        manifesto="You are a test agent. End with <TASK_COMPLETED>.",
        max_steps=5,
    )
    # Override LLM untuk deterministic response
    agent.llm_call = lambda p: "I am done. <TASK_COMPLETED>"
    result = agent.run("Test goal")
    assert "<TASK_COMPLETED>" in result
    assert agent.step_count <= 5
    print("  [OK] MetaAgent loop + end detection")


def _test_meta_agent_tool_detection() -> None:
    agent = MetaAgent(manifesto="Test")
    tool, args = agent.detect_tool("Please <TOOL: SEARCH>query</TOOL> now")
    assert tool == "SEARCH"
    assert args == "query"
    print("  [OK] Tool detection (XML)")


def _test_research_agent() -> None:
    agent = ResearchAgent()
    agent.llm_call = lambda p: "<TOOL: SEARCH>test</TOOL>"
    agent.run("Research test topic")
    assert agent.step_count >= 1
    print("  [OK] ResearchAgent")


def _test_summary_agent() -> None:
    agent = SummaryAgent()
    chunks = agent.chunk_text("First sentence. Second sentence. Third one here.")
    assert len(chunks) >= 1
    print("  [OK] SummaryAgent chunking")


def _test_code_agent() -> None:
    agent = CodeAgent()
    agent.llm_call = lambda p: "<TOOL: WRITE_FILE>test.txt|hello world</TOOL>"
    agent.run("Write test file")
    assert agent.step_count >= 1
    print("  [OK] CodeAgent")


def _test_agent_optimizer() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        vs = VariableStore(tmpdir)
        opt = AgentOptimizer(MetaAgent, vs)
        best = opt.optimize(
            base_manifesto="You are helpful.",
            test_goal="Say hello",
            variations=["You are helpful.", "You are super helpful!", "You are concise."],
            score_fn=lambda r: 1.0 if "hello" in r.lower() else 0.5,
        )
        assert "manifesto" in best
        print("  [OK] AgentOptimizer")


def _test_memory_tracing() -> None:
    agent = MetaAgent(
        manifesto="Test",
        memory_tracing=True,
        max_steps=3,
    )
    agent.llm_call = lambda p: "Response."
    agent.run("Goal")
    trace = agent.get_memory_trace()
    assert len(trace) >= 1
    print("  [OK] Memory tracing")


def _test_agent_factory_discover() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "research_agent"))
        os.makedirs(os.path.join(tmpdir, "code_agent"))
        agents = AgentFactory.discover_agents(tmpdir)
        names = [a[0] for a in agents]
        assert "research_agent" in names
        assert "code_agent" in names
        print("  [OK] AgentFactory.discover")


def _demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Meta Agent Framework — Native Demo")
    print("=" * 60)

    print("\n[Tests]")
    _test_streaming_logger()
    _test_variable_store()
    _test_tool_registry()
    _test_meta_agent_loop()
    _test_meta_agent_tool_detection()
    _test_research_agent()
    _test_summary_agent()
    _test_code_agent()
    _test_agent_optimizer()
    _test_memory_tracing()
    _test_agent_factory_discover()

    print("\n[Agent Execution Demo]")
    agent = MetaAgent(
        manifesto=(
            "You are a task completion agent.\n"
            "Available tools: SEARCH, TELL_USER, WRITE_FILE\n"
            "Use <TOOL: TOOL_NAME>args</TOOL> format.\n"
            "End with <TASK_COMPLETED>."
        ),
        max_steps=5,
    )
    # Simulated deterministic LLM
    responses = [
        "I will search for information. <TOOL: SEARCH>MAGNATRIX OS</TOOL>",
        "Found it. I will write a summary file. <TOOL: WRITE_FILE>summary.txt|MAGNATRIX-OS is an agentic OS.</TOOL>",
        "All tasks complete. <TASK_COMPLETED>",
    ]
    idx = [0]
    bridge = MockToUnifiedBridge()
    def _real_llm(p: str) -> str:
        try:
            return bridge.generate(p)
        except Exception:
            # Fallback to mock responses for demo
            r = responses[idx[0] % len(responses)]
            idx[0] += 1
            return r
    agent.llm_call = _real_llm

    result = agent.run("Research MAGNATRIX-OS")
    print(f"Steps: {agent.step_count}")
    print(f"Last tool: {agent._last_tool_called}")
    print(f"Memory trace length: {len(agent.get_memory_trace())}")

    print("\n" + "=" * 60)
    print("All tests passed. Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    _demo()
