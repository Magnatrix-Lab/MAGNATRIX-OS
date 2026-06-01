# ai/modular_agent_native.py
# AMATI-PELAJARI-TIRU: Pattern extracted from matthiasgeihs/agent
# https://github.com/matthiasgeihs/agent
# Modular agent framework with dynamic class loading, variable optimization, streaming logger
# Native reimplementation for MAGNATRIX-OS Layer 10 (AI) + Layer 6 (Skills)

"""
Native Modular Agent Framework
================================
Inspired by matthiasgeihs/agent architecture:
  - Agent base class with manifesto, memory, tools, and LLM loop
  - Dynamic agent class loading from directory structure
  - Variable optimization: A/B test different variable sets per agent
  - Streaming logger: writes to both file and stdout in real-time
  - Agent runner with timestamped run folders
  - Tool detection, end detection, and memory management hooks

Features:
  - Pure-Python agent framework without external LLM dependencies
  - Pluggable LLM, tool detection, end detection, memory management
  - Agent directory scanner and loader
  - Variable variation loader from JSON
  - Run folder creation with debug.log + results.json
"""

from __future__ import annotations

import os
import sys
import json
import datetime
import inspect
import importlib.util
from typing import Dict, Any, TextIO, Type, List, Tuple, Optional, Callable


class StreamingLogger:
    """Logger that writes to both file and stdout in real-time."""

    def __init__(self, log_file: TextIO):
        self.terminal = sys.stdout
        self.log_file = log_file

    def write(self, message: str) -> None:
        self.terminal.write(message)
        self.log_file.write(message)
        self.terminal.flush()
        self.log_file.flush()

    def flush(self) -> None:
        self.terminal.flush()
        self.log_file.flush()


class AgentMeta(type):
    """Metaclass that auto-registers agents."""

    registry: Dict[str, Type["Agent"]] = {}

    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)
        if name != "Agent" and hasattr(cls, "run"):
            AgentMeta.registry[name] = cls
        return cls


class Agent(metaclass=AgentMeta):
    """
    Flexible agent base class.
    Manages conversations with an LLM while handling tool calls and memory.
    """

    def __init__(
        self,
        model_name: str = "mock",
        manifesto: str = "You are a helpful agent.",
        memory: str = "",
        tools: Optional[Dict[str, Callable]] = None,
        end_detection: Optional[Callable[[str, str], bool]] = None,
        tool_detection: Optional[Callable[[str], Tuple[Optional[str], Optional[str]]]] = None,
        memory_management: Optional[Callable[[str], Optional[str]]] = None,
        memory_tracing: bool = False,
    ):
        self.log_handler: Callable[[str], None] = lambda msg: print(msg)
        self.debug_verbose = False
        self.model_name = model_name
        self.manifesto = manifesto
        self.memory = memory
        self._ask_user_impl: Callable[[str], str] = lambda q: input(q + "\nYour response: ")
        self._tell_user_impl: Callable[[str], None] = lambda m: self.log_handler(m)

        self.tools = {
            "ASK_USER": self.ask_user,
            "TELL_USER": self.tell_user,
            **(tools or {})
        }
        self.end_detection_fn = end_detection
        self.tool_detection_fn = tool_detection
        self.memory_management_fn = memory_management
        self._memory_trace: List[str] = []
        self._last_tool_called: Optional[str] = None
        self.memory_tracing = memory_tracing

    def get_memory_trace(self) -> List[str]:
        return self._memory_trace

    def override_log_handler(self, new_impl: Callable[[str], None]) -> None:
        self.log_handler = new_impl

    def update_memory(self, text: str) -> None:
        if self.memory_tracing:
            self._memory_trace.append(self.memory)
        if callable(self.memory_management_fn):
            updated = self.memory_management_fn(text)
            if updated is not None:
                self.memory = updated
        else:
            self.memory = text

    def compose_request(self) -> str:
        return self.manifesto + "\n" + self.memory

    def run(self) -> str:
        while True:
            self._last_tool_called = None
            response = self.llm_call(self.compose_request())
            self.update_memory(self.memory + "\n" + self.__class__.__name__ + ": " + response)

            tool_name, tool_args = self._detect_tool(response)
            if tool_name and tool_name in self.tools:
                self._last_tool_called = tool_name
                result = self.tools[tool_name](tool_args)
                self.update_memory(self.memory + "\nTool Result: " + str(result))
            elif tool_name:
                self.update_memory(self.memory + "\nTool Not Found: " + tool_name)

            if self._check_end():
                break
        return self.memory

    def llm_call(self, prompt: str, **kwargs: Any) -> str:
        # Pluggable LLM call
        return f"[LLM] {prompt[:80]}..."

    def _detect_tool(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        if not self.tool_detection_fn:
            return None, None
        return self.tool_detection_fn(text)

    def _check_end(self) -> bool:
        if callable(self.end_detection_fn):
            return self.end_detection_fn(self.manifesto, self.memory)
        return self._last_tool_called is None

    def ask_user(self, question: str) -> str:
        return self._ask_user_impl(question)

    def tell_user(self, message: str) -> None:
        self._tell_user_impl(message)


class AgentLoader:
    """Dynamically load agent classes from directory structure."""

    def __init__(self, agents_dir: str = "agents"):
        self.agents_dir = agents_dir

    def get_available_agents(self) -> List[Tuple[str, Optional[str]]]:
        agents = []
        if not os.path.isdir(self.agents_dir):
            return agents
        for item in sorted(os.listdir(self.agents_dir)):
            path = os.path.join(self.agents_dir, item)
            if os.path.isdir(path) and not item.startswith("__"):
                agent_class = self._get_agent_class(item)
                description = agent_class.__doc__ if agent_class else None
                agents.append((item, description))
        return agents

    def _get_agent_class(self, agent_name: str) -> Optional[Type[Agent]]:
        try:
            module = importlib.import_module(f"agents.{agent_name}.agent")
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and name.endswith("Agent") and obj.__module__ == module.__name__:
                    return obj
        except Exception:
            return None
        return None

    def load_agent(self, agent_name: str, variables: Dict[str, Any]) -> Agent:
        cls = self._get_agent_class(agent_name)
        if not cls:
            raise ValueError(f"Agent class not found for {agent_name}")
        return cls(**variables)


class VariableOptimizer:
    """Load variable variations from JSON and run A/B optimization."""

    def __init__(self, var_dir: str):
        self.var_dir = var_dir

    def load_all_variations(self) -> Tuple[List[Dict[str, str]], int]:
        variations: Dict[str, List[str]] = {}
        num_variations = None
        for filename in os.listdir(self.var_dir):
            if filename.endswith(".json"):
                var_name = filename[:-5]
                with open(os.path.join(self.var_dir, filename)) as f:
                    var_list = json.load(f)
                    variations[var_name] = var_list
                    if num_variations is None:
                        num_variations = len(var_list)
                    elif len(var_list) != num_variations:
                        raise ValueError(f"Mismatched variations in {filename}")
        if not num_variations:
            raise ValueError("No variations found")
        combos = []
        for i in range(num_variations):
            combo = {name: variations[name][i] for name in variations}
            combos.append(combo)
        return combos, num_variations

    def optimize(self, agent_class: Type[Agent], agent_name: str) -> Tuple[Dict[str, str], Any]:
        var_dir = os.path.join("agents", agent_name, "variables")
        if not os.path.isdir(var_dir):
            return {}, None
        combos, num = self.load_all_variations()
        best_result = None
        best_combo = {}
        for i, combo in enumerate(combos):
            agent = agent_class(**combo)
            result = agent.run()
            if best_result is None or len(result) > len(best_result):
                best_result = result
                best_combo = combo
        return best_combo, best_result


class AgentRunner:
    """Run agent with timestamped folder and logging."""

    def __init__(self, agents_dir: str = "agents"):
        self.agents_dir = agents_dir

    def create_run_folder(self, agent_name: str) -> str:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = os.path.join(self.agents_dir, agent_name, "logs", f"run_{timestamp}")
        os.makedirs(run_dir, exist_ok=True)
        return run_dir

    def run_with_logging(self, agent_class: Type[Agent], variables: Dict[str, Any], agent_name: str) -> Any:
        run_dir = self.create_run_folder(agent_name)
        with open(os.path.join(run_dir, "debug.log"), "w") as log_file:
            old_stdout = sys.stdout
            sys.stdout = StreamingLogger(log_file)
            try:
                agent = agent_class(**variables)
                result = agent.run()
                with open(os.path.join(run_dir, "results.json"), "w") as f:
                    json.dump({"result": result}, f, indent=2)
                return result
            finally:
                sys.stdout = old_stdout


# --- Standalone test ---
if __name__ == "__main__":
    agent = Agent(
        manifesto="You are a test agent. End when you see 'DONE'.",
        end_detection=lambda manifesto, memory: "DONE" in memory.upper(),
        tool_detection=lambda text: ("TELL_USER", text) if "hello" in text.lower() else (None, None),
    )
    # Simulate LLM
    agent.llm_call = lambda prompt: "hello world DONE"
    result = agent.run()
    print("Agent memory trace:", agent.get_memory_trace())
    print("Final result:", result[:200])
