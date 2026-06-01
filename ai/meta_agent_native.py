# meta_agent_native.py
# AMATI-PELAJARI-TIRU: matthiasgeihs/agent (Prompt-Driven Agent Optimization)
# XML tool protocol, JSON variable system, streaming logger, agent optimizer.
# Pure Python, standard library only.

from __future__ import annotations
import re, json, os, time, dataclasses, typing, hashlib, random
from typing import List, Dict, Optional, Callable, Any, Tuple

# ---------------------------------------------------------------------------
# Variable Store (JSON array prompt management)
# ---------------------------------------------------------------------------

class VariableStore:
    """All prompts stored as JSON arrays ["content"]."""

    def __init__(self, base_dir: str = "variables"):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def load(self, name: str) -> List[str]:
        path = os.path.join(self.base_dir, f"{name}.json")
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []

    def save(self, name: str, variables: List[str]):
        path = os.path.join(self.base_dir, f"{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(variables, f, indent=2, ensure_ascii=False)

    def append(self, name: str, variable: str):
        variables = self.load(name)
        variables.append(variable)
        self.save(name, variables)

    def list(self) -> List[str]:
        return [f.replace(".json", "") for f in os.listdir(self.base_dir) if f.endswith(".json")]

# ---------------------------------------------------------------------------
# Streaming Logger (dual output: stdout + file)
# ---------------------------------------------------------------------------

class StreamingLogger:
    def __init__(self, log_file: str = "agent.log"):
        self.log_file = log_file
        self._buffer = []

    def log(self, message: str, level: str = "INFO"):
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{level}] {message}"
        print(line)
        self._buffer.append(line)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def flush(self):
        self._buffer.clear()

# ---------------------------------------------------------------------------
# Tool Registry
# ---------------------------------------------------------------------------

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._register_defaults()

    def _register_defaults(self):
        self.register("ASK_USER", lambda question: f"User answered: {question}")
        self.register("TELL_USER", lambda message: f"Told user: {message}")
        self.register("SEARCH", lambda query: f"Search results for '{query}'")
        self.register("WRITE_FILE", lambda path, content: f"Written to {path}")
        self.register("READ_FILE", lambda path: f"Contents of {path}")

    def register(self, name: str, fn: Callable):
        self._tools[name] = fn

    def run(self, name: str, params: Dict[str, Any]) -> str:
        if name not in self._tools:
            return f"[Error: Unknown tool {name}]"
        try:
            return str(self._tools[name](**params))
        except Exception as e:
            return f"[Error: {e}]"

    def list(self) -> List[str]:
        return list(self._tools.keys())

# ---------------------------------------------------------------------------
# Mock LLM
# ---------------------------------------------------------------------------

class MockLLM:
    def generate(self, prompt: str, max_tokens: int = 256) -> str:
        if "ASK_USER" in prompt or "question" in prompt.lower():
            return "<ASK_USER>What is your preference?</ASK_USER>"
        if "SEARCH" in prompt or "find" in prompt.lower():
            return "<SEARCH>{\"query\": \"python best practices\"}</SEARCH>"
        if "WRITE_FILE" in prompt:
            return '<WRITE_FILE>{"path": "notes.txt", "content": "Summary of findings."}</WRITE_FILE>'
        return "<TELL_USER>Task completed successfully.</TELL_USER>"

# ---------------------------------------------------------------------------
# XML Tool Parser
# ---------------------------------------------------------------------------

class XMLToolParser:
    """Parse <TOOL: TOOL_NAME>args</TOOL> or <TOOL_NAME>args</TOOL_NAME>."""

    def parse(self, text: str) -> List[Tuple[str, str]]:
        results = []
        # Pattern 1: <TOOL: NAME>args</TOOL>
        pattern1 = re.findall(r'<TOOL:\s*(\w+)>\s*(.*?)\s*</TOOL>', text, re.DOTALL | re.IGNORECASE)
        for name, args in pattern1:
            results.append((name.upper(), args.strip()))
        # Pattern 2: <NAME>args</NAME>
        pattern2 = re.findall(r'<(\w+)>\s*(.*?)\s*</\1>', text, re.DOTALL | re.IGNORECASE)
        for name, args in pattern2:
            if name.upper() in ("SYSTEM", "USER", "ASSISTANT", "MANIFESTO", "CONTEXT", "TOOLS", "TOOL"):
                continue
            results.append((name.upper(), args.strip()))
        return results

    def parse_json_args(self, text: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"query": text}

# ---------------------------------------------------------------------------
# Memory Management (optional compression)
# ---------------------------------------------------------------------------

class MemoryManager:
    def __init__(self, compress: bool = False, max_entries: int = 100):
        self.compress = compress
        self.max_entries = max_entries
        self.entries: List[Dict[str, Any]] = []

    def add(self, role: str, content: str):
        self.entries.append({"role": role, "content": content, "timestamp": time.time()})
        if len(self.entries) > self.max_entries:
            self.entries.pop(0)
        if self.compress and len(self.entries) > 20:
            self._compress()

    def get(self, n: int = 10) -> List[Dict[str, Any]]:
        return self.entries[-n:]

    def to_prompt(self, n: int = 10) -> str:
        msgs = self.get(n)
        return "\n".join(f"[{m['role']}] {m['content']}" for m in msgs)

    def _compress(self):
        # Summarize oldest entries into a single compressed entry
        if len(self.entries) < 10:
            return
        oldest = self.entries[:10]
        summary = f"[Compressed {len(oldest)} older interactions]"
        self.entries = [{"role": "system", "content": summary, "timestamp": time.time()}] + self.entries[10:]

# ---------------------------------------------------------------------------
# Meta Agent Base Class
# ---------------------------------------------------------------------------

class MetaAgent:
    """Base class with manifesto + memory + tools loop."""

    def __init__(self, name: str, manifesto: str, tools: ToolRegistry,
                 end_detection: Optional[Callable] = None,
                 tool_detection: Optional[Callable] = None,
                 memory_mgmt: Optional[MemoryManager] = None,
                 llm: Optional[MockLLM] = None,
                 logger: Optional[StreamingLogger] = None):
        self.name = name
        self.manifesto = manifesto
        self.tools = tools
        self.end_detection = end_detection or self._default_end_detection
        self.tool_detection = tool_detection or self._default_tool_detection
        self.memory = memory_mgmt or MemoryManager()
        self.llm = llm or MockLLM()
        self.logger = logger or StreamingLogger()
        self.parser = XMLToolParser()

    def _default_end_detection(self, response: str) -> bool:
        return "</TELL_USER>" in response or "done" in response.lower()

    def _default_tool_detection(self, response: str) -> bool:
        return bool(re.search(r'<\w+>', response))

    def run(self, user_input: str, max_steps: int = 10) -> str:
        self.memory.add("user", user_input)
        self.logger.log(f"Agent {self.name} started with input: {user_input[:60]}...")
        for step in range(max_steps):
            context = self.memory.to_prompt()
            prompt = self._build_prompt(context, user_input)
            response = self.llm.generate(prompt, max_tokens=256)
            self.memory.add("assistant", response)
            self.logger.log(f"Step {step+1}: {response[:80]}...")
            if self.end_detection(response):
                self.logger.log("End detected. Stopping.")
                break
            if self.tool_detection(response):
                tools_found = self.parser.parse(response)
                for tool_name, raw_args in tools_found:
                    if tool_name.upper() in ("SYSTEM", "USER", "ASSISTANT"):
                        continue
                    args = self.parser.parse_json_args(raw_args)
                    result = self.tools.run(tool_name, args)
                    self.memory.add("system", f"Tool {tool_name} result: {result}")
                    self.logger.log(f"Executed {tool_name}: {result[:80]}...")
        # Return last assistant message
        for entry in reversed(self.memory.get()):
            if entry["role"] == "assistant":
                return entry["content"]
        return "[No response]"

    def _build_prompt(self, context: str, user_input: str) -> str:
        return (
            f"<manifesto>\n{self.manifesto}\n</manifesto>\n"
            f"<context>\n{context}\n</context>\n"
            f"<user>\n{user_input}\n</user>\n"
            f"<tools>\n{', '.join(self.tools.list())}\n</tools>\n"
            f"<assistant>\n"
        )

# ---------------------------------------------------------------------------
# Agent Optimizer (variation testing framework)
# ---------------------------------------------------------------------------

class AgentOptimizer:
    """Tries N prompt variations and scores results."""

    def __init__(self, llm: Optional[MockLLM] = None):
        self.llm = llm or MockLLM()
        self.variations: List[Dict[str, Any]] = []

    def create_variations(self, base_prompt: str, n: int = 3) -> List[str]:
        variations = [base_prompt]
        for i in range(1, n):
            # Simple variations: add style modifiers
            modifiers = [
                " Be concise.",
                " Provide detailed reasoning.",
                " Use bullet points.",
            ]
            variations.append(base_prompt + modifiers[i % len(modifiers)])
        return variations

    def score(self, response: str) -> float:
        # Simple scoring: length + completeness heuristics
        score = 0.0
        if len(response) > 20:
            score += 0.3
        if any(t in response for t in ["<", "{", "result", "answer"]):
            score += 0.3
        if len(response) < 500:
            score += 0.2
        # Penalize errors
        if "error" in response.lower():
            score -= 0.5
        return max(0.0, min(1.0, score))

    def optimize(self, base_prompt: str, n: int = 3) -> Tuple[str, float]:
        best = (base_prompt, 0.0)
        for var in self.create_variations(base_prompt, n):
            response = self.llm.generate(var, max_tokens=256)
            s = self.score(response)
            self.variations.append({"prompt": var, "response": response, "score": s})
            if s > best[1]:
                best = (var, s)
        return best

# ---------------------------------------------------------------------------
# Agent Factory (directory-based discovery)
# ---------------------------------------------------------------------------

class AgentFactory:
    """Discover agents from directory structure: agents/<name>/agent.py + variables/"""

    def __init__(self, base_dir: str = "agents"):
        self.base_dir = base_dir

    def discover(self) -> List[Dict[str, Any]]:
        agents = []
        if not os.path.isdir(self.base_dir):
            return agents
        for name in os.listdir(self.base_dir):
            agent_dir = os.path.join(self.base_dir, name)
            agent_file = os.path.join(agent_dir, "agent.py")
            if os.path.isdir(agent_dir) and os.path.exists(agent_file):
                vars_dir = os.path.join(agent_dir, "variables")
                variables = VariableStore(vars_dir).list() if os.path.isdir(vars_dir) else []
                agents.append({
                    "name": name,
                    "path": agent_file,
                    "variables": variables,
                })
        return agents

# ---------------------------------------------------------------------------
# Example Agents (subclasses)
# ---------------------------------------------------------------------------

class ResearchAgent(MetaAgent):
    def __init__(self, tools: Optional[ToolRegistry] = None, llm: Optional[MockLLM] = None):
        super().__init__(
            name="ResearchAgent",
            manifesto="You are a research agent. Use SEARCH to find information, then TELL_USER the summary.",
            tools=tools or ToolRegistry(),
            llm=llm
        )

class SummaryAgent(MetaAgent):
    def __init__(self, tools: Optional[ToolRegistry] = None, llm: Optional[MockLLM] = None):
        super().__init__(
            name="SummaryAgent",
            manifesto="You are a summary agent. READ_FILE then WRITE_FILE with a concise summary.",
            tools=tools or ToolRegistry(),
            llm=llm
        )

class CodeAgent(MetaAgent):
    def __init__(self, tools: Optional[ToolRegistry] = None, llm: Optional[MockLLM] = None):
        super().__init__(
            name="CodeAgent",
            manifesto="You are a code agent. SEARCH for best practices, then WRITE_FILE with code.",
            tools=tools or ToolRegistry(),
            llm=llm
        )

# ---------------------------------------------------------------------------
# Test Suite
# ---------------------------------------------------------------------------

def _test_variable_store():
    vs = VariableStore(base_dir="/tmp/test_variables")
    vs.save("test", ["hello", "world"])
    loaded = vs.load("test")
    assert loaded == ["hello", "world"]
    print("[PASS] variable store")

def _test_streaming_logger():
    logger = StreamingLogger(log_file="/tmp/test_agent.log")
    logger.log("Test message")
    assert os.path.exists("/tmp/test_agent.log")
    print("[PASS] streaming logger")

def _test_xml_tool_parser():
    parser = XMLToolParser()
    tools = parser.parse("<SEARCH>{\"query\": \"python\"}</SEARCH>")
    assert tools[0][0] == "SEARCH"
    tools2 = parser.parse("<TOOL: WRITE_FILE>{\"path\": \"a.txt\"}</TOOL>")
    assert tools2[0][0] == "WRITE_FILE"
    print("[PASS] xml tool parser")

def _test_memory_manager():
    mem = MemoryManager(compress=True, max_entries=5)
    for i in range(6):
        mem.add("user", f"msg {i}")
    assert len(mem.get()) <= 5
    print("[PASS] memory manager")

def _test_meta_agent():
    tools = ToolRegistry()
    agent = MetaAgent("Test", "Manifesto", tools)
    result = agent.run("Do research on Python", max_steps=3)
    assert result
    print("[PASS] meta agent")

def _test_agent_optimizer():
    opt = AgentOptimizer()
    best_prompt, score = opt.optimize("Summarize Python", n=3)
    assert score >= 0.0
    assert len(opt.variations) == 3
    print("[PASS] agent optimizer")

def _test_agent_factory():
    factory = AgentFactory(base_dir="/tmp/test_agents")
    os.makedirs("/tmp/test_agents/test_agent/variables", exist_ok=True)
    open("/tmp/test_agents/test_agent/agent.py", "w").write("# agent")
    agents = factory.discover()
    assert len(agents) >= 1
    print("[PASS] agent factory")

def _test_example_agents():
    ra = ResearchAgent()
    assert ra.name == "ResearchAgent"
    ca = CodeAgent()
    assert ca.name == "CodeAgent"
    print("[PASS] example agents")

if __name__ == "__main__":
    _test_variable_store()
    _test_streaming_logger()
    _test_xml_tool_parser()
    _test_memory_manager()
    _test_meta_agent()
    _test_agent_optimizer()
    _test_agent_factory()
    _test_example_agents()
    print("\n[OK] meta_agent_native.py — all 8 tests passed")
