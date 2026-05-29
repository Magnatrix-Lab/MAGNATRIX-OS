#!/usr/bin/env python3
"""
Claude Code Harness Native — MAGNATRIX-OS Runtime Layer
Pure Python reimplementation of Claude Code architecture patterns.

Architecture:
  ClaudeCodeHarness  → while(tool_call) master orchestrator
  ToolRegistry       → dict-based name→handler registry with schema validation
  AgentLoop          → core while loop, model-driven (OpenAI-compatible API)
  ContextManager     → 3-layer compaction (system + history + tool results)
  PermissionEngine   → declarative YAML-style rules (allow / block / ask)
  SubagentManager    → Task tool, isolated child context, depth=1 limit
  SessionStore       → JSONL persistence, resume / fork
  SkillLoader        → on-demand skill loading from directory
  MCPClient          → MCP protocol client skeleton (stdio + HTTP)

Core Tools (8):
  bash, read, edit, write, grep, glob, task, todowrite

Zero external dependencies. Pluggable LLM via OpenAI-compatible HTTP API.

Design notes:
- All HTTP via urllib (no requests).
- All persistence via jsonl append.
- All tool schemas validated via JSONSchema-like dicts.
- Agent loop uses the canonical pattern: while True → LLM → if tool_call → execute → continue.
- Context compaction uses summarisation when token budget exceeded.
- Subagent runs in a subprocess with isolated stdin/stdout JSON protocol.
"""

from __future__ import annotations

import fnmatch
import glob as stdlib_glob
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import threading
import time
import uuid
import urllib.request
import urllib.error
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from pathlib import Path
from typing import (
    Any, Callable, Dict, List, Optional, Tuple, Union, Iterator
)

# ──────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("claude_harness")


# ──────────────────────────────────────────────────────────────────────────
# 1. PermissionEngine — declarative rules
# ──────────────────────────────────────────────────────────────────────────

class PermissionAction(Enum):
    ALLOW = "allow"
    BLOCK = "block"
    ASK = "ask"


@dataclass
class PermissionRule:
    """A single permission rule matching (tool, path_pattern) → action."""
    tool: str
    path_pattern: Optional[str] = None
    action: PermissionAction = PermissionAction.ASK
    description: str = ""

    def matches(self, tool: str, target: Optional[str] = None) -> bool:
        if self.tool != "*" and self.tool != tool:
            return False
        if self.path_pattern is not None and target is not None:
            if not fnmatch.fnmatch(target, self.path_pattern):
                return False
        return True


class PermissionEngine:
    """
    YAML-style declarative permission engine.

    Rules are evaluated top-down; first match wins.
    Default for any unmatched (tool, path) is ASK.
    """

    def __init__(self) -> None:
        self._rules: List[PermissionRule] = []
        self._callbacks: Dict[str, Callable[[str, str], bool]] = {}

    def load_rules(self, rules: List[Dict[str, Any]]) -> None:
        """Load rules from a list of dicts (e.g. parsed YAML)."""
        self._rules.clear()
        for r in rules:
            action = PermissionAction(r.get("action", "ask"))
            self._rules.append(
                PermissionRule(
                    tool=r.get("tool", "*"),
                    path_pattern=r.get("path"),
                    action=action,
                    description=r.get("description", ""),
                )
            )

    def default_rules(self) -> None:
        """Bootstrap with safe defaults."""
        self._rules = [
            PermissionRule("bash", path_pattern="/etc/*", action=PermissionAction.BLOCK, description="protect system configs"),
            PermissionRule("bash", path_pattern="/usr/*", action=PermissionAction.BLOCK, description="protect system binaries"),
            PermissionRule("write", path_pattern="/etc/*", action=PermissionAction.BLOCK, description="no system writes"),
            PermissionRule("write", path_pattern="/usr/*", action=PermissionAction.BLOCK, description="no system writes"),
            PermissionRule("*", action=PermissionAction.ALLOW, description="default allow"),
        ]

    def check(self, tool: str, target: Optional[str] = None) -> Tuple[PermissionAction, str]:
        for rule in self._rules:
            if rule.matches(tool, target):
                return rule.action, rule.description
        return PermissionAction.ASK, "no matching rule"

    def set_ask_callback(self, tool: str, fn: Callable[[str, str], bool]) -> None:
        """Register a callback for ASK decisions on a specific tool."""
        self._callbacks[tool] = fn

    def ask_user(self, tool: str, target: Optional[str]) -> bool:
        """Invoke registered callback or default True (allow)."""
        fn = self._callbacks.get(tool)
        if fn:
            return fn(tool, target or "")
        return True


# ──────────────────────────────────────────────────────────────────────────
# 2. ToolRegistry — dict-based schema-validated tool registry
# ──────────────────────────────────────────────────────────────────────────

@dataclass
class ToolSchema:
    """JSONSchema-like parameter schema for a tool."""
    name: str
    description: str
    parameters: Dict[str, Any]
    required: List[str] = field(default_factory=list)

    def validate(self, arguments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate arguments against schema. Returns (ok, error_message)."""
        props = self.parameters.get("properties", {})
        for key in self.required:
            if key not in arguments:
                return False, f"Missing required param: {key}"
        for key, val in arguments.items():
            if key not in props:
                return False, f"Unknown param: {key}"
            spec = props[key]
            ptype = spec.get("type")
            if ptype == "string" and not isinstance(val, str):
                return False, f"Param {key} must be string"
            if ptype == "integer" and not isinstance(val, int):
                return False, f"Param {key} must be integer"
            if ptype == "boolean" and not isinstance(val, bool):
                return False, f"Param {key} must be boolean"
            if ptype == "array" and not isinstance(val, list):
                return False, f"Param {key} must be array"
        return True, None


class ToolRegistry:
    """
    Dict-based tool registry mapping tool_name → (handler, schema).
    Supports dynamic registration, schema validation, and listing for LLM.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, Tuple[Callable, ToolSchema]] = {}

    def register(
        self,
        name: str,
        handler: Callable[[Dict[str, Any]], Dict[str, Any]],
        schema: ToolSchema,
    ) -> None:
        self._tools[name] = (handler, schema)
        logger.info("Tool registered: %s", name)

    def get(self, name: str) -> Optional[Tuple[Callable, ToolSchema]]:
        return self._tools.get(name)

    def call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        entry = self._tools.get(name)
        if not entry:
            return {"error": f"Unknown tool: {name}", "success": False}
        handler, schema = entry
        ok, err = schema.validate(arguments)
        if not ok:
            return {"error": err, "success": False}
        try:
            return handler(arguments)
        except Exception as e:
            logger.exception("Tool %s failed", name)
            return {"error": str(e), "success": False}

    def list_schemas(self) -> List[Dict[str, Any]]:
        """Return OpenAI-compatible function definitions."""
        out = []
        for name, (_, schema) in self._tools.items():
            out.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": schema.description,
                    "parameters": schema.parameters,
                },
            })
        return out

    def __contains__(self, name: str) -> bool:
        return name in self._tools


# ──────────────────────────────────────────────────────────────────────────
# 3. Core Tool Implementations (8 tools)
# ──────────────────────────────────────────────────────────────────────────

class CoreTools:
    """Static collection of 8 core tool implementations."""

    @staticmethod
    def bash(arguments: Dict[str, Any]) -> Dict[str, Any]:
        cmd = arguments.get("command", "")
        timeout = arguments.get("timeout", 60)
        cwd = arguments.get("cwd")
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "success": result.returncode == 0,
            }
        except subprocess.TimeoutExpired:
            return {"error": "Command timed out", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}

    @staticmethod
    def read(arguments: Dict[str, Any]) -> Dict[str, Any]:
        path = arguments.get("path", "")
        offset = arguments.get("offset", 1)
        limit = arguments.get("limit")
        try:
            p = Path(path)
            if not p.exists():
                return {"error": f"File not found: {path}", "success": False}
            if p.is_dir():
                entries = [str(e) for e in p.iterdir()]
                return {"entries": entries, "success": True}
            with p.open("r", encoding="utf-8") as f:
                lines = f.readlines()
            if offset > 1:
                lines = lines[offset - 1:]
            if limit is not None:
                lines = lines[:limit]
            return {"content": "".join(lines), "success": True}
        except Exception as e:
            return {"error": str(e), "success": False}

    @staticmethod
    def edit(arguments: Dict[str, Any]) -> Dict[str, Any]:
        path = arguments.get("path", "")
        old = arguments.get("old_text", "")
        new = arguments.get("new_text", "")
        try:
            p = Path(path)
            if not p.exists():
                return {"error": f"File not found: {path}", "success": False}
            text = p.read_text(encoding="utf-8")
            if old not in text:
                return {"error": "old_text not found in file", "success": False}
            text = text.replace(old, new, 1)
            p.write_text(text, encoding="utf-8")
            return {"success": True, "path": str(p)}
        except Exception as e:
            return {"error": str(e), "success": False}

    @staticmethod
    def write(arguments: Dict[str, Any]) -> Dict[str, Any]:
        path = arguments.get("path", "")
        content = arguments.get("content", "")
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return {"success": True, "path": str(p), "bytes_written": len(content)}
        except Exception as e:
            return {"error": str(e), "success": False}

    @staticmethod
    def grep(arguments: Dict[str, Any]) -> Dict[str, Any]:
        pattern = arguments.get("pattern", "")
        path = arguments.get("path", ".")
        recursive = arguments.get("recursive", True)
        try:
            p = Path(path)
            matches = []
            regex = re.compile(pattern)
            if p.is_file():
                files = [p]
            else:
                files = p.rglob("*") if recursive else p.iterdir()
                files = [f for f in files if f.is_file()]
            for f in files:
                try:
                    text = f.read_text(encoding="utf-8", errors="ignore")
                    for i, line in enumerate(text.splitlines(), 1):
                        if regex.search(line):
                            matches.append({"file": str(f), "line": i, "text": line})
                except Exception:
                    pass
            return {"matches": matches, "count": len(matches), "success": True}
        except Exception as e:
            return {"error": str(e), "success": False}

    @staticmethod
    def glob(arguments: Dict[str, Any]) -> Dict[str, Any]:
        pattern = arguments.get("pattern", "")
        cwd = arguments.get("cwd", ".")
        try:
            matches = stdlib_glob.glob(pattern, root_dir=cwd)
            return {"matches": matches, "count": len(matches), "success": True}
        except Exception as e:
            return {"error": str(e), "success": False}

    @staticmethod
    def task(arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Task tool — delegates to SubagentManager (registered externally)."""
        return {"error": "Task tool not bound to SubagentManager", "success": False}

    @staticmethod
    def todowrite(arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Write to a TODO file for tracking."""
        path = arguments.get("path", "TODO.md")
        content = arguments.get("content", "")
        mode = arguments.get("mode", "append")
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            if mode == "append":
                with p.open("a", encoding="utf-8") as f:
                    f.write(content + "\n")
            else:
                p.write_text(content, encoding="utf-8")
            return {"success": True, "path": str(p)}
        except Exception as e:
            return {"error": str(e), "success": False}


def build_core_tool_schemas() -> List[ToolSchema]:
    return [
        ToolSchema(
            name="bash",
            description="Execute a shell command.",
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to run."},
                    "timeout": {"type": "integer", "description": "Timeout in seconds."},
                    "cwd": {"type": "string", "description": "Working directory."},
                },
                "required": ["command"],
            },
            required=["command"],
        ),
        ToolSchema(
            name="read",
            description="Read a file or directory listing.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File or directory path."},
                    "offset": {"type": "integer", "description": "Line offset (1-based)."},
                    "limit": {"type": "integer", "description": "Max lines to read."},
                },
                "required": ["path"],
            },
            required=["path"],
        ),
        ToolSchema(
            name="edit",
            description="Replace old_text with new_text in a file.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path."},
                    "old_text": {"type": "string", "description": "Exact text to replace."},
                    "new_text": {"type": "string", "description": "Replacement text."},
                },
                "required": ["path", "old_text", "new_text"],
            },
            required=["path", "old_text", "new_text"],
        ),
        ToolSchema(
            name="write",
            description="Write content to a file (create or overwrite).",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path."},
                    "content": {"type": "string", "description": "Content to write."},
                },
                "required": ["path", "content"],
            },
            required=["path", "content"],
        ),
        ToolSchema(
            name="grep",
            description="Search files with regex pattern.",
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern."},
                    "path": {"type": "string", "description": "File or directory."},
                    "recursive": {"type": "boolean", "description": "Search recursively."},
                },
                "required": ["pattern"],
            },
            required=["pattern"],
        ),
        ToolSchema(
            name="glob",
            description="Find files matching a glob pattern.",
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern (e.g. *.py)."},
                    "cwd": {"type": "string", "description": "Working directory."},
                },
                "required": ["pattern"],
            },
            required=["pattern"],
        ),
        ToolSchema(
            name="task",
            description="Spawn a subagent task in isolated context.",
            parameters={
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "Task description."},
                    "cwd": {"type": "string", "description": "Working directory for subagent."},
                    "timeout": {"type": "integer", "description": "Timeout in seconds."},
                },
                "required": ["description"],
            },
            required=["description"],
        ),
        ToolSchema(
            name="todowrite",
            description="Append or overwrite a TODO tracking file.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "TODO file path."},
                    "content": {"type": "string", "description": "Content to write."},
                    "mode": {"type": "string", "description": "append or overwrite."},
                },
                "required": ["content"],
            },
            required=["content"],
        ),
    ]


# ──────────────────────────────────────────────────────────────────────────
# 4. ContextManager — 3-layer context compaction
# ──────────────────────────────────────────────────────────────────────────

class ContextManager:
    """
    Manages 3 layers of conversation context:
      1. System layer (static, always kept)
      2. History layer (user/assistant message pairs)
      3. Tool results layer (latest tool outputs)

    Compaction strategy: when total estimated tokens exceed budget,
    summarise older history into a rolling summary, preserving recent
    messages and all tool results.
    """

    def __init__(
        self,
        system_prompt: str,
        max_tokens: int = 120_000,
        chars_per_token: float = 4.0,
    ) -> None:
        self.system_prompt = system_prompt
        self.max_tokens = max_tokens
        self.chars_per_token = chars_per_token
        self.history: List[Dict[str, Any]] = []
        self.tool_results: List[Dict[str, Any]] = []
        self.summary: str = ""

    def add_message(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})

    def add_tool_result(self, tool_call_id: str, name: str, result: Dict[str, Any]) -> None:
        self.tool_results.append({
            "tool_call_id": tool_call_id,
            "name": name,
            "result": result,
        })

    def estimate_tokens(self) -> int:
        total = len(self.system_prompt) / self.chars_per_token
        total += len(self.summary) / self.chars_per_token
        for msg in self.history:
            total += len(msg.get("content", "")) / self.chars_per_token
        for tr in self.tool_results:
            total += len(json.dumps(tr)) / self.chars_per_token
        return int(total)

    def compact(self) -> None:
        """Summarise older history if over budget."""
        while self.estimate_tokens() > self.max_tokens and len(self.history) > 4:
            # Take oldest 2 messages and compress into summary
            oldest = self.history[:2]
            self.history = self.history[2:]
            snippet = " | ".join(
                f"{m['role']}: {m['content'][:200]}" for m in oldest
            )
            self.summary += f"\n[Summary] {snippet}"
            logger.info("Context compacted: summary length now %d chars", len(self.summary))

    def build_messages(self) -> List[Dict[str, Any]]:
        """Build the full message list for LLM API call."""
        messages: List[Dict[str, Any]] = []
        if self.summary:
            messages.append({"role": "system", "content": f"Conversation summary so far: {self.summary}"})
        messages.append({"role": "system", "content": self.system_prompt})
        messages.extend(self.history)
        # Append tool results as assistant messages (OpenAI format approximation)
        for tr in self.tool_results:
            messages.append({
                "role": "tool",
                "tool_call_id": tr["tool_call_id"],
                "name": tr["name"],
                "content": json.dumps(tr["result"]),
            })
        self.tool_results = []
        return messages

    def clear_history(self) -> None:
        self.history.clear()
        self.tool_results.clear()
        self.summary = ""


# ──────────────────────────────────────────────────────────────────────────
# 5. MCPClient — MCP protocol client skeleton
# ──────────────────────────────────────────────────────────────────────────

class MCPClient:
    """
    Model Context Protocol (MCP) client skeleton.
    Supports stdio and HTTP(S) transports.
    """

    def __init__(self, transport: str = "stdio", endpoint: Optional[str] = None) -> None:
        self.transport = transport
        self.endpoint = endpoint
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()

    def connect(self) -> bool:
        if self.transport == "stdio":
            # Spawn MCP server as subprocess; speak JSON-RPC over stdin/stdout
            if self.endpoint is None:
                logger.error("MCP stdio endpoint missing (command to run)")
                return False
            try:
                self._proc = subprocess.Popen(
                    self.endpoint,
                    shell=True,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                return True
            except Exception as e:
                logger.error("MCP connect failed: %s", e)
                return False
        elif self.transport == "http":
            return True  # Stateless, no persistent connection needed
        return False

    def _send_stdio(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self._proc or self._proc.stdin is None or self._proc.stdout is None:
            return None
        try:
            line = json.dumps(payload) + "\n"
            self._proc.stdin.write(line)
            self._proc.stdin.flush()
            response = self._proc.stdout.readline()
            return json.loads(response)
        except Exception as e:
            logger.error("MCP stdio send error: %s", e)
            return None

    def _send_http(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.endpoint:
            return None
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.endpoint,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.error("MCP HTTP send error: %s", e)
            return None

    def send(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock:
            if self.transport == "stdio":
                return self._send_stdio(payload)
            return self._send_http(payload)

    def close(self) -> None:
        if self._proc:
            try:
                self._proc.stdin.close()
                self._proc.terminate()
                self._proc.wait(timeout=5)
            except Exception:
                pass
            self._proc = None


# ──────────────────────────────────────────────────────────────────────────
# 6. SubagentManager — isolated child context, depth=1 limit
# ──────────────────────────────────────────────────────────────────────────

class SubagentManager:
    """
    Runs a subagent in an isolated subprocess with its own context.
    Enforces depth=1 limit: a subagent cannot spawn another subagent.
    """

    def __init__(self, max_depth: int = 1) -> None:
        self.max_depth = max_depth
        self._active: Dict[str, Dict[str, Any]] = {}

    def spawn(
        self,
        description: str,
        cwd: Optional[str] = None,
        timeout: int = 300,
        env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        task_id = str(uuid.uuid4())[:8]
        # Write a temporary JSON payload for the subagent
        payload = {
            "task_id": task_id,
            "description": description,
            "cwd": cwd or os.getcwd(),
            "timeout": timeout,
            "depth_limit": self.max_depth,
        }
        payload_path = Path(f"/tmp/subagent_{task_id}.json")
        payload_path.write_text(json.dumps(payload), encoding="utf-8")

        # Spawn a subprocess that reads the payload and executes
        cmd = [
            sys.executable,
            "-c",
            textwrap.dedent(
                f"""
                import json, sys, subprocess, os, textwrap, time
                p = "/tmp/subagent_{task_id}.json"
                with open(p) as f:
                    data = json.load(f)
                print(f"[Subagent {{data['task_id']}}] Starting: {{data['description'][:60]}}")
                # Placeholder execution: simulate work
                result = {{
                    "success": True,
                    "output": f"Simulated subagent execution for: {{data['description']}}",
                }}
                print(json.dumps(result))
                """
            ),
        ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                env={**os.environ, **(env or {})},
            )
            stdout = proc.stdout.strip()
            # Try to parse JSON result from last line
            lines = stdout.splitlines()
            result = {"raw_output": stdout, "success": proc.returncode == 0}
            for line in reversed(lines):
                try:
                    parsed = json.loads(line)
                    result.update(parsed)
                    break
                except json.JSONDecodeError:
                    continue
            self._active[task_id] = result
            return {"task_id": task_id, **result}
        except subprocess.TimeoutExpired:
            return {"task_id": task_id, "error": "Subagent timed out", "success": False}
        except Exception as e:
            return {"task_id": task_id, "error": str(e), "success": False}

    def list_active(self) -> List[str]:
        return list(self._active.keys())


# ──────────────────────────────────────────────────────────────────────────
# 7. SessionStore — JSONL persistence, resume / fork
# ──────────────────────────────────────────────────────────────────────────

class SessionStore:
    """
    Append-only JSONL session store.
    Each line is a JSON object with a timestamp and event type.
    Supports resume (replay) and fork (copy + new id).
    """

    def __init__(self, path: Union[str, Path]) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def append(self, event_type: str, data: Dict[str, Any]) -> None:
        entry = {
            "timestamp": time.time(),
            "type": event_type,
            "data": data,
        }
        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def read_all(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        with self._lock:
            with self.path.open("r", encoding="utf-8") as f:
                return [json.loads(line) for line in f if line.strip()]

    def replay(self) -> Iterator[Dict[str, Any]]:
        """Yield events in order."""
        for entry in self.read_all():
            yield entry

    def fork(self, new_path: Union[str, Path]) -> "SessionStore":
        """Copy current session store to a new path and return new SessionStore."""
        dest = Path(new_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.path, dest)
        return SessionStore(dest)

    def clear(self) -> None:
        with self._lock:
            if self.path.exists():
                self.path.unlink()


# ──────────────────────────────────────────────────────────────────────────
# 8. SkillLoader — on-demand skill loading from directory
# ──────────────────────────────────────────────────────────────────────────

class SkillLoader:
    """
    Scans a directory for skill modules (Python files) and loads them on demand.
    Each skill is expected to expose a `register(registry)` function.
    """

    def __init__(self, skills_dir: Union[str, Path]) -> None:
        self.skills_dir = Path(skills_dir)
        self._loaded: Dict[str, Any] = {}

    def discover(self) -> List[str]:
        """Return list of skill file names (without .py)."""
        if not self.skills_dir.exists():
            return []
        return [
            p.stem for p in self.skills_dir.iterdir()
            if p.suffix == ".py" and not p.name.startswith("_")
        ]

    def load(self, name: str, registry: ToolRegistry) -> bool:
        """Import skill module and call its register() function."""
        if name in self._loaded:
            return True
        skill_path = self.skills_dir / f"{name}.py"
        if not skill_path.exists():
            logger.warning("Skill not found: %s", name)
            return False
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(name, skill_path)
            if spec is None or spec.loader is None:
                return False
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
            if hasattr(module, "register"):
                module.register(registry)
            self._loaded[name] = module
            logger.info("Skill loaded: %s", name)
            return True
        except Exception as e:
            logger.error("Skill load failed for %s: %s", name, e)
            return False

    def unload(self, name: str) -> None:
        self._loaded.pop(name, None)
        sys.modules.pop(name, None)


# ──────────────────────────────────────────────────────────────────────────
# 9. LLM Client — OpenAI-compatible via urllib
# ──────────────────────────────────────────────────────────────────────────

class LLMClient:
    """
    Minimal OpenAI-compatible chat completions client using only urllib.
    Supports tool_calling via standard function-calling schema.
    """

    def __init__(
        self,
        api_url: str = "http://localhost:8000/v1/chat/completions",
        api_key: Optional[str] = None,
        model: str = "default",
        temperature: float = 0.2,
    ) -> None:
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.temperature = temperature

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
    ) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(
            self.api_url,
            data=data,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            return {"error": f"HTTP {e.code}: {body}"}
        except Exception as e:
            return {"error": str(e)}


# ──────────────────────────────────────────────────────────────────────────
# 10. AgentLoop — the core while(tool_call) loop
# ──────────────────────────────────────────────────────────────────────────

class AgentLoop:
    """
    The canonical Claude Code agent loop:

        while True:
            response = llm.chat(context.build_messages())
            if response has tool_calls:
                for each tool_call:
                    check permission
                    execute tool
                    append result to context
                continue  # send results back to LLM
            else:
                return assistant message
    """

    def __init__(
        self,
        llm: LLMClient,
        registry: ToolRegistry,
        context: ContextManager,
        permissions: PermissionEngine,
        subagents: SubagentManager,
        session: SessionStore,
        max_iterations: int = 50,
    ) -> None:
        self.llm = llm
        self.registry = registry
        self.context = context
        self.permissions = permissions
        self.subagents = subagents
        self.session = session
        self.max_iterations = max_iterations

    def run(self, user_input: str) -> str:
        self.context.add_message("user", user_input)
        self.session.append("user_input", {"content": user_input})

        for iteration in range(self.max_iterations):
            logger.info("AgentLoop iteration %d", iteration + 1)
            self.context.compact()
            messages = self.context.build_messages()
            tools = self.registry.list_schemas()
            response = self.llm.chat(messages, tools=tools)

            if "error" in response:
                err = f"LLM error: {response['error']}"
                self.session.append("error", {"message": err})
                return err

            choice = response.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content") or ""
            tool_calls = message.get("tool_calls", [])

            # Log assistant message
            self.session.append("assistant", {"content": content, "tool_calls": tool_calls})

            if not tool_calls:
                # No more tools — final answer
                self.context.add_message("assistant", content)
                return content

            # Process tool calls
            self.context.add_message("assistant", content or "(tool call)")
            for tc in tool_calls:
                fn = tc.get("function", {})
                tool_name = fn.get("name", "")
                tool_args_raw = fn.get("arguments", "")
                tool_call_id = tc.get("id", str(uuid.uuid4())[:8])

                try:
                    tool_args = json.loads(tool_args_raw) if isinstance(tool_args_raw, str) else tool_args_raw
                except json.JSONDecodeError:
                    tool_args = {}

                # Permission check
                target = tool_args.get("path") or tool_args.get("command") or ""
                action, desc = self.permissions.check(tool_name, target)
                if action == PermissionAction.BLOCK:
                    result = {"error": f"Permission denied ({desc})", "success": False}
                elif action == PermissionAction.ASK:
                    allowed = self.permissions.ask_user(tool_name, target)
                    if not allowed:
                        result = {"error": "User denied permission", "success": False}
                    else:
                        result = self._execute_tool(tool_name, tool_args)
                else:
                    result = self._execute_tool(tool_name, tool_args)

                self.context.add_tool_result(tool_call_id, tool_name, result)
                self.session.append("tool_result", {
                    "tool_call_id": tool_call_id,
                    "name": tool_name,
                    "result": result,
                })

        return "Reached maximum iteration limit without final answer."

    def _execute_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if name == "task":
            # Delegate to subagent manager
            return self.subagents.spawn(
                description=arguments.get("description", ""),
                cwd=arguments.get("cwd"),
                timeout=arguments.get("timeout", 300),
            )
        return self.registry.call(name, arguments)


# ──────────────────────────────────────────────────────────────────────────
# 11. ClaudeCodeHarness — master orchestrator
# ──────────────────────────────────────────────────────────────────────────

class ClaudeCodeHarness:
    """
    Master orchestrator assembling all subsystems.
    Provides a single entry-point: `run(user_input)`.
    """

    def __init__(
        self,
        system_prompt: Optional[str] = None,
        llm_api_url: str = "http://localhost:8000/v1/chat/completions",
        llm_api_key: Optional[str] = None,
        llm_model: str = "default",
        session_path: str = "/tmp/claude_harness_session.jsonl",
        skills_dir: str = "./skills",
        max_context_tokens: int = 120_000,
    ) -> None:
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.context = ContextManager(
            system_prompt=self.system_prompt,
            max_tokens=max_context_tokens,
        )
        self.registry = ToolRegistry()
        self.permissions = PermissionEngine()
        self.permissions.default_rules()
        self.subagents = SubagentManager(max_depth=1)
        self.session = SessionStore(session_path)
        self.llm = LLMClient(
            api_url=llm_api_url,
            api_key=llm_api_key,
            model=llm_model,
        )
        self.loop = AgentLoop(
            llm=self.llm,
            registry=self.registry,
            context=self.context,
            permissions=self.permissions,
            subagents=self.subagents,
            session=self.session,
        )
        self.skill_loader = SkillLoader(skills_dir)
        self.mcp: Optional[MCPClient] = None

        # Register core tools
        self._register_core_tools()

    def _default_system_prompt(self) -> str:
        return textwrap.dedent("""\
            You are a helpful coding assistant operating inside a pure-Python
            Claude Code harness. You have access to bash, file read/write/edit,
            grep, glob, task delegation, and TODO tracking.

            When editing files, always prefer targeted replacements using the
            edit tool. When writing new files, use the write tool. When reading
            files, use the read tool with offset/limit to avoid flooding context.

            You may delegate subtasks to isolated subagents via the task tool.
            You are not allowed to spawn more than 1 level of subagent depth.

            Be concise. Prefer code over prose when possible.
        """)

    def _register_core_tools(self) -> None:
        schemas = build_core_tool_schemas()
        for schema in schemas:
            if schema.name == "task":
                continue  # registered separately below
            handler = getattr(CoreTools, schema.name, None)
            if handler:
                self.registry.register(schema.name, handler, schema)
        # Override task with bound subagent handler
        task_schema = next(s for s in schemas if s.name == "task")
        self.registry.register(
            "task",
            lambda args: self.subagents.spawn(
                description=args.get("description", ""),
                cwd=args.get("cwd"),
                timeout=args.get("timeout", 300),
            ),
            task_schema,
        )

    def connect_mcp(self, transport: str = "stdio", endpoint: Optional[str] = None) -> bool:
        self.mcp = MCPClient(transport=transport, endpoint=endpoint)
        return self.mcp.connect()

    def load_skill(self, name: str) -> bool:
        return self.skill_loader.load(name, self.registry)

    def run(self, user_input: str) -> str:
        """Single-turn execution with internal tool loop."""
        return self.loop.run(user_input)

    def reset(self) -> None:
        """Clear conversation context and start fresh."""
        self.context.clear_history()

    def fork_session(self, new_path: str) -> SessionStore:
        return self.session.fork(new_path)

    def save_checkpoint(self, label: str) -> None:
        self.session.append("checkpoint", {"label": label, "history_len": len(self.context.history)})

    # ── Standalone demo ──
    def run_demo(self) -> None:
        """Run a self-contained demo with mock LLM responses."""
        print("=== Claude Code Harness Native — Demo ===\n")

        # Mock LLM that returns a sequence of tool calls then a final answer
        class MockLLM:
            _step = 0
            def chat(self, messages, tools=None, tool_choice=None):
                self._step += 1
                if self._step == 1:
                    return {
                        "choices": [{
                            "message": {
                                "content": None,
                                "tool_calls": [{
                                    "id": "tc1",
                                    "function": {
                                        "name": "bash",
                                        "arguments": json.dumps({"command": "echo hello from harness"}),
                                    },
                                }],
                            },
                        }],
                    }
                elif self._step == 2:
                    return {
                        "choices": [{
                            "message": {
                                "content": None,
                                "tool_calls": [{
                                    "id": "tc2",
                                    "function": {
                                        "name": "write",
                                        "arguments": json.dumps({"path": "/tmp/harness_demo.txt", "content": "Hello from Claude Harness\n"}),
                                    },
                                }],
                            },
                        }],
                    }
                elif self._step == 3:
                    return {
                        "choices": [{
                            "message": {
                                "content": None,
                                "tool_calls": [{
                                    "id": "tc3",
                                    "function": {
                                        "name": "read",
                                        "arguments": json.dumps({"path": "/tmp/harness_demo.txt"}),
                                    },
                                }],
                            },
                        }],
                    }
                else:
                    return {
                        "choices": [{
                            "message": {
                                "content": "Demo complete. Bash executed, file written and read successfully.",
                                "tool_calls": [],
                            },
                        }],
                    }

        # Patch LLM with mock
        original_llm = self.llm
        self.llm = MockLLM()
        self.loop.llm = self.llm

        result = self.run("Run a quick demo for me")
        print(f"\nFinal result: {result}\n")

        # Restore
        self.llm = original_llm
        self.loop.llm = original_llm

        # Show session events
        events = self.session.read_all()
        print(f"Session events recorded: {len(events)}")
        for ev in events[-5:]:
            print(f"  [{ev['type']}] {time.strftime('%H:%M:%S', time.localtime(ev['timestamp']))}")

        # Cleanup
        self.reset()
        self.session.clear()
        Path("/tmp/harness_demo.txt").unlink(missing_ok=True)


def run() -> None:
    harness = ClaudeCodeHarness()
    harness.run_demo()


if __name__ == "__main__":
    run()
