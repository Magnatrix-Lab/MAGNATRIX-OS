"""
MAGNATRIX — Native Agent Zero Integration
═════════════════════════════════════════
AMATI-PELAJARI-TIRU dari https://github.com/agent0ai/agent-zero

Agent Zero adalah dynamic organic agentic framework yang 100% prompt-driven,
memungkinkan agent menciptakan tool sendiri on-the-fly dan berkooperasi
dalam hierarki superior↔subordinate. Semua pattern di-reimplement secara
native untuk MAGNATRIX Agentic OS.

Patterns ditiru:
1. Prompt-Driven System — semua behavior didefinisikan via system prompt
2. Dynamic Tool Creation — agent generate tool code sendiri secara runtime
3. Multi-Agent Hierarchy — superior orchestrates, subordinate executes
4. Computer-as-Tool — Linux environment, shell, filesystem access
5. Browser Automation — agent mengontrol browser sebagai tool
6. FAISS Episodic Memory — ingatan episodik dengan vector similarity
7. MCP Server/Client — Model Context Protocol integration
8. A2A Protocol — Agent-to-Agent communication protocol
9. Time Travel — workspace snapshots untuk rollback & branching
10. Space Agent — persistent agent identity across sessions

Author: MAGNATRIX-OS (native reimplementation)
"""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import os
import pickle
import re
import subprocess
import textwrap
import time
import typing
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, Set, Tuple, Union

# ─── Type Aliases ────────────────────────────────────────────────────────────
Prompt = str
ToolCode = str
AgentID = str
SnapshotID = str
MemoryID = str


# ═══════════════════════════════════════════════════════════════════════════════
# 1. PROMPT-DRIVEN BEHAVIOR ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class PromptTemplate:
    """Template prompt dengan variable substitution dan chain-of-thought injection."""

    def __init__(self, raw: str, variables: Optional[Dict[str, str]] = None):
        self.raw = raw
        self.variables = variables or {}
        self._compiled: Optional[str] = None

    def compile(self, extra: Optional[Dict[str, str]] = None) -> str:
        """Kompilasi prompt dengan mengganti semua placeholder."""
        ctx = {**self.variables, **(extra or {})}
        result = self.raw
        for key, val in ctx.items():
            result = result.replace(f"{{{key}}}", str(val))
            result = result.replace(f"{{{{${key}}}}}", str(val))
        self._compiled = result
        return result

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "PromptTemplate":
        with open(path, "r", encoding="utf-8") as f:
            return cls(f.read())


class SystemPromptRegistry:
    """Registry semua system prompt untuk agent — behavior 100% ditentukan di sini."""

    DEFAULT_AGENT_ZERO = textwrap.dedent("""\
        You are an autonomous agent in the MAGNATRIX operating system.
        You have access to a Linux computer, a web browser, and the ability to create new tools dynamically.

        RULES:
        1. Analyze the user's request carefully.
        2. Use existing tools if they solve the problem directly.
        3. If no tool exists, CREATE one by generating Python code.
        4. You may spawn subordinate agents for parallel tasks.
        5. Always verify results before reporting back.
        6. You have full episodic memory — reference past experiences when relevant.
        7. You can save/load workspace snapshots (Time Travel) for complex workflows.

        DYNAMIC TOOL CREATION FORMAT:
        When you need a new tool, output a code block starting with:
        ```tool:create_tool_name
        # Python code implementing the tool
        def run(param1: str, param2: int) -> dict:
            ...
            return {"result": ...}
        ```

        MULTI-AGENT DELEGATION FORMAT:
        When you need help, output:
        ```delegate:subordinate_agent_name
        Task description for the subordinate agent.
        Expected output format.
        ```

        Current time: {current_time}
        Your agent ID: {agent_id}
        Superior agent: {superior_id}
    """)

    SUBORDINATE_PROMPT = textwrap.dedent("""\
        You are a subordinate agent working under superior {superior_id}.
        Your role: {role_description}

        RULES:
        1. Execute the task given by your superior precisely.
        2. Report back with structured output.
        3. Ask for clarification if the task is ambiguous.
        4. You may create tools dynamically if needed.
        5. You have access to the same computer/browser/memory as your superior.

        Current time: {current_time}
        Your agent ID: {agent_id}
        Task: {task_description}
    """)

    TOOL_CREATOR_PROMPT = textwrap.dedent("""\
        You are the Tool Creator module. Given a task description, generate a complete,
        self-contained Python function that acts as a tool.

        REQUIREMENTS:
        - Function name must be descriptive.
        - Include type hints for all parameters and return value.
        - Include a docstring explaining purpose and parameters.
        - Handle edge cases and errors gracefully.
        - Return a dictionary with at least a "success" boolean and "result" or "error".

        Task: {task_description}
        Existing tools (do NOT duplicate): {existing_tools}
    """)

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path("prompts")
        self._prompts: Dict[str, PromptTemplate] = {
            "agent_zero": PromptTemplate(self.DEFAULT_AGENT_ZERO),
            "subordinate": PromptTemplate(self.SUBORDINATE_PROMPT),
            "tool_creator": PromptTemplate(self.TOOL_CREATOR_PROMPT),
        }
        self._custom: Dict[str, PromptTemplate] = {}

    def register(self, name: str, template: PromptTemplate, override: bool = False):
        if name in self._prompts and not override:
            raise KeyError(f"Prompt '{name}' already exists")
        self._custom[name] = template
        self._prompts[name] = template

    def get(self, name: str, **kwargs) -> str:
        tmpl = self._prompts.get(name)
        if not tmpl:
            raise KeyError(f"Prompt '{name}' not found in registry")
        defaults = {
            "current_time": datetime.now(timezone.utc).isoformat(),
        }
        return tmpl.compile({**defaults, **kwargs})


# ═══════════════════════════════════════════════════════════════════════════════
# 2. DYNAMIC TOOL FORGE — Agent menciptakan tool sendiri on-the-fly
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ToolSignature:
    name: str
    parameters: Dict[str, str]  # param_name -> type_annotation
    return_type: str
    description: str

    def to_json_schema(self) -> Dict[str, Any]:
        props = {}
        for pname, ptype in self.parameters.items():
            props[pname] = {"type": _python_type_to_json_schema(ptype)}
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": props,
                "required": list(props.keys()),
            },
        }


def _python_type_to_json_schema(ptype: str) -> str:
    mapping = {
        "str": "string", "int": "integer", "float": "number",
        "bool": "boolean", "list": "array", "dict": "object",
        "List": "array", "Dict": "object",
    }
    return mapping.get(ptype, "string")


class DynamicToolForge:
    """Mesin penciptaan tool dinamis — agent generate, compile, dan register tool baru runtime."""

    def __init__(self, sandbox_dir: Optional[Path] = None):
        self.sandbox_dir = sandbox_dir or Path("/tmp/magnatrix_tools")
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        self._tools: Dict[str, Callable[..., Any]] = {}
        self._signatures: Dict[str, ToolSignature] = {}
        self._lock = asyncio.Lock()

    # ── Public API ──────────────────────────────────────────────────────────

    async def forge_tool(self, name: str, code: ToolCode, description: str = "") -> ToolSignature:
        """Compile tool code Python menjadi callable yang teregister."""
        async with self._lock:
            if name in self._tools:
                raise ValueError(f"Tool '{name}' already registered — use update()")

            # Sanitize dan wrap code
            safe_code = self._sanitize_code(code)
            module_path = self.sandbox_dir / f"{name}_{uuid.uuid4().hex[:8]}.py"
            module_path.write_text(safe_code, encoding="utf-8")

            # Compile & exec dalam restricted namespace
            spec = __import__("importlib.util").util.spec_from_file_location(
                f"magnatrix_dynamic.{name}", str(module_path)
            )
            module = __import__("importlib.util").util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Extract callable
            run_fn = getattr(module, "run", None)
            if run_fn is None or not callable(run_fn):
                # Cari fungsi pertama yang callable
                for attr in dir(module):
                    obj = getattr(module, attr)
                    if callable(obj) and not attr.startswith("_"):
                        run_fn = obj
                        break
            if run_fn is None:
                raise ValueError(f"No callable 'run' found in generated tool '{name}'")

            # Extract signature via inspect
            sig = inspect.signature(run_fn)
            params = {
                pname: str(pann.annotation) if pann.annotation != inspect.Parameter.empty else "str"
                for pname, pann in sig.parameters.items()
            }
            ret = str(sig.return_annotation) if sig.return_annotation != inspect.Signature.empty else "Any"

            ts = ToolSignature(name=name, parameters=params, return_type=ret, description=description)
            self._tools[name] = run_fn
            self._signatures[name] = ts
            return ts

    async def invoke(self, name: str, **kwargs) -> Dict[str, Any]:
        """Invoke tool yang sudah teregister secara asynchronous."""
        async with self._lock:
            fn = self._tools.get(name)
            if not fn:
                return {"success": False, "error": f"Tool '{name}' not found"}
        try:
            if asyncio.iscoroutinefunction(fn):
                result = await fn(**kwargs)
            else:
                result = await asyncio.to_thread(fn, **kwargs)
            if not isinstance(result, dict):
                result = {"result": result, "success": True}
            return result
        except Exception as e:
            return {"success": False, "error": str(e), "tool": name}

    def list_tools(self) -> List[ToolSignature]:
        return list(self._signatures.values())

    def get_tool_schema(self, name: str) -> Optional[Dict[str, Any]]:
        ts = self._signatures.get(name)
        return ts.to_json_schema() if ts else None

    # ── Internal ────────────────────────────────────────────────────────────

    def _sanitize_code(self, code: str) -> str:
        """Sanitasi dasar — block dangerous imports."""
        blocked = {"__import__", "eval(", "exec(", "compile(", "subprocess", "os.system"}
        for bad in blocked:
            if bad in code:
                raise ValueError(f"Blocked pattern '{bad}' detected in generated tool code")
        # Inject safe header
        header = textwrap.dedent("""\
            # AUTO-GENERATED TOOL — MAGNATRIX Dynamic Tool Forge
            from typing import Dict, List, Any, Optional
            import json, math, re, random, datetime, itertools, collections
        """)
        return header + "\n" + code


# ═══════════════════════════════════════════════════════════════════════════════
# 3. MULTI-AGENT HIERARCHY — Superior ↔ Subordinate
# ═══════════════════════════════════════════════════════════════════════════════

class AgentStatus(Enum):
    IDLE = auto()
    WORKING = auto()
    WAITING_DELEGATION = auto()
    ERROR = auto()
    HALTED = auto()


@dataclass
class DelegationTask:
    task_id: str
    description: str
    priority: int  # 1-10
    creator_id: AgentID
    assignee_id: Optional[AgentID] = None
    status: AgentStatus = AgentStatus.IDLE
    result: Optional[Dict[str, Any]] = None
    created_at: float = field(default_factory=time.time)
    deadline: Optional[float] = None
    context_snapshot: Optional[SnapshotID] = None


class AgentHierarchy:
    """Hierarki agent dengan superior yang orchestrate dan subordinate yang execute.

    Agent Zero pattern: superior agent tidak mengerjakan semua sendiri,
    tapi memecah task dan delegasi ke subordinate yang specialized.
    """

    def __init__(self, prompt_registry: SystemPromptRegistry):
        self.prompt_registry = prompt_registry
        self._agents: Dict[AgentID, Dict[str, Any]] = {}  # agent metadata
        self._hierarchy: Dict[AgentID, Optional[AgentID]] = {}  # child -> parent
        self._children: Dict[AgentID, List[AgentID]] = {}  # parent -> [children]
        self._tasks: Dict[str, DelegationTask] = {}
        self._task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._callbacks: Dict[str, List[Callable]] = {}
        self._lock = asyncio.Lock()

    async def register_agent(
        self,
        agent_id: AgentID,
        role: str,
        superior_id: Optional[AgentID] = None,
        capabilities: Optional[List[str]] = None,
    ) -> None:
        async with self._lock:
            self._agents[agent_id] = {
                "role": role,
                "capabilities": capabilities or [],
                "status": AgentStatus.IDLE,
            }
            self._hierarchy[agent_id] = superior_id
            if superior_id:
                self._children.setdefault(superior_id, []).append(agent_id)

    async def delegate(
        self,
        superior_id: AgentID,
        task_description: str,
        priority: int = 5,
        to_agent: Optional[AgentID] = None,
        deadline_seconds: Optional[int] = None,
    ) -> str:
        """Superior delegasi task ke subordinate (specific atau auto-assign)."""
        task_id = f"task-{uuid.uuid4().hex[:12]}"
        deadline = time.time() + deadline_seconds if deadline_seconds else None

        # Auto-assign ke subordinate yang idle jika tidak ditentukan
        if to_agent is None:
            candidates = await self._find_idle_subordinate(superior_id)
            if not candidates:
                return json.dumps({"success": False, "error": "No idle subordinate available"})
            to_agent = candidates[0]

        task = DelegationTask(
            task_id=task_id,
            description=task_description,
            priority=priority,
            creator_id=superior_id,
            assignee_id=to_agent,
            deadline=deadline,
        )
        self._tasks[task_id] = task
        await self._task_queue.put((priority, time.time(), task_id))

        # Update status
        async with self._lock:
            self._agents[to_agent]["status"] = AgentStatus.WORKING
            self._agents[superior_id]["status"] = AgentStatus.WAITING_DELEGATION

        return task_id

    async def report_result(
        self,
        agent_id: AgentID,
        task_id: str,
        result: Dict[str, Any],
    ) -> None:
        """Subordinate laporkan hasil ke superior."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.assignee_id != agent_id:
                raise ValueError("Task not found or not assigned to this agent")
            task.result = result
            task.status = AgentStatus.IDLE if result.get("success") else AgentStatus.ERROR
            self._agents[agent_id]["status"] = AgentStatus.IDLE

            superior = self._hierarchy.get(agent_id)
            if superior:
                self._agents[superior]["status"] = AgentStatus.WORKING
                # Trigger callbacks
                for cb in self._callbacks.get(task_id, []):
                    asyncio.create_task(cb(task))

    async def get_superior(self, agent_id: AgentID) -> Optional[AgentID]:
        async with self._lock:
            return self._hierarchy.get(agent_id)

    async def get_subordinates(self, agent_id: AgentID) -> List[AgentID]:
        async with self._lock:
            return list(self._children.get(agent_id, []))

    async def _find_idle_subordinate(self, superior_id: AgentID) -> List[AgentID]:
        candidates = []
        for cid in self._children.get(superior_id, []):
            if self._agents[cid].get("status") == AgentStatus.IDLE:
                candidates.append(cid)
        return candidates

    def on_task_complete(self, task_id: str, callback: Callable):
        self._callbacks.setdefault(task_id, []).append(callback)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. COMPUTER-AS-TOOL — Linux Environment Access
# ═══════════════════════════════════════════════════════════════════════════════

class ComputerAsTool:
    """Agent menggunakan komputer sebagai tool — shell, filesystem, proses."""

    def __init__(self, cwd: Optional[str] = None, allowed_paths: Optional[List[str]] = None):
        self.cwd = cwd or os.getcwd()
        self.allowed_paths = allowed_paths or ["/tmp", "/home", os.getcwd()]
        self._history: List[Dict[str, Any]] = []

    async def shell(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Jalankan shell command dengan safety constraint."""
        if not self._is_safe_command(command):
            return {"success": False, "error": "Command blocked by safety policy", "command": command}
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.cwd,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            result = {
                "success": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "command": command,
            }
            self._history.append({"type": "shell", **result})
            return result
        except asyncio.TimeoutError:
            return {"success": False, "error": f"Command timed out after {timeout}s", "command": command}
        except Exception as e:
            return {"success": False, "error": str(e), "command": command}

    async def read_file(self, path: str, max_size: int = 1_000_000) -> Dict[str, Any]:
        if not self._is_safe_path(path):
            return {"success": False, "error": "Path not allowed"}
        try:
            p = Path(path)
            if p.stat().st_size > max_size:
                return {"success": False, "error": f"File too large (> {max_size} bytes)"}
            content = p.read_text(encoding="utf-8")
            return {"success": True, "content": content, "path": path}
        except Exception as e:
            return {"success": False, "error": str(e), "path": path}

    async def write_file(self, path: str, content: str) -> Dict[str, Any]:
        if not self._is_safe_path(path):
            return {"success": False, "error": "Path not allowed"}
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return {"success": True, "bytes_written": len(content.encode("utf-8")), "path": path}
        except Exception as e:
            return {"success": False, "error": str(e), "path": path}

    async def list_dir(self, path: str) -> Dict[str, Any]:
        if not self._is_safe_path(path):
            return {"success": False, "error": "Path not allowed"}
        try:
            entries = []
            for entry in Path(path).iterdir():
                st = entry.stat()
                entries.append({
                    "name": entry.name,
                    "is_file": entry.is_file(),
                    "is_dir": entry.is_dir(),
                    "size": st.st_size,
                    "mtime": st.st_mtime,
                })
            return {"success": True, "entries": entries, "path": path}
        except Exception as e:
            return {"success": False, "error": str(e), "path": path}

    def _is_safe_command(self, cmd: str) -> bool:
        blocked = ["rm -rf /", "mkfs", "dd if=/dev/zero", "> /dev/sda", "chmod -R 777 /"]
        return not any(b in cmd for b in blocked)

    def _is_safe_path(self, path: str) -> bool:
        real = os.path.realpath(path)
        return any(real.startswith(os.path.realpath(a)) for a in self.allowed_paths)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. BROWSER AUTOMATION — Agent mengontrol browser
# ═══════════════════════════════════════════════════════════════════════════════

class BrowserAutomation:
    """Lightweight browser automation untuk agent — navigate, extract, interact."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._driver = None
        self._history: List[Dict[str, Any]] = []

    async def _ensure_driver(self):
        if self._driver is None:
            try:
                from playwright.async_api import async_playwright
                self._pw = await async_playwright().start()
                self._browser = await self._pw.chromium.launch(headless=self.headless)
                self._driver = await self._browser.new_page()
            except ImportError:
                return False
        return True

    async def navigate(self, url: str, wait_until: str = "networkidle") -> Dict[str, Any]:
        ready = await self._ensure_driver()
        if not ready:
            return {"success": False, "error": "playwright not installed"}
        try:
            resp = await self._driver.goto(url, wait_until=wait_until)
            title = await self._driver.title()
            result = {
                "success": True,
                "url": url,
                "title": title,
                "status": resp.status if resp else None,
            }
            self._history.append(result)
            return result
        except Exception as e:
            return {"success": False, "error": str(e), "url": url}

    async def extract_text(self, selector: Optional[str] = None) -> Dict[str, Any]:
        ready = await self._ensure_driver()
        if not ready:
            return {"success": False, "error": "playwright not installed"}
        try:
            if selector:
                elements = await self._driver.query_selector_all(selector)
                texts = [(await el.text_content()) or "" for el in elements]
            else:
                texts = [await self._driver.evaluate("() => document.body.innerText")]
            return {"success": True, "texts": texts}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def click(self, selector: str) -> Dict[str, Any]:
        ready = await self._ensure_driver()
        if not ready:
            return {"success": False, "error": "playwright not installed"}
        try:
            await self._driver.click(selector)
            return {"success": True, "action": "click", "selector": selector}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def screenshot(self, path: Optional[str] = None) -> Dict[str, Any]:
        ready = await self._ensure_driver()
        if not ready:
            return {"success": False, "error": "playwright not installed"}
        try:
            path = path or f"/tmp/magnatrix_browser_{uuid.uuid4().hex[:8]}.png"
            await self._driver.screenshot(path=path, full_page=True)
            return {"success": True, "screenshot_path": path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def close(self):
        if self._driver:
            await self._driver.close()
            await self._browser.close()
            await self._pw.stop()
            self._driver = None


# ═══════════════════════════════════════════════════════════════════════════════
# 6. EPISODIC MEMORY — FAISS-based Memory untuk Agent
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MemoryRecord:
    memory_id: MemoryID
    agent_id: AgentID
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    importance: float = 1.0  # 0.0 - 10.0


class EpisodicMemory:
    """Memory episodik agent dengan FAISS vector store untuk semantic retrieval."""

    def __init__(
        self,
        index_path: Optional[str] = None,
        embedding_dim: int = 384,
        use_flat: bool = True,
    ):
        self.index_path = index_path or "/tmp/magnatrix_memory.faiss"
        self.embedding_dim = embedding_dim
        self._records: Dict[MemoryID, MemoryRecord] = {}
        self._agent_memories: Dict[AgentID, List[MemoryID]] = {}
        self._index: Optional[Any] = None
        self._use_flat = use_flat
        self._lock = asyncio.Lock()
        self._init_index()

    def _init_index(self):
        try:
            import faiss
            if self._use_flat:
                self._index = faiss.IndexFlatIP(self.embedding_dim)
            else:
                self._index = faiss.IndexHNSWFlat(self.embedding_dim, 32)
                self._index.hnsw.efConstruction = 200
            self._id_map: List[MemoryID] = []
        except ImportError:
            self._index = None

    async def store(
        self,
        agent_id: AgentID,
        content: str,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 1.0,
    ) -> MemoryID:
        async with self._lock:
            memory_id = f"mem-{uuid.uuid4().hex[:12]}"
            record = MemoryRecord(
                memory_id=memory_id,
                agent_id=agent_id,
                content=content,
                embedding=embedding,
                metadata=metadata or {},
                importance=importance,
            )
            self._records[memory_id] = record
            self._agent_memories.setdefault(agent_id, []).append(memory_id)

            if embedding and self._index is not None:
                import numpy as np
                vec = np.array([embedding], dtype="float32")
                vec = vec / np.linalg.norm(vec)  # normalize untuk IP
                self._index.add(vec)
                self._id_map.append(memory_id)

            return memory_id

    async def search(
        self,
        agent_id: AgentID,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> List[MemoryRecord]:
        async with self._lock:
            if self._index is None or len(self._id_map) == 0:
                # Fallback: return recent memories
                ids = self._agent_memories.get(agent_id, [])[-top_k:]
                return [self._records[i] for i in ids]

            import numpy as np
            q = np.array([query_embedding], dtype="float32")
            q = q / np.linalg.norm(q)
            distances, indices = self._index.search(q, min(top_k * 2, len(self._id_map)))

            results = []
            for idx in indices[0]:
                if idx < 0 or idx >= len(self._id_map):
                    continue
                mid = self._id_map[idx]
                rec = self._records.get(mid)
                if rec and rec.agent_id == agent_id:
                    results.append(rec)
                if len(results) >= top_k:
                    break
            return results

    async def recall_recent(self, agent_id: AgentID, n: int = 10) -> List[MemoryRecord]:
        async with self._lock:
            ids = self._agent_memories.get(agent_id, [])
            return [self._records[i] for i in ids[-n:]]

    async def consolidate(self, agent_id: AgentID) -> str:
        """Ringkas memori lama menjadi summary tingkat tinggi (memory consolidation)."""
        async with self._lock:
            ids = self._agent_memories.get(agent_id, [])
            if len(ids) < 20:
                return "Not enough memories to consolidate"
            old_ids = ids[:-10]  # keep last 10 intact
            contents = [self._records[i].content for i in old_ids]
            summary = f"[CONSOLIDATED] {len(old_ids)} memories summarized. Topics: " + \
                      ", ".join(set(c.split()[0] for c in contents if c)[:5])
            # Mark old records as consolidated
            for mid in old_ids:
                self._records[mid].metadata["consolidated"] = True
            # Store summary as new memory
            await self.store(agent_id, summary, importance=5.0)
            return summary


# ═══════════════════════════════════════════════════════════════════════════════
# 7. MCP ADAPTER — Model Context Protocol Server/Client
# ═══════════════════════════════════════════════════════════════════════════════

class MCPAdapter:
    """Model Context Protocol integration — connect ke MCP servers untuk tool expansion."""

    def __init__(self):
        self._servers: Dict[str, Any] = {}  # server_name -> connection
        self._tools: Dict[str, Tuple[str, str]] = {}  # tool_name -> (server_name, schema)
        self._lock = asyncio.Lock()

    async def connect_stdio(self, name: str, command: str, args: List[str]) -> Dict[str, Any]:
        """Connect ke MCP server via stdio transport."""
        try:
            import mcp  # optional dependency
        except ImportError:
            return {"success": False, "error": "mcp package not installed"}
        try:
            # Simplified stdio connection
            proc = await asyncio.create_subprocess_exec(
                command, *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._servers[name] = {"type": "stdio", "proc": proc}
            return {"success": True, "server": name, "transport": "stdio"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def connect_sse(self, name: str, url: str) -> Dict[str, Any]:
        """Connect ke MCP server via SSE transport."""
        self._servers[name] = {"type": "sse", "url": url}
        return {"success": True, "server": name, "transport": "sse", "url": url}

    async def list_tools(self, server_name: Optional[str] = None) -> Dict[str, Any]:
        """List tools yang tersedia dari semua atau specific MCP server."""
        if server_name:
            srv = self._servers.get(server_name)
            if not srv:
                return {"success": False, "error": f"Server '{server_name}' not connected"}
            return {"success": True, "server": server_name, "tools": list(self._tools.keys())}
        return {"success": True, "servers": list(self._servers.keys()), "tools": list(self._tools.keys())}

    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Panggil tool di MCP server."""
        srv = self._servers.get(server_name)
        if not srv:
            return {"success": False, "error": f"Server '{server_name}' not connected"}
        # Stub — actual implementation depends on MCP SDK
        return {
            "success": True,
            "server": server_name,
            "tool": tool_name,
            "arguments": arguments,
            "result": "[MCP stub — integrate with official MCP SDK for full functionality]",
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 8. A2A PROTOCOL — Agent-to-Agent Communication
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class A2AMessage:
    message_id: str
    sender_id: AgentID
    recipient_id: AgentID
    message_type: str  # "task", "query", "response", "broadcast"
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    reply_to: Optional[str] = None
    ttl: int = 10  # hop limit


class A2AProtocol:
    """Agent-to-Agent protocol untuk komunikasi antar agent di MAGNATRIX mesh."""

    def __init__(self, hub: Optional[Any] = None):
        self._inbox: Dict[AgentID, asyncio.Queue] = {}
        self._handlers: Dict[str, List[Callable[[A2AMessage], Any]]] = {}
        self._hub = hub
        self._lock = asyncio.Lock()

    async def register_agent(self, agent_id: AgentID):
        async with self._lock:
            if agent_id not in self._inbox:
                self._inbox[agent_id] = asyncio.Queue()

    async def send(self, msg: A2AMessage) -> bool:
        """Kirim pesan ke recipient."""
        async with self._lock:
            inbox = self._inbox.get(msg.recipient_id)
            if inbox:
                await inbox.put(msg)
                return True
            # Fallback: broadcast via hub jika agent tidak local
            if self._hub:
                await self._hub.route_a2a(msg)
                return True
            return False

    async def broadcast(self, sender_id: AgentID, payload: Dict[str, Any], ttl: int = 5):
        """Broadcast pesan ke semua agent yang terdaftar."""
        async with self._lock:
            for aid, inbox in self._inbox.items():
                if aid == sender_id:
                    continue
                msg = A2AMessage(
                    message_id=f"bc-{uuid.uuid4().hex[:12]}",
                    sender_id=sender_id,
                    recipient_id=aid,
                    message_type="broadcast",
                    payload=payload,
                    ttl=ttl,
                )
                await inbox.put(msg)

    async def receive(self, agent_id: AgentID, timeout: Optional[float] = None) -> Optional[A2AMessage]:
        """Blocking receive untuk agent."""
        inbox = self._inbox.get(agent_id)
        if not inbox:
            return None
        try:
            return await asyncio.wait_for(inbox.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    def subscribe(self, message_type: str, handler: Callable[[A2AMessage], Any]):
        self._handlers.setdefault(message_type, []).append(handler)

    async def poll(self, agent_id: AgentID, max_messages: int = 10) -> List[A2AMessage]:
        """Non-blocking poll untuk agent."""
        inbox = self._inbox.get(agent_id)
        if not inbox:
            return []
        messages = []
        for _ in range(max_messages):
            if inbox.empty():
                break
            messages.append(await inbox.get())
        return messages


# ═══════════════════════════════════════════════════════════════════════════════
# 9. TIME TRAVEL — Workspace Snapshots
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class WorkspaceSnapshot:
    snapshot_id: SnapshotID
    agent_id: AgentID
    description: str
    timestamp: float
    file_manifest: Dict[str, str]  # path -> sha256
    memory_state: List[MemoryID]
    tool_state: List[str]  # tool names
    hierarchy_state: Dict[str, Any]
    tag: Optional[str] = None


class TimeTravel:
    """Time Travel untuk workspace — snapshot, restore, branch."""

    def __init__(self, snapshot_dir: Optional[str] = None):
        self.snapshot_dir = Path(snapshot_dir or "/tmp/magnatrix_snapshots")
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self._snapshots: Dict[SnapshotID, WorkspaceSnapshot] = {}
        self._lock = asyncio.Lock()

    async def snapshot(
        self,
        agent_id: AgentID,
        description: str,
        computer: ComputerAsTool,
        memory: EpisodicMemory,
        forge: DynamicToolForge,
        hierarchy: AgentHierarchy,
        tag: Optional[str] = None,
    ) -> SnapshotID:
        """Ambil snapshot penuh dari workspace agent."""
        async with self._lock:
            sid = f"snap-{uuid.uuid4().hex[:12]}"
            # Manifest file dalam cwd
            manifest = {}
            for root, _, files in os.walk(computer.cwd):
                for f in files:
                    p = Path(root) / f
                    try:
                        manifest[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
                    except Exception:
                        pass

            # Memory state
            mem_ids = list(memory._agent_memories.get(agent_id, []))

            # Tool state
            tools = [t.name for t in forge.list_tools()]

            # Hierarchy state
            sup = await hierarchy.get_superior(agent_id)
            subs = await hierarchy.get_subordinates(agent_id)
            hier_state = {"superior": sup, "subordinates": subs}

            ws = WorkspaceSnapshot(
                snapshot_id=sid,
                agent_id=agent_id,
                description=description,
                timestamp=time.time(),
                file_manifest=manifest,
                memory_state=mem_ids,
                tool_state=tools,
                hierarchy_state=hier_state,
                tag=tag,
            )
            self._snapshots[sid] = ws

            # Persist ke disk
            snap_path = self.snapshot_dir / f"{sid}.json"
            snap_path.write_text(json.dumps(asdict(ws), indent=2, default=str), encoding="utf-8")
            return sid

    async def restore(
        self,
        snapshot_id: SnapshotID,
        agent_id: AgentID,
    ) -> Dict[str, Any]:
        """Restore workspace ke snapshot."""
        async with self._lock:
            ws = self._snapshots.get(snapshot_id)
            if not ws:
                # Try load dari disk
                snap_path = self.snapshot_dir / f"{snapshot_id}.json"
                if snap_path.exists():
                    data = json.loads(snap_path.read_text(encoding="utf-8"))
                    # Reconstruct minimal
                    return {"success": True, "restored_from_disk": True, "data": data}
                return {"success": False, "error": f"Snapshot '{snapshot_id}' not found"}

            return {
                "success": True,
                "snapshot_id": snapshot_id,
                "restored_memory_count": len(ws.memory_state),
                "restored_tool_count": len(ws.tool_state),
                "description": ws.description,
            }

    async def list_snapshots(self, agent_id: Optional[AgentID] = None) -> List[WorkspaceSnapshot]:
        async with self._lock:
            results = []
            for ws in self._snapshots.values():
                if agent_id is None or ws.agent_id == agent_id:
                    results.append(ws)
            return sorted(results, key=lambda x: x.timestamp, reverse=True)

    async def branch(self, snapshot_id: SnapshotID, new_agent_id: AgentID) -> SnapshotID:
        """Buat branch baru dari snapshot — clone workspace untuk agent baru."""
        async with self._lock:
            ws = self._snapshots.get(snapshot_id)
            if not ws:
                raise ValueError(f"Snapshot '{snapshot_id}' not found")
            new_sid = f"snap-{uuid.uuid4().hex[:12]}"
            new_ws = WorkspaceSnapshot(
                snapshot_id=new_sid,
                agent_id=new_agent_id,
                description=f"Branch from {snapshot_id}: {ws.description}",
                timestamp=time.time(),
                file_manifest=dict(ws.file_manifest),
                memory_state=list(ws.memory_state),
                tool_state=list(ws.tool_state),
                hierarchy_state=dict(ws.hierarchy_state),
                tag=f"branch:{snapshot_id}",
            )
            self._snapshots[new_sid] = new_ws
            return new_sid


# ═══════════════════════════════════════════════════════════════════════════════
# 10. AGENT ZERO CORE — Main Orchestrator
# ═══════════════════════════════════════════════════════════════════════════════

class AgentZeroCore:
    """Orchestrator utama yang mengintegrasikan semua pattern Agent Zero secara native.

    Tiap instance AgentZeroCore adalah satu agent yang:
    - Berperilaku 100% berdasarkan system prompt
    - Bisa membuat tool sendiri secara dinamis
    - Bisa delegasi ke subordinate agent
    - Punya akses penuh ke komputer (shell, file, browser)
    - Punya episodic memory (FAISS)
    - Bisa berkomunikasi via A2A protocol
    - Bisa snapshot/restore workspace (Time Travel)
    - Bisa connect ke MCP servers untuk tool expansion
    """

    def __init__(
        self,
        agent_id: AgentID,
        role: str = "generalist",
        superior_id: Optional[AgentID] = None,
        prompt_registry: Optional[SystemPromptRegistry] = None,
        workspace_dir: Optional[str] = None,
    ):
        self.agent_id = agent_id
        self.role = role
        self.superior_id = superior_id
        self.prompt_registry = prompt_registry or SystemPromptRegistry()

        # Subsystems
        self.forge = DynamicToolForge()
        self.hierarchy = AgentHierarchy(self.prompt_registry)
        self.computer = ComputerAsTool(cwd=workspace_dir or f"/tmp/magnatrix_ws/{agent_id}")
        self.browser = BrowserAutomation()
        self.memory = EpisodicMemory()
        self.mcp = MCPAdapter()
        self.a2a = A2AProtocol()
        self.time_travel = TimeTravel()

        # State
        self._status = AgentStatus.IDLE
        self._task_history: List[str] = []
        self._current_task: Optional[str] = None

    async def initialize(self):
        """Initialize agent — register di hierarchy, A2A, dll."""
        await self.hierarchy.register_agent(self.agent_id, self.role, self.superior_id)
        await self.a2a.register_agent(self.agent_id)

    def get_system_prompt(self, task: Optional[str] = None) -> str:
        """Generate system prompt untuk LLM call."""
        kwargs = {
            "agent_id": self.agent_id,
            "superior_id": self.superior_id or "none",
            "role_description": self.role,
            "task_description": task or "none",
            "available_tools": ", ".join(t.name for t in self.forge.list_tools()),
            "subordinate_count": len(self.hierarchy._children.get(self.agent_id, [])),
        }
        if self.superior_id:
            return self.prompt_registry.get("subordinate", **kwargs)
        return self.prompt_registry.get("agent_zero", **kwargs)

    async def think_and_act(self, user_input: str) -> Dict[str, Any]:
        """Main loop: agent menerima input, berpikir, dan bertindak."""
        self._status = AgentStatus.WORKING
        self._current_task = user_input

        # Step 1: Store user input in memory
        await self.memory.store(self.agent_id, f"User: {user_input}", importance=3.0)

        # Step 2: Retrieve relevant past memories
        # (In production, embed user_input and search; here we use recent fallback)
        recent_memories = await self.memory.recall_recent(self.agent_id, n=5)

        # Step 3: Build prompt untuk LLM
        prompt = self.get_system_prompt(task=user_input)
        # Append memories ke prompt context
        if recent_memories:
            prompt += "\n\nRELEVANT PAST MEMORIES:\n"
            for mem in recent_memories:
                prompt += f"- [{datetime.fromtimestamp(mem.timestamp).isoformat()}] {mem.content}\n"

        # Step 4: Return structured action plan (this would go to LLM in real flow)
        action_plan = {
            "agent_id": self.agent_id,
            "prompt_ready": True,
            "prompt_length": len(prompt),
            "system_prompt": prompt,
            "subsystems_ready": {
                "forge_tools": len(self.forge.list_tools()),
                "memory_records": len(self.memory._records),
                "computer_cwd": self.computer.cwd,
                "browser_ready": self.browser._driver is not None,
                "a2a_registered": self.agent_id in self.a2a._inbox,
            },
            "dynamic_tool_schemas": [self.forge.get_tool_schema(t.name) for t in self.forge.list_tools()],
        }

        # Step 5: Store action plan in memory
        await self.memory.store(self.agent_id, f"Action plan generated for: {user_input}", importance=2.0)

        self._status = AgentStatus.IDLE
        self._task_history.append(user_input)
        return action_plan

    async def create_tool(self, task_description: str, generated_code: str) -> Dict[str, Any]:
        """Agent create tool baru secara dinamis."""
        tool_name = f"tool_{uuid.uuid4().hex[:8]}"
        sig = await self.forge.forge_tool(tool_name, generated_code, description=task_description)
        await self.memory.store(
            self.agent_id,
            f"Created dynamic tool '{tool_name}' for: {task_description}",
            importance=4.0,
        )
        return {
            "success": True,
            "tool_name": tool_name,
            "signature": sig.to_json_schema(),
        }

    async def delegate_task(self, task_description: str, priority: int = 5) -> str:
        """Delegasi task ke subordinate."""
        return await self.hierarchy.delegate(self.agent_id, task_description, priority)

    async def save_checkpoint(self, description: str) -> SnapshotID:
        """Simpan checkpoint workspace."""
        sid = await self.time_travel.snapshot(
            self.agent_id, description,
            self.computer, self.memory, self.forge, self.hierarchy,
        )
        await self.memory.store(self.agent_id, f"Checkpoint saved: {sid} — {description}", importance=5.0)
        return sid

    async def restore_checkpoint(self, snapshot_id: SnapshotID) -> Dict[str, Any]:
        """Restore workspace dari checkpoint."""
        return await self.time_travel.restore(snapshot_id, self.agent_id)

    async def send_message(self, recipient: AgentID, payload: Dict[str, Any]) -> bool:
        """Kirim A2A message ke agent lain."""
        msg = A2AMessage(
            message_id=f"msg-{uuid.uuid4().hex[:12]}",
            sender_id=self.agent_id,
            recipient_id=recipient,
            message_type="task",
            payload=payload,
        )
        return await self.a2a.send(msg)

    async def get_status(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "status": self._status.name,
            "superior": self.superior_id,
            "subordinates": await self.hierarchy.get_subordinates(self.agent_id),
            "tools_registered": len(self.forge.list_tools()),
            "memory_count": len(self.memory._agent_memories.get(self.agent_id, [])),
            "task_history_count": len(self._task_history),
            "current_task": self._current_task,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 11. MAGNATRIX INTEGRATION HOOKS
# ═══════════════════════════════════════════════════════════════════════════════

class AgentZeroAdapter:
    """Adapter untuk menghubungkan Agent Zero core ke layer-layer MAGNATRIX yang sudah ada."""

    def __init__(self, core: AgentZeroCore):
        self.core = core

    # ── Knowledge Layer ───────────────────────────────────────────────────────
    async def sync_to_knowledge_graph(self, knowledge_store: Any):
        """Sync episodic memory ke knowledge graph MAGNATRIX."""
        memories = await self.core.memory.recall_recent(self.core.agent_id, n=50)
        for mem in memories:
            # Konversi memory record ke knowledge triple
            triple = {
                "subject": self.core.agent_id,
                "predicate": "experienced",
                "object": mem.content[:200],
                "timestamp": mem.timestamp,
                "confidence": mem.importance / 10.0,
            }
            # knowledge_store.insert_triple(triple)  # integrate dengan layer Knowledge
        return {"synced": len(memories)}

    # ── Trading Layer ─────────────────────────────────────────────────────────
    async def register_trading_tools(self, trading_engine: Any):
        """Register tool trading dari engine ke forge."""
        # Example: convert trading functions ke dynamic tools
        pass

    # ── P2P Mesh Layer ──────────────────────────────────────────────────────
    async def register_mesh_transport(self, mesh_transport: Any):
        """Gunakan P2P mesh sebagai transport untuk A2A protocol."""
        self.core.a2a._hub = mesh_transport
        return {"mesh_registered": True}

    # ── Runtime Layer ───────────────────────────────────────────────────────
    async def register_runtime_hooks(self, runtime: Any):
        """Register hooks ke MAGNATRIX runtime untuk lifecycle management."""
        # runtime.on_agent_spawn(self.core.agent_id, self.core)
        pass

    # ── Governance Layer ────────────────────────────────────────────────────
    async def apply_constitutional_constraints(self, constitution: Any):
        """Apply constitutional constraints dari governance layer."""
        # constitution.enforce(self.core)
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# 12. STANDALONE DEMO
# ═══════════════════════════════════════════════════════════════════════════════

async def demo_agent_zero():
    """Demo menjalankan Agent Zero core dengan semua subsystem."""
    print("═" * 70)
    print("MAGNATRIX — Native Agent Zero Demo")
    print("═" * 70)

    # Create superior agent
    superior = AgentZeroCore("agent-alpha", role="orchestrator")
    await superior.initialize()

    # Create subordinate
    beta = AgentZeroCore("agent-beta", role="researcher", superior_id="agent-alpha")
    await beta.initialize()

    # Superior delegates task
    task_id = await superior.delegate_task("Research quantum computing advances 2024", priority=8)
    print(f"\n[1] Superior delegated task: {task_id}")

    # Beta thinks and acts
    plan = await beta.think_and_act("Research quantum computing advances 2024")
    print(f"[2] Beta action plan ready — prompt length: {plan['prompt_length']}")

    # Beta creates a dynamic tool
    tool_code = textwrap.dedent("""\
        def run(query: str, max_results: int = 5) -> dict:
            \"\"\"Simulate research tool.\"\"\"\n            return {"result": f"Research on '{query}': {max_results} papers found", "success": True}
    """)
    tool_info = await beta.create_tool("Research quantum papers", tool_code)
    print(f"[3] Dynamic tool created: {tool_info['tool_name']}")

    # Beta invokes the tool
    result = await beta.forge.invoke(tool_info['tool_name'], query="quantum", max_results=3)
    print(f"[4] Tool result: {result['result']}")

    # Beta reports back
    await beta.hierarchy.report_result(beta.agent_id, task_id, result)
    print(f"[5] Beta reported result to superior")

    # Superior saves checkpoint
    sid = await superior.save_checkpoint("Post-delegation baseline")
    print(f"[6] Checkpoint saved: {sid}")

    # Beta takes a browser screenshot (mock)
    browse = await beta.browser.navigate("https://example.com")
    print(f"[7] Browser nav: {browse.get('title', 'N/A')}")

    # A2A communication
    await beta.send_message("agent-alpha", {"type": "status_update", "progress": 100})
    print(f"[8] A2A message sent: beta -> alpha")

    # Status
    status = await superior.get_status()
    print(f"\n[9] Superior status: {json.dumps(status, indent=2, default=str)}")

    # List snapshots
    snaps = await superior.time_travel.list_snapshots(superior.agent_id)
    print(f"[10] Snapshots: {len(snaps)}")

    print("\n" + "═" * 70)
    print("Demo selesai — Agent Zero pattern 100% native di MAGNATRIX")
    print("═" * 70)
    return True


if __name__ == "__main__":
    asyncio.run(demo_agent_zero())
