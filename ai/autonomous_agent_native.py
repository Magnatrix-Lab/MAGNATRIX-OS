# autonomous_agent_native.py
# AMATI-PELAJARI-TIRU: AutoGPT / AgentGPT Pattern
# Goal-driven autonomy with task decomposition, tool ecosystem, memory, and self-critique.
# Pure Python, standard library only.

from __future__ import annotations
import json, re, math, time, dataclasses, typing, os, hashlib
from collections import deque
from typing import List, Dict, Optional, Callable, Any

# ---------------------------------------------------------------------------
# Task Data Structure
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class Task:
    id: str
    description: str
    status: str = "pending"  # pending, running, completed, failed
    result: str = ""
    priority: int = 5  # 1 = highest
    depends_on: List[str] = dataclasses.field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

# ---------------------------------------------------------------------------
# Mock LLM
# ---------------------------------------------------------------------------

class MockLLM:
    """Deterministic mock LLM for subtask generation and synthesis."""

    def generate(self, prompt: str, max_tokens: int = 256) -> str:
        if "decompose" in prompt.lower() or "subtask" in prompt.lower():
            # Extract goal and return 2-3 mock subtasks
            goal = prompt.split("\n")[0].replace("Goal:", "").strip()
            return json.dumps({
                "subtasks": [
                    {"description": f"Research {goal}", "priority": 1},
                    {"description": f"Analyze findings for {goal}", "priority": 2},
                    {"description": f"Synthesize final answer for {goal}", "priority": 3}
                ]
            })
        if "synthesize" in prompt.lower() or "final answer" in prompt.lower():
            return "Final synthesized answer based on completed subtasks."
        if "reflect" in prompt.lower() or "critique" in prompt.lower():
            return "Improvement suggestion: verify sources before synthesis."
        return "Mock LLM response."

    def parse_subtasks(self, raw: str) -> List[Dict[str, Any]]:
        try:
            data = json.loads(raw)
            return data.get("subtasks", [])
        except json.JSONDecodeError:
            # Fallback: parse simple numbered list
            lines = [l.strip() for l in raw.split("\n") if l.strip() and l[0].isdigit()]
            return [{"description": l, "priority": i+1} for i, l in enumerate(lines)]

# ---------------------------------------------------------------------------
# Goal Decomposer
# ---------------------------------------------------------------------------

class GoalDecomposer:
    def __init__(self, llm: Optional[MockLLM] = None):
        self.llm = llm or MockLLM()
        self._counter = 0

    def decompose(self, goal: str) -> List[Task]:
        prompt = f"Goal: {goal}\n\nDecompose this goal into prioritized subtasks. Return JSON with 'subtasks' array."
        raw = self.llm.generate(prompt, max_tokens=256)
        raw_subtasks = self.llm.parse_subtasks(raw)
        tasks = []
        for i, st in enumerate(raw_subtasks):
            self._counter += 1
            tasks.append(Task(
                id=f"t{self._counter}",
                description=st.get("description", "unnamed task"),
                priority=st.get("priority", i+1)
            ))
        # Add dependency chain
        for i in range(1, len(tasks)):
            tasks[i].depends_on.append(tasks[i-1].id)
        return tasks

# ---------------------------------------------------------------------------
# Tool Registry
# ---------------------------------------------------------------------------

class ToolRegistry:
    """Built-in tools: SEARCH, WRITE_FILE, READ_FILE, CALCULATE, HTTP_GET."""

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._register_defaults()

    def _register_defaults(self):
        self.register("SEARCH", self._search)
        self.register("WRITE_FILE", self._write_file)
        self.register("READ_FILE", self._read_file)
        self.register("CALCULATE", self._calculate)
        self.register("HTTP_GET", self._http_get)

    def register(self, name: str, fn: Callable):
        self._tools[name] = fn

    def run(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if name not in self._tools:
            return {"error": f"Tool {name} not found"}
        try:
            result = self._tools[name](**params)
            return {"tool": name, "result": result}
        except Exception as e:
            return {"tool": name, "error": str(e)}

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())

    @staticmethod
    def _search(query: str) -> str:
        return f"[Simulated search result for '{query}']"

    @staticmethod
    def _write_file(path: str, content: str) -> str:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Written {len(content)} bytes to {path}"

    @staticmethod
    def _read_file(path: str) -> str:
        if not os.path.exists(path):
            return f"File not found: {path}"
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def _calculate(expression: str) -> str:
        try:
            # SAFE evaluation: only allow numbers and operators
            allowed = set("0123456789.+-*/() ")
            if not all(c in allowed for c in expression):
                return "Invalid expression: only numbers and operators allowed"
            result = eval(expression, {"__builtins__": {}}, {})
            return str(result)
        except Exception as e:
            return f"Calculation error: {e}"

    @staticmethod
    def _http_get(url: str) -> str:
        return f"[Simulated HTTP GET to {url}: status=200, body='...']"

# ---------------------------------------------------------------------------
# Memory Manager
# ---------------------------------------------------------------------------

class MemoryManager:
    """Short-term (deque) + long-term (JSON file) memory."""

    def __init__(self, long_term_path: str = "agent_memory.json", max_short_term: int = 20):
        self.short_term: deque = deque(maxlen=max_short_term)
        self.long_term_path = long_term_path
        self.long_term: Dict[str, Any] = {}
        self._load_long_term()

    def add(self, role: str, content: str):
        entry = {"role": role, "content": content, "timestamp": time.time()}
        self.short_term.append(entry)
        self.long_term[f"entry_{len(self.long_term)}"] = entry
        self._save_long_term()

    def context(self, n: int = 10) -> List[Dict[str, Any]]:
        return list(self.short_term)[-n:]

    def retrieve(self, key: str) -> Optional[Any]:
        return self.long_term.get(key)

    def _load_long_term(self):
        if os.path.exists(self.long_term_path):
            try:
                with open(self.long_term_path, "r", encoding="utf-8") as f:
                    self.long_term = json.load(f)
            except json.JSONDecodeError:
                self.long_term = {}

    def _save_long_term(self):
        with open(self.long_term_path, "w", encoding="utf-8") as f:
            json.dump(self.long_term, f, indent=2, ensure_ascii=False)

    def clear(self):
        self.short_term.clear()
        self.long_term.clear()
        if os.path.exists(self.long_term_path):
            os.remove(self.long_term_path)

# ---------------------------------------------------------------------------
# Observer
# ---------------------------------------------------------------------------

class Observer:
    """Evaluates task result quality (success/failure/partial)."""

    def evaluate(self, task: Task, result: Dict[str, Any]) -> str:
        if "error" in result:
            return "failure"
        if not result.get("result"):
            return "partial"
        # Length heuristic: longer results = more complete
        res_text = str(result.get("result", ""))
        if len(res_text) < 10:
            return "partial"
        return "success"

    def score(self, task: Task, result: Dict[str, Any]) -> float:
        status = self.evaluate(task, result)
        scores = {"success": 1.0, "partial": 0.5, "failure": 0.0}
        return scores.get(status, 0.0)

# ---------------------------------------------------------------------------
# Self-Critique
# ---------------------------------------------------------------------------

class SelfCritique:
    def __init__(self, llm: Optional[MockLLM] = None):
        self.llm = llm or MockLLM()

    def reflect(self, history: List[Dict[str, Any]]) -> str:
        summary = json.dumps(history, indent=2)[:2000]
        prompt = (
            f"Execution history:\n{summary}\n\n"
            "Reflect on overall progress. Suggest improvements."
        )
        return self.llm.generate(prompt, max_tokens=128)

# ---------------------------------------------------------------------------
# Task Executor
# ---------------------------------------------------------------------------

class TaskExecutor:
    def __init__(self, tools: ToolRegistry, observer: Observer):
        self.tools = tools
        self.observer = observer

    def execute(self, task: Task) -> Dict[str, Any]:
        task.status = "running"
        # Determine which tool to use based on task description
        tool_name = self._select_tool(task.description)
        params = self._extract_params(task.description)
        result = self.tools.run(tool_name, params)
        task.status = self.observer.evaluate(task, result)
        task.result = str(result.get("result", result.get("error", "")))
        return result

    def _select_tool(self, description: str) -> str:
        d = description.lower()
        if "search" in d or "find" in d or "look up" in d:
            return "SEARCH"
        if "write" in d or "save" in d or "create file" in d:
            return "WRITE_FILE"
        if "read" in d or "load" in d or "open file" in d:
            return "READ_FILE"
        if "calculate" in d or "compute" in d or "math" in d:
            return "CALCULATE"
        if "http" in d or "get" in d or "fetch" in d or "url" in d:
            return "HTTP_GET"
        return "SEARCH"

    def _extract_params(self, description: str) -> Dict[str, Any]:
        # Very simple param extraction
        d = description.lower()
        if "calculate" in d:
            expr = re.search(r'[\d\+\-\*/\.\(\)]+', description)
            return {"expression": expr.group(0) if expr else "0"}
        if "write" in d or "save" in d:
            return {"path": "output.txt", "content": description}
        if "read" in d:
            return {"path": "input.txt"}
        if "http" in d:
            url = re.search(r'https?://\S+', description)
            return {"url": url.group(0) if url else "https://example.com"}
        return {"query": description}

# ---------------------------------------------------------------------------
# Autonomous Agent
# ---------------------------------------------------------------------------

class AutonomousAgent:
    """Orchestrates decompose -> execute -> observe -> critique -> replan."""

    def __init__(self, llm: Optional[MockLLM] = None, max_steps: int = 10):
        self.llm = llm or MockLLM()
        self.max_steps = max_steps
        self.decomposer = GoalDecomposer(self.llm)
        self.tools = ToolRegistry()
        self.observer = Observer()
        self.executor = TaskExecutor(self.tools, self.observer)
        self.memory = MemoryManager()
        self.critique = SelfCritique(self.llm)
        self.tasks: List[Task] = []

    def run(self, goal: str) -> Dict[str, Any]:
        self.memory.clear()
        self.memory.add("user", f"Goal: {goal}")
        self.tasks = self.decomposer.decompose(goal)
        self.memory.add("system", f"Decomposed into {len(self.tasks)} tasks")
        step = 0
        while step < self.max_steps:
            pending = [t for t in self.tasks if t.status == "pending"]
            if not pending:
                break
            task = self._pick_next_task(pending)
            self.memory.add("system", f"Executing {task.id}: {task.description}")
            result = self.executor.execute(task)
            self.memory.add("system", f"Result: {task.status} — {task.result}")
            if task.status == "failure":
                # Replan: add a recovery task
                recovery = Task(
                    id=f"recover_{task.id}",
                    description=f"Retry {task.description} with alternative approach",
                    priority=task.priority - 1,
                    depends_on=[]
                )
                self.tasks.append(recovery)
            step += 1
        final_answer = self._synthesize()
        reflection = self.critique.reflect(self.memory.context(20))
        return {
            "goal": goal,
            "tasks": [t.to_dict() for t in self.tasks],
            "final_answer": final_answer,
            "reflection": reflection,
            "steps_executed": step,
            "success_rate": self._success_rate(),
        }

    def _pick_next_task(self, pending: List[Task]) -> Task:
        # Sort by priority, then check dependencies
        pending.sort(key=lambda t: t.priority)
        completed_ids = {t.id for t in self.tasks if t.status in ("completed", "success", "partial")}
        for t in pending:
            if all(dep in completed_ids for dep in t.depends_on):
                return t
        return pending[0]

    def _synthesize(self) -> str:
        completed = [t for t in self.tasks if t.status in ("success", "partial", "completed")]
        context = "\n".join(f"- {t.description}: {t.result}" for t in completed)
        prompt = (
            f"Completed tasks:\n{context}\n\n"
            "Synthesize a final answer based on the task results."
        )
        return self.llm.generate(prompt, max_tokens=256)

    def _success_rate(self) -> float:
        if not self.tasks:
            return 0.0
        successes = sum(1 for t in self.tasks if t.status in ("success", "completed"))
        return successes / len(self.tasks)

# ---------------------------------------------------------------------------
# Test Suite
# ---------------------------------------------------------------------------

def _test_decomposer():
    d = GoalDecomposer()
    tasks = d.decompose("Build a Python web scraper")
    assert len(tasks) >= 2
    assert all(t.description for t in tasks)
    print("[PASS] goal decomposer")

def _test_tool_registry():
    reg = ToolRegistry()
    r = reg.run("CALCULATE", {"expression": "2 + 3 * 4"})
    assert r["result"] == "14"
    r2 = reg.run("SEARCH", {"query": "python"})
    assert "python" in r2["result"].lower()
    print("[PASS] tool registry")

def _test_memory():
    mem = MemoryManager(long_term_path="/tmp/test_agent_memory.json")
    mem.add("user", "hello")
    assert len(mem.context()) == 1
    mem.clear()
    print("[PASS] memory manager")

def _test_observer():
    obs = Observer()
    t = Task("t1", "test")
    assert obs.evaluate(t, {"result": "this is a long enough result text"}) == "success"
    assert obs.evaluate(t, {"error": "fail"}) == "failure"
    assert obs.evaluate(t, {"result": ""}) == "partial"
    print("[PASS] observer")

def _test_executor():
    exec_ = TaskExecutor(ToolRegistry(), Observer())
    t = Task("t1", "calculate 2+2")
    r = exec_.execute(t)
    assert t.status == "success" or t.status == "partial"
    print("[PASS] task executor")

def _test_autonomous_agent():
    agent = AutonomousAgent(max_steps=10)
    result = agent.run("Research Python async patterns")
    assert "final_answer" in result
    assert "tasks" in result
    assert result["success_rate"] >= 0.0
    print("[PASS] autonomous agent full loop")

if __name__ == "__main__":
    _test_decomposer()
    _test_tool_registry()
    _test_memory()
    _test_observer()
    _test_executor()
    _test_autonomous_agent()
    print("\n[OK] autonomous_agent_native.py — all 6 tests passed")
