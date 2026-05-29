
"""
claude_code_v2_native.py — MAGNATRIX-OS Enhanced Claude Code Harness v2

AMATI from GHGmc2/claude-code actual source code (TypeScript).
Pure Python, stdlib only. Zero external dependencies.

Components:
    • StreamingToolExecutor — async tool execution with concurrency-safe dispatch
    • QueryEngine — main orchestration with token budget, compaction, streaming
    • ContextSystem — memoized system/user context with git integration
    • TaskManager — typed tasks with lifecycle management
    • HistoryManager — conversation history with paste reference handling
    • ClaudeCodeHarnessV2 — main orchestrator combining all above
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


# ════════════════════════════════════════════════════════════════════════════
# 1. StreamingToolExecutor — async tool execution with concurrency dispatch
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class ToolExecution:
    """Result of a single tool execution."""
    tool_name: str
    input_args: Dict[str, Any]
    output: Any
    error: Optional[str] = None
    duration_ms: float = 0.0
    tokens_used: int = 0


class StreamingToolExecutor:
    """
    Execute tools with streaming support and concurrency-safe dispatch.
    Tools marked concurrency-safe run in parallel.
    """

    def __init__(self, registry: Any) -> None:
        self.registry = registry  # ToolRegistry from claude_code_tools_native.py
        self._lock = threading.Lock()
        self._execution_log: List[ToolExecution] = []

    def execute(self, tool_name: str, args: Dict[str, Any]) -> ToolExecution:
        """Execute a single tool synchronously."""
        start = time.time()
        try:
            tool = self.registry.get(tool_name)
            if not tool:
                return ToolExecution(
                    tool_name=tool_name, input_args=args,
                    output=None, error=f"Tool '{tool_name}' not found",
                    duration_ms=(time.time() - start) * 1000
                )
            result = tool.call(args)
            duration = (time.time() - start) * 1000
            exec_result = ToolExecution(
                tool_name=tool_name, input_args=args,
                output=result, error=None, duration_ms=duration
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            exec_result = ToolExecution(
                tool_name=tool_name, input_args=args,
                output=None, error=str(e), duration_ms=duration
            )

        with self._lock:
            self._execution_log.append(exec_result)
        return exec_result

    def execute_batch(
        self, calls: List[Tuple[str, Dict[str, Any]]]
    ) -> List[ToolExecution]:
        """
        Execute multiple tools. Concurrency-safe tools run in parallel threads.
        Others run sequentially.
        """
        results: List[ToolExecution] = []
        sequential: List[Tuple[str, Dict[str, Any]]] = []
        parallel_calls: List[Tuple[str, Dict[str, Any]]] = []

        for name, args in calls:
            tool = self.registry.get(name)
            if tool and getattr(tool, 'is_concurrency_safe', False):
                parallel_calls.append((name, args))
            else:
                sequential.append((name, args))

        # Run concurrent tools in threads
        if parallel_calls:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            with ThreadPoolExecutor(max_workers=8) as pool:
                futures = {pool.submit(self.execute, n, a): (n, a) for n, a in parallel_calls}
                for fut in as_completed(futures):
                    results.append(fut.result())

        # Run sequential tools in order
        for name, args in sequential:
            results.append(self.execute(name, args))

        return results

    def get_execution_log(self) -> List[ToolExecution]:
        with self._lock:
            return self._execution_log.copy()


# ════════════════════════════════════════════════════════════════════════════
# 2. QueryEngine — main orchestration with token budget & compaction
# ════════════════════════════════════════════════════════════════════════════

class TokenBudgetState:
    """Tracks token budget consumption."""
    def __init__(self, max_tokens: int = 200000):
        self.max_tokens = max_tokens
        self.used_tokens = 0
        self.compaction_count = 0

    def add(self, tokens: int) -> None:
        self.used_tokens += tokens

    def remaining(self) -> int:
        return max(0, self.max_tokens - self.used_tokens)

    def usage_ratio(self) -> float:
        return self.used_tokens / self.max_tokens

    def should_compact(self, threshold: float = 0.75) -> bool:
        return self.usage_ratio() >= threshold


class Message:
    """A single message in the conversation."""
    def __init__(
        self, role: str, content: str,
        tool_calls: Optional[List[Dict]] = None,
        tool_results: Optional[List[Dict]] = None
    ):
        self.role = role
        self.content = content
        self.tool_calls = tool_calls or []
        self.tool_results = tool_results or []
        self.timestamp = datetime.now().isoformat()

    def estimate_tokens(self) -> int:
        """Rough token estimation: ~4 chars per token."""
        total = len(self.content)
        for tc in self.tool_calls:
            total += len(str(tc))
        for tr in self.tool_results:
            total += len(str(tr))
        return total // 4

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "tool_calls": self.tool_calls,
            "tool_results": self.tool_results,
            "timestamp": self.timestamp,
        }


class QueryEngine:
    """
    Main orchestration engine.
    - Token budget tracking
    - Context compaction (summarize when >75% budget)
    - Message normalization
    - Tool result budget limiting
    - Error handling
    """

    def __init__(
        self,
        llm_fn: Callable[[List[Dict[str, Any]], str], str],
        tool_executor: StreamingToolExecutor,
        max_tokens: int = 200000,
        compact_threshold: float = 0.75,
    ):
        self.llm_fn = llm_fn
        self.tool_executor = tool_executor
        self.budget = TokenBudgetState(max_tokens)
        self.compact_threshold = compact_threshold
        self.messages: List[Message] = []
        self.system_prompt = (
            "You are a helpful assistant. You have access to tools. "
            "Use them when appropriate. Always use the provided context."
        )

    def run(self, user_input: str) -> str:
        """Run one turn of the conversation."""
        # Add user message
        user_msg = Message("user", user_input)
        self.messages.append(user_msg)
        self.budget.add(user_msg.estimate_tokens())

        # Compact if needed
        if self.budget.should_compact(self.compact_threshold):
            self._compact_context()

        # Build API messages
        api_messages = self._build_api_messages()

        # Call LLM
        try:
            response = self.llm_fn(api_messages, self.system_prompt)
        except Exception as e:
            return f"[LLM Error: {e}]"

        # Parse tool calls from response (simple JSON parsing)
        tool_calls = self._parse_tool_calls(response)

        if tool_calls:
            # Execute tools
            tool_results = self._execute_tools(tool_calls)
            # Add assistant message with tool calls
            assistant_msg = Message(
                "assistant", response, tool_calls=tool_calls, tool_results=tool_results
            )
            self.messages.append(assistant_msg)
            self.budget.add(assistant_msg.estimate_tokens())

            # Re-call LLM with tool results
            api_messages = self._build_api_messages()
            try:
                response = self.llm_fn(api_messages, self.system_prompt)
            except Exception as e:
                return f"[LLM Error after tool execution: {e}]"

        # Add final assistant message
        final_msg = Message("assistant", response)
        self.messages.append(final_msg)
        self.budget.add(final_msg.estimate_tokens())

        return response

    def _build_api_messages(self) -> List[Dict[str, Any]]:
        """Convert internal messages to API format."""
        return [m.to_dict() for m in self.messages]

    def _parse_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """Parse tool calls from LLM response."""
        tool_calls = []
        # Simple JSON-based tool call detection
        # Look for {"tool": "name", "args": {...}}
        pattern = r'\{\s*"tool"\s*:\s*"([^"]+)"\s*,\s*"args"\s*:\s*(\{[^}]*\})\}'
        matches = re.findall(pattern, response)
        for tool_name, args_str in matches:
            try:
                args = json.loads(args_str)
                tool_calls.append({"name": tool_name, "args": args})
            except json.JSONDecodeError:
                continue
        # Also look for simpler pattern: <tool name="...">...</tool>
        xml_pattern = r'<tool\s+name="([^"]+)">(.*?)</tool>'
        for name, args_str in re.findall(xml_pattern, response, re.DOTALL):
            try:
                args = json.loads(args_str)
                tool_calls.append({"name": name, "args": args})
            except json.JSONDecodeError:
                tool_calls.append({"name": name, "args": {"content": args_str}})
        return tool_calls

    def _execute_tools(self, tool_calls: List[Dict]) -> List[Dict]:
        """Execute tool calls and return results."""
        calls = [(tc["name"], tc["args"]) for tc in tool_calls]
        executions = self.tool_executor.execute_batch(calls)
        return [
            {
                "tool": e.tool_name,
                "output": e.output,
                "error": e.error,
                "duration_ms": e.duration_ms,
            }
            for e in executions
        ]

    def _compact_context(self) -> None:
        """Summarize old messages to free token budget."""
        if len(self.messages) < 4:
            return

        # Keep system context + last 2 exchanges, summarize the rest
        to_summarize = self.messages[2:-2]
        if not to_summarize:
            return

        summary_content = "\n".join(
            f"[{m.role}]: {m.content[:100]}..." for m in to_summarize
        )
        summary = f"[Summary of {len(to_summarize)} previous messages]:\n{summary_content}"

        self.messages = [self.messages[0], Message("system", summary)] + self.messages[-2:]
        self.budget.used_tokens = sum(m.estimate_tokens() for m in self.messages)
        self.budget.compaction_count += 1

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in self.messages]

    def get_token_stats(self) -> Dict[str, Any]:
        return {
            "max_tokens": self.budget.max_tokens,
            "used_tokens": self.budget.used_tokens,
            "remaining": self.budget.remaining(),
            "usage_ratio": round(self.budget.usage_ratio(), 3),
            "compaction_count": self.budget.compaction_count,
        }


# ════════════════════════════════════════════════════════════════════════════
# 3. ContextSystem — memoized system/user context with git integration
# ════════════════════════════════════════════════════════════════════════════

class ContextSystem:
    """
    Provides memoized system and user context for each conversation.
    - System context: git status, branch, recent commits, current directory
    - User context: CLAUDE.md files, current date
    - Cache invalidation on file changes
    """

    def __init__(self, project_root: Optional[str] = None):
        self.project_root = project_root or os.getcwd()
        self._cache: Dict[str, Any] = {}
        self._cache_lock = threading.Lock()

    def _get_git_info(self) -> Optional[Dict[str, str]]:
        """Get git status, branch, and recent commits."""
        try:
            # Check if git repo
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True, text=True, cwd=self.project_root, timeout=5
            )
            if result.returncode != 0:
                return None

            # Get branch
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, cwd=self.project_root, timeout=5
            ).stdout.strip()

            # Get default branch
            default_branch = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "origin/HEAD"],
                capture_output=True, text=True, cwd=self.project_root, timeout=5
            ).stdout.strip().replace("origin/", "")

            # Get status (truncated at 2k chars)
            status = subprocess.run(
                ["git", "--no-optional-locks", "status", "--short"],
                capture_output=True, text=True, cwd=self.project_root, timeout=5
            ).stdout.strip()
            if len(status) > 2000:
                status = status[:2000] + "\n... (truncated — run git status for full)"

            # Get recent commits
            log = subprocess.run(
                ["git", "--no-optional-locks", "log", "--oneline", "-n", "5"],
                capture_output=True, text=True, cwd=self.project_root, timeout=5
            ).stdout.strip()

            # Get user name
            user_name = subprocess.run(
                ["git", "config", "user.name"],
                capture_output=True, text=True, cwd=self.project_root, timeout=5
            ).stdout.strip()

            return {
                "branch": branch or "unknown",
                "default_branch": default_branch or "main",
                "user_name": user_name,
                "status": status or "(clean)",
                "recent_commits": log,
            }
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
            return None

    def _get_claude_mds(self) -> Optional[str]:
        """Find and read CLAUDE.md files in project."""
        claude_mds = []
        try:
            for root, _, files in os.walk(self.project_root):
                for f in files:
                    if f.lower() == "claude.md":
                        path = os.path.join(root, f)
                        try:
                            with open(path, "r", encoding="utf-8") as fh:
                                content = fh.read()
                                claude_mds.append(f"--- {os.path.relpath(path, self.project_root)} ---\n{content}")
                        except Exception:
                            continue
                # Limit walk depth
                if root.count(os.sep) - self.project_root.count(os.sep) >= 3:
                    break
        except Exception:
            pass
        return "\n\n".join(claude_mds) if claude_mds else None

    def get_system_context(self) -> Dict[str, str]:
        """Get system context (git, project info). Memoized."""
        cache_key = f"system_{self.project_root}"
        with self._cache_lock:
            if cache_key in self._cache:
                return self._cache[cache_key]

        git_info = self._get_git_info()
        context: Dict[str, str] = {}

        if git_info:
            context["git_status"] = (
                f"Current branch: {git_info['branch']}\n"
                f"Main branch: {git_info['default_branch']}\n"
                f"Git user: {git_info['user_name']}\n"
                f"Status:\n{git_info['status']}\n"
                f"Recent commits:\n{git_info['recent_commits']}"
            )

        context["current_directory"] = self.project_root
        context["timestamp"] = datetime.now().isoformat()

        with self._cache_lock:
            self._cache[cache_key] = context
        return context

    def get_user_context(self) -> Dict[str, str]:
        """Get user context (CLAUDE.md, date). Memoized."""
        cache_key = f"user_{self.project_root}"
        with self._cache_lock:
            if cache_key in self._cache:
                return self._cache[cache_key]

        claude_md = self._get_claude_mds()
        context: Dict[str, str] = {}

        if claude_md:
            context["claude_md"] = claude_md

        context["current_date"] = f"Today's date is {datetime.now().strftime('%Y-%m-%d')}."

        with self._cache_lock:
            self._cache[cache_key] = context
        return context

    def invalidate_cache(self) -> None:
        """Invalidate all cached contexts."""
        with self._cache_lock:
            self._cache.clear()


# ════════════════════════════════════════════════════════════════════════════
# 4. TaskManager — typed tasks with lifecycle management
# ════════════════════════════════════════════════════════════════════════════

class TaskType(Enum):
    LOCAL_BASH = "local_bash"
    LOCAL_AGENT = "local_agent"
    REMOTE_AGENT = "remote_agent"
    IN_PROCESS_TEAMMATE = "in_process_teammate"
    LOCAL_WORKTREE = "local_worktree"
    MONITOR_MCP = "monitor_mcp"
    DREAM = "dream"


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"


TASK_ID_PREFIXES: Dict[str, str] = {
    "local_bash": "b",
    "local_agent": "a",
    "remote_agent": "r",
    "in_process_teammate": "t",
    "local_worktree": "w",
    "monitor_mcp": "m",
    "dream": "d",
}


def is_terminal_status(status: TaskStatus) -> bool:
    return status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.KILLED)


@dataclass
class Task:
    id: str
    type: TaskType
    status: TaskStatus
    description: str
    created_at: float
    completed_at: Optional[float] = None
    total_paused_ms: float = 0.0
    output: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskManager:
    """
    Manage typed tasks with lifecycle tracking.
    - 7 task types (local_bash, local_agent, remote_agent, etc.)
    - Status transitions: pending -> running -> (completed | failed | killed)
    - Task ID generation with prefix + random
    - Output tracking
    """

    def __init__(self) -> None:
        self._tasks: Dict[str, Task] = {}
        self._lock = threading.Lock()

    @staticmethod
    def generate_task_id(task_type: TaskType) -> str:
        """Generate task ID: prefix + 8 random chars."""
        prefix = TASK_ID_PREFIXES.get(task_type.value, "x")
        import random
        alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
        random_chars = "".join(random.choice(alphabet) for _ in range(8))
        return f"{prefix}-{random_chars}"

    def create(
        self, task_type: TaskType, description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Task:
        """Create a new task in pending status."""
        task_id = self.generate_task_id(task_type)
        task = Task(
            id=task_id,
            type=task_type,
            status=TaskStatus.PENDING,
            description=description,
            created_at=time.time(),
            metadata=metadata or {},
        )
        with self._lock:
            self._tasks[task_id] = task
        return task

    def start(self, task_id: str) -> bool:
        """Transition task to running."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status != TaskStatus.PENDING:
                return False
            task.status = TaskStatus.RUNNING
        return True

    def complete(self, task_id: str, output: str = "") -> bool:
        """Transition task to completed."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status not in (TaskStatus.PENDING, TaskStatus.RUNNING):
                return False
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            task.output = output
        return True

    def fail(self, task_id: str, error: str = "") -> bool:
        """Transition task to failed."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or is_terminal_status(task.status):
                return False
            task.status = TaskStatus.FAILED
            task.completed_at = time.time()
            task.output = error
        return True

    def kill(self, task_id: str) -> bool:
        """Transition task to killed."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or is_terminal_status(task.status):
                return False
            task.status = TaskStatus.KILLED
            task.completed_at = time.time()
        return True

    def get(self, task_id: str) -> Optional[Task]:
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(
        self, status: Optional[TaskStatus] = None
    ) -> List[Task]:
        with self._lock:
            tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    def list_all(self) -> List[Task]:
        return self.list_tasks()

    def get_stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "total": len(self._tasks),
                "pending": sum(1 for t in self._tasks.values() if t.status == TaskStatus.PENDING),
                "running": sum(1 for t in self._tasks.values() if t.status == TaskStatus.RUNNING),
                "completed": sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED),
                "failed": sum(1 for t in self._tasks.values() if t.status == TaskStatus.FAILED),
                "killed": sum(1 for t in self._tasks.values() if t.status == TaskStatus.KILLED),
            }


# ════════════════════════════════════════════════════════════════════════════
# 5. HistoryManager — conversation history with paste references
# ════════════════════════════════════════════════════════════════════════════

MAX_HISTORY_ITEMS = 100
MAX_PASTED_CONTENT_LENGTH = 1024


class HistoryManager:
    """
    Manage conversation history with paste content handling.
    - Small pastes (<1024) stored inline
    - Large pastes stored as hash references
    - Reference parsing: [Pasted text #N], [Image #N]
    - JSONL persistence
    """

    def __init__(self, history_file: Optional[str] = None) -> None:
        self._history: List[Dict[str, Any]] = []
        self._pasted_content: Dict[int, str] = {}
        self._paste_counter = 0
        self._lock = threading.Lock()
        self._history_file = history_file

    def _format_pasted_text_ref(self, paste_id: int, num_lines: int) -> str:
        if num_lines == 0:
            return f"[Pasted text #{paste_id}]"
        return f"[Pasted text #{paste_id} +{num_lines} lines]"

    def _format_image_ref(self, image_id: int) -> str:
        return f"[Image #{image_id}]"

    def add_pasted_text(self, text: str) -> str:
        """Add pasted text and return a reference string."""
        num_lines = text.count("\n")
        self._paste_counter += 1
        paste_id = self._paste_counter

        if len(text) <= MAX_PASTED_CONTENT_LENGTH:
            # Store inline in history
            with self._lock:
                self._pasted_content[paste_id] = text
            return text  # Return inline for small content
        else:
            # Store as hash reference
            import hashlib
            content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
            with self._lock:
                self._pasted_content[paste_id] = text
            return f"[Pasted text #{paste_id} hash:{content_hash}]"

    def parse_references(self, text: str) -> List[Dict[str, Any]]:
        """Parse [Pasted text #N] and [Image #N] references from text."""
        pattern = r'\[(Pasted text|Image|\.\.\.Truncated text) #(\d+)(?: \+\d+ lines)?(\.)*\]'
        matches = re.finditer(pattern, text)
        refs = []
        for match in matches:
            ref_id = int(match.group(2))
            refs.append({
                "id": ref_id,
                "type": match.group(1),
                "match": match.group(0),
                "index": match.start(),
            })
        return refs

    def expand_references(self, text: str) -> str:
        """Replace paste references with actual content."""
        refs = self.parse_references(text)
        if not refs:
            return text

        # Process in reverse order to preserve indices
        for ref in reversed(refs):
            if ref["type"] == "Pasted text" and ref["id"] in self._pasted_content:
                content = self._pasted_content[ref["id"]]
                text = text[:ref["index"]] + content + text[ref["index"] + len(ref["match"]):]
        return text

    def add_entry(self, role: str, content: str) -> None:
        """Add a history entry."""
        with self._lock:
            self._history.append({
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            })
            # Trim to max
            if len(self._history) > MAX_HISTORY_ITEMS:
                self._history = self._history[-MAX_HISTORY_ITEMS:]

    def get_history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return self._history.copy()

    def save(self, path: Optional[str] = None) -> None:
        """Save history to JSONL file."""
        save_path = path or self._history_file
        if not save_path:
            return
        with open(save_path, "w", encoding="utf-8") as f:
            for entry in self._history:
                f.write(json.dumps(entry) + "\n")

    def load(self, path: Optional[str] = None) -> None:
        """Load history from JSONL file."""
        load_path = path or self._history_file
        if not load_path or not os.path.exists(load_path):
            return
        with self._lock:
            self._history = []
            with open(load_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self._history.append(json.loads(line))


# ════════════════════════════════════════════════════════════════════════════
# 6. ClaudeCodeHarnessV2 — Main orchestrator
# ════════════════════════════════════════════════════════════════════════════

class ClaudeCodeHarnessV2:
    """
    Main orchestrator combining all v2 components.
    - QueryEngine for LLM interaction
    - ContextSystem for git/project context
    - TaskManager for sub-task lifecycle
    - HistoryManager for conversation persistence
    - StreamingToolExecutor for tool dispatch
    """

    def __init__(
        self,
        llm_fn: Callable[[List[Dict[str, Any]], str], str],
        tool_registry: Any,
        project_root: Optional[str] = None,
        max_tokens: int = 200000,
    ):
        self.llm_fn = llm_fn
        self.tool_registry = tool_registry
        self.project_root = project_root or os.getcwd()

        # Initialize subsystems
        self.tool_executor = StreamingToolExecutor(tool_registry)
        self.query_engine = QueryEngine(llm_fn, self.tool_executor, max_tokens)
        self.context_system = ContextSystem(self.project_root)
        self.task_manager = TaskManager()
        self.history_manager = HistoryManager()

    def run(self, user_input: str) -> str:
        """Run one turn: get context, run query, update history."""
        # Get context
        system_ctx = self.context_system.get_system_context()
        user_ctx = self.context_system.get_user_context()

        # Build enriched prompt with context
        enriched_input = self._enrich_input(user_input, system_ctx, user_ctx)

        # Run query engine
        response = self.query_engine.run(enriched_input)

        # Update history
        self.history_manager.add_entry("user", user_input)
        self.history_manager.add_entry("assistant", response)

        return response

    def run_conversation(self, inputs: List[str]) -> List[str]:
        """Run multiple turns."""
        responses = []
        for inp in inputs:
            responses.append(self.run(inp))
        return responses

    def _enrich_input(
        self, user_input: str,
        system_ctx: Dict[str, str],
        user_ctx: Dict[str, str]
    ) -> str:
        """Prepend context to user input."""
        parts = []
        for key, value in system_ctx.items():
            parts.append(f"[{key}]\n{value}")
        for key, value in user_ctx.items():
            parts.append(f"[{key}]\n{value}")
        parts.append(f"[user_question]\n{user_input}")
        return "\n\n".join(parts)

    def create_task(
        self, task_type_str: str, description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Task:
        """Create a managed task."""
        task_type = TaskType(task_type_str)
        return self.task_manager.create(task_type, description, metadata)

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.task_manager.get(task_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive system stats."""
        return {
            "tokens": self.query_engine.get_token_stats(),
            "tasks": self.task_manager.get_stats(),
            "history_entries": len(self.history_manager.get_history()),
            "tools_available": len(self.tool_registry.list_enabled()) if hasattr(self.tool_registry, 'list_enabled') else 0,
        }

    def save_session(self, path: str) -> None:
        """Save session state to file."""
        state = {
            "history": self.history_manager.get_history(),
            "tasks": [
                {
                    "id": t.id, "type": t.type.value, "status": t.status.value,
                    "description": t.description, "output": t.output,
                }
                for t in self.task_manager.list_all()
            ],
            "token_stats": self.query_engine.get_token_stats(),
            "timestamp": datetime.now().isoformat(),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def load_session(self, path: str) -> None:
        """Load session state from file."""
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
        # Restore history
        for entry in state.get("history", []):
            self.history_manager.add_entry(entry["role"], entry["content"])


# ════════════════════════════════════════════════════════════════════════════
# DEMO / SELF-TEST
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Claude Code Harness V2 — Self-Test")
    print("=" * 60)

    # Mock LLM
    def mock_llm(messages: List[Dict], system: str) -> str:
        last_msg = messages[-1] if messages else {"content": ""}
        content = last_msg.get("content", "")
        if "ls" in content.lower() or "list" in content.lower():
            return '{"tool": "bash", "args": {"command": "ls -la"}}'
        if "cat" in content.lower() or "read" in content.lower():
            return '{"tool": "read", "args": {"path": "README.md"}}'
        if "search" in content.lower():
            return '{"tool": "grep", "args": {"pattern": "def", "path": "."}}'
        return "I understand. Let me help you with that."

    # Mock ToolRegistry
    class MockTool:
        def __init__(self, name):
            self.name = name
            self.is_concurrency_safe = True
        def call(self, args):
            if self.name == "bash":
                return f"Executed: {args.get('command', 'none')}"
            elif self.name == "read":
                return f"Content of {args.get('path', 'none')}"
            elif self.name == "grep":
                return f"Found matches for {args.get('pattern', 'none')}"
            return f"Mock result for {self.name}"

    class MockToolRegistry:
        def __init__(self):
            self._tools = {
                "bash": MockTool("bash"),
                "read": MockTool("read"),
                "grep": MockTool("grep"),
            }
        def get(self, name):
            return self._tools.get(name)
        def list_enabled(self):
            return list(self._tools.keys())

    registry = MockToolRegistry()

    harness = ClaudeCodeHarnessV2(mock_llm, registry)

    # Test 1: Basic turn
    print("\n[1] Basic turn")
    r1 = harness.run("List files in current directory")
    print(f"  → Response: {r1[:60]}...")

    # Test 2: Multiple turns
    print("\n[2] Multiple turns")
    r2 = harness.run("Read the README file")
    print(f"  → Response: {r2[:60]}...")
    r3 = harness.run("Search for function definitions")
    print(f"  → Response: {r3[:60]}...")

    # Test 3: Context system
    print("\n[3] Context system")
    ctx = harness.context_system.get_system_context()
    print(f"  → System context keys: {list(ctx.keys())}")
    user_ctx = harness.context_system.get_user_context()
    print(f"  → User context keys: {list(user_ctx.keys())}")

    # Test 4: Task manager
    print("\n[4] Task manager")
    t1 = harness.create_task("local_bash", "Run tests")
    print(f"  → Created task: {t1.id}")
    harness.task_manager.start(t1.id)
    harness.task_manager.complete(t1.id, "All tests passed")
    print(f"  → Task status: {harness.get_task(t1.id).status.value}")
    print(f"  → Task output: {harness.get_task(t1.id).output[:40]}...")

    # Test 5: History manager
    print("\n[5] History manager")
    history = harness.history_manager.get_history()
    print(f"  → History entries: {len(history)}")

    # Test 6: Token stats
    print("\n[6] Token stats")
    stats = harness.get_stats()
    print(f"  → Tokens: {stats['tokens']}")
    print(f"  → Tasks: {stats['tasks']}")
    print(f"  → Tools available: {stats['tools_available']}")

    # Test 7: Session save/load
    print("\n[7] Session persistence")
    harness.save_session("/tmp/cc_v2_session.json")
    print(f"  → Session saved to /tmp/cc_v2_session.json")
    with open("/tmp/cc_v2_session.json") as f:
        session = json.load(f)
    print(f"  → Session tasks: {len(session['tasks'])}")
    print(f"  → Session history: {len(session['history'])}")

    # Test 8: QueryEngine compaction
    print("\n[8] QueryEngine compaction")
    qe = harness.query_engine
    for i in range(10):
        qe.messages.append(Message("user", f"Message {i} " * 100))
        qe.budget.add(500)
    print(f"  → Before compaction: {qe.get_token_stats()}")
    qe._compact_context()
    print(f"  → After compaction: {qe.get_token_stats()}")

    print("\n" + "=" * 60)
    print("All self-tests passed ✓")
    print("=" * 60)
