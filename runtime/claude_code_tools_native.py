#!/usr/bin/env python3
"""
claude_code_tools_native.py — Claude Code Tool System (Native Python)

A pure-Python reimplementation of the Claude Code tool layer inspired by
the GHGmc2/claude-code source. 16 tools, a ToolRegistry, a permission
engine, and a self-test runner. Zero external dependencies.

Each tool follows the buildTool pattern:
  - name, description, prompt
  - input_schema (JSONSchema-like dict)
  - output_schema (JSONSchema-like dict)
  - is_enabled, is_concurrency_safe
  - call(context, **args) -> result dict
  - render_message(result) -> human-readable str
  - map_result(result) -> Any (for programatic consumers)
"""

from __future__ import annotations

import glob as stdlib_glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import traceback
import urllib.request
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _truncate(text: str, max_len: int = 8000) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _escape_ansi(text: str) -> str:
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


# ─────────────────────────────────────────────────────────────────────────────
# Permission context
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ToolPermissionContext:
    """Declarative allow/deny/ask rules for tool invocation."""

    rules: List[Dict[str, Any]] = field(default_factory=list)
    ask_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None

    @classmethod
    def default(cls) -> "ToolPermissionContext":
        return cls(rules=[])

    def add_rule(self, tool_name: str, action: str, pattern: Optional[str] = None) -> None:
        """action is 'allow', 'deny', or 'ask'."""
        self.rules.append({"tool": tool_name, "action": action, "pattern": pattern})

    def check(self, tool_name: str, args: Dict[str, Any]) -> Tuple[bool, bool]:
        """Returns (allowed: bool, needs_ask: bool)."""
        for rule in self.rules:
            if rule["tool"] != tool_name and rule["tool"] != "*":
                continue
            pat = rule.get("pattern")
            if pat and pat not in json.dumps(args):
                continue
            action = rule["action"]
            if action == "deny":
                return (False, False)
            if action == "ask":
                if self.ask_callback:
                    approved = self.ask_callback(tool_name, args)
                    return (approved, False)
                return (False, True)
            if action == "allow":
                return (True, False)
        return (True, False)


# ─────────────────────────────────────────────────────────────────────────────
# Base tool
# ─────────────────────────────────────────────────────────────────────────────


class NativeTool:
    name: str = ""
    description: str = ""
    prompt: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    is_enabled: bool = True
    is_concurrency_safe: bool = True

    def call(self, exec_ctx: Dict[str, Any], **args: Any) -> Dict[str, Any]:
        raise NotImplementedError

    def render_message(self, result: Dict[str, Any]) -> str:
        return json.dumps(result, indent=2, ensure_ascii=False)

    def map_result(self, result: Dict[str, Any]) -> Any:
        return result


# ─────────────────────────────────────────────────────────────────────────────
# 1. BashTool
# ─────────────────────────────────────────────────────────────────────────────


class NativeBashTool(NativeTool):
    name = "bash"
    description = "Execute a shell command in a controlled environment."
    prompt = (
        "Run shell commands. Prefer absolute paths. "
        "Command should be non-interactive and finish quickly."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to run"},
            "timeout": {"type": "integer", "default": 30, "description": "Timeout in seconds"},
            "cwd": {"type": "string", "description": "Working directory"},
        },
        "required": ["command"],
    }
    output_schema = {
        "type": "object",
        "properties": {
            "stdout": {"type": "string"},
            "stderr": {"type": "string"},
            "exit_code": {"type": "integer"},
            "duration_ms": {"type": "number"},
        },
    }
    is_concurrency_safe = False

    DANGEROUS_PATTERNS: Tuple[str, ...] = (
        r"rm\s+-rf\s+/",
        r"mkfs\.",
        r"dd\s+if=.*of=/dev/",
        r">\s+/dev/\w+",
        r"shutdown",
        r"reboot",
        r":\(\)\{\s*:\|\:\&\s*\};\s*:",
        r"curl\s+.*\|\s*sh",
        r"wget\s+.*\|\s*sh",
    )

    def _is_dangerous(self, cmd: str) -> bool:
        lower = cmd.lower()
        for pat in self.DANGEROUS_PATTERNS:
            if re.search(pat, lower):
                return True
        return False

    def call(self, exec_ctx: Dict[str, Any], **args: Any) -> Dict[str, Any]:
        command: str = args.get("command", "")
        timeout: int = args.get("timeout", 30)
        cwd: Optional[str] = args.get("cwd")

        if not command.strip():
            return {"error": "Empty command", "stdout": "", "stderr": "", "exit_code": -1, "duration_ms": 0}

        if self._is_dangerous(command):
            perms: ToolPermissionContext = exec_ctx.get("permissions", ToolPermissionContext.default())
            allowed, needs_ask = perms.check(self.name, args)
            if not allowed:
                return {"error": "Dangerous command blocked", "stdout": "", "stderr": "", "exit_code": -1, "duration_ms": 0}

        cwd_path = Path(cwd).resolve() if cwd else Path.cwd()
        if not cwd_path.exists():
            return {"error": f"cwd does not exist: {cwd}", "stdout": "", "stderr": "", "exit_code": -1, "duration_ms": 0}

        t0 = time.time()
        try:
            import shlex
            cmd_list = shlex.split(command) if isinstance(command, str) else command
            proc = subprocess.run(
                cmd_list,
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(cwd_path),
            )
            duration = (time.time() - t0) * 1000
            return {
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "exit_code": proc.returncode,
                "duration_ms": round(duration, 2),
            }
        except subprocess.TimeoutExpired:
            return {"error": f"Timed out after {timeout}s", "stdout": "", "stderr": "", "exit_code": -1, "duration_ms": timeout * 1000}
        except Exception as exc:
            return {"error": str(exc), "stdout": "", "stderr": "", "exit_code": -1, "duration_ms": 0}

    def render_message(self, result: Dict[str, Any]) -> str:
        if "error" in result:
            return f"❌ bash: {result['error']}"
        out = result.get("stdout", "")
        err = result.get("stderr", "")
        code = result.get("exit_code", 0)
        lines = []
        if out:
            lines.append(out)
        if err:
            lines.append(f"[stderr] {err}")
        lines.append(f"exit {code}  ({result.get('duration_ms', 0)} ms)")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 2. FileReadTool
# ─────────────────────────────────────────────────────────────────────────────


class NativeFileReadTool(NativeTool):
    name = "read"
    description = "Read the contents of a file."
    prompt = "Read a file by absolute or relative path. Supports offset/limit for large files."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path"},
            "offset": {"type": "integer", "default": 1, "description": "Line to start from (1-indexed)"},
            "limit": {"type": "integer", "default": 200, "description": "Max lines to read"},
        },
        "required": ["path"],
    }
    output_schema = {
        "type": "object",
        "properties": {
            "content": {"type": "string"},
            "lines_read": {"type": "integer"},
            "total_lines": {"type": "integer"},
            "truncated": {"type": "boolean"},
        },
    }

    def call(self, exec_ctx: Dict[str, Any], **args: Any) -> Dict[str, Any]:
        path = Path(args.get("path", "")).expanduser()
        if not path.is_absolute():
            path = Path(exec_ctx.get("cwd", ".")) / path
        path = path.resolve()

        if not path.exists():
            return {"error": f"File not found: {path}", "content": "", "lines_read": 0, "total_lines": 0, "truncated": False}
        if path.is_dir():
            return {"error": f"Is a directory: {path}", "content": "", "lines_read": 0, "total_lines": 0, "truncated": False}

        offset: int = max(1, args.get("offset", 1))
        limit: int = args.get("limit", 200)

        try:
            with path.open("r", encoding="utf-8", errors="replace") as fh:
                all_lines = fh.readlines()
        except Exception as exc:
            return {"error": str(exc), "content": "", "lines_read": 0, "total_lines": 0, "truncated": False}

        total = len(all_lines)
        start = offset - 1
        end = min(start + limit, total)
        selected = all_lines[start:end]
        truncated = end < total

        content = "".join(selected)
        return {
            "content": content,
            "lines_read": len(selected),
            "total_lines": total,
            "truncated": truncated,
        }

    def render_message(self, result: Dict[str, Any]) -> str:
        if "error" in result:
            return f"❌ read: {result['error']}"
        hdr = f"lines {result.get('lines_read')} / {result.get('total_lines')}"
        if result.get("truncated"):
            hdr += " (truncated)"
        return f"📄 {hdr}\n" + result.get("content", "")


# ─────────────────────────────────────────────────────────────────────────────
# 3. FileWriteTool
# ─────────────────────────────────────────────────────────────────────────────


class NativeFileWriteTool(NativeTool):
    name = "write"
    description = "Write content to a file, creating it if necessary."
    prompt = "Write a file. Will overwrite by default unless overwrite=false."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
            "overwrite": {"type": "boolean", "default": True},
        },
        "required": ["path", "content"],
    }
    output_schema = {
        "type": "object",
        "properties": {"bytes_written": {"type": "integer"}, "path": {"type": "string"}},
    }

    def call(self, exec_ctx: Dict[str, Any], **args: Any) -> Dict[str, Any]:
        raw_path = args.get("path", "")
        content: str = args.get("content", "")
        overwrite: bool = args.get("overwrite", True)

        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = Path(exec_ctx.get("cwd", ".")) / path
        path = path.resolve()

        if path.exists() and not overwrite:
            return {"error": f"File exists and overwrite=false: {path}", "bytes_written": 0, "path": str(path)}

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as fh:
                fh.write(content)
            return {"bytes_written": len(content.encode("utf-8")), "path": str(path)}
        except Exception as exc:
            return {"error": str(exc), "bytes_written": 0, "path": str(path)}

    def render_message(self, result: Dict[str, Any]) -> str:
        if "error" in result:
            return f"❌ write: {result['error']}"
        return f"✏️  wrote {result['bytes_written']} bytes → {result['path']}"


# ─────────────────────────────────────────────────────────────────────────────
# 4. FileEditTool
# ─────────────────────────────────────────────────────────────────────────────


class NativeFileEditTool(NativeTool):
    name = "edit"
    description = "Search-and-replace editing of a file."
    prompt = "Replace old_text with new_text in a file. Undo is supported if history is kept."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "old_text": {"type": "string"},
            "new_text": {"type": "string"},
        },
        "required": ["path", "old_text", "new_text"],
    }
    output_schema = {
        "type": "object",
        "properties": {
            "replacements": {"type": "integer"},
            "path": {"type": "string"},
            "backup_path": {"type": "string"},
        },
    }

    # Simple in-memory undo store: path -> list of (backup_path,)
    _undo_store: Dict[str, List[str]] = {}
    _lock = threading.Lock()

    def call(self, exec_ctx: Dict[str, Any], **args: Any) -> Dict[str, Any]:
        raw_path = args.get("path", "")
        old_text: str = args.get("old_text", "")
        new_text: str = args.get("new_text", "")

        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = Path(exec_ctx.get("cwd", ".")) / path
        path = path.resolve()

        if not path.exists():
            return {"error": f"File not found: {path}", "replacements": 0, "path": str(path), "backup_path": ""}

        try:
            with path.open("r", encoding="utf-8", errors="replace") as fh:
                original = fh.read()
        except Exception as exc:
            return {"error": str(exc), "replacements": 0, "path": str(path), "backup_path": ""}

        count = original.count(old_text)
        if count == 0:
            return {"error": "old_text not found", "replacements": 0, "path": str(path), "backup_path": ""}

        modified = original.replace(old_text, new_text)

        # Backup
        backup_path = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, backup_path)

        with self._lock:
            self._undo_store.setdefault(str(path), []).append(str(backup_path))

        with path.open("w", encoding="utf-8") as fh:
            fh.write(modified)

        return {
            "replacements": count,
            "path": str(path),
            "backup_path": str(backup_path),
        }

    def render_message(self, result: Dict[str, Any]) -> str:
        if "error" in result:
            return f"❌ edit: {result['error']}"
        return f"🔧 {result['replacements']} replacement(s) in {result['path']} (backup: {result['backup_path']})"


# ─────────────────────────────────────────────────────────────────────────────
# 5. GlobTool
# ─────────────────────────────────────────────────────────────────────────────


class NativeGlobTool(NativeTool):
    name = "glob"
    description = "Match file paths using glob patterns."
    prompt = "Find files matching a glob pattern like '**/*.py'."
    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "cwd": {"type": "string", "description": "Directory to search from"},
        },
        "required": ["pattern"],
    }
    output_schema = {
        "type": "object",
        "properties": {"matches": {"type": "array", "items": {"type": "string"}}, "count": {"type": "integer"}},
    }

    def call(self, exec_ctx: Dict[str, Any], **args: Any) -> Dict[str, Any]:
        pattern: str = args.get("pattern", "")
        cwd: Optional[str] = args.get("cwd")
        base = Path(cwd).resolve() if cwd else Path(exec_ctx.get("cwd", ".")).resolve()

        matches = [str(p) for p in base.glob(pattern) if p.exists()]
        return {"matches": matches, "count": len(matches)}

    def render_message(self, result: Dict[str, Any]) -> str:
        lines = [f"🔍 {result['count']} match(es):"]
        for m in result.get("matches", [])[:20]:
            lines.append(f"  • {m}")
        if result["count"] > 20:
            lines.append(f"  … and {result['count'] - 20} more")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 6. GrepTool
# ─────────────────────────────────────────────────────────────────────────────


class NativeGrepTool(NativeTool):
    name = "grep"
    description = "Search file contents with a regex pattern."
    prompt = "Search files recursively for a pattern. Returns file, line number, and snippet."
    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "path": {"type": "string", "description": "Directory or file to search"},
            "max_results": {"type": "integer", "default": 50},
        },
        "required": ["pattern"],
    }
    output_schema = {
        "type": "object",
        "properties": {
            "matches": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "file": {"type": "string"},
                        "line": {"type": "integer"},
                        "text": {"type": "string"},
                    },
                },
            },
            "count": {"type": "integer"},
        },
    }

    def call(self, exec_ctx: Dict[str, Any], **args: Any) -> Dict[str, Any]:
        pattern: str = args.get("pattern", "")
        raw_path = args.get("path", ".")
        max_results: int = args.get("max_results", 50)

        base = Path(raw_path).expanduser()
        if not base.is_absolute():
            base = Path(exec_ctx.get("cwd", ".")) / base
        base = base.resolve()

        if not base.exists():
            return {"error": f"Path not found: {base}", "matches": [], "count": 0}

        targets: List[Path] = [base] if base.is_file() else list(base.rglob("*"))

        matches: List[Dict[str, Any]] = []
        try:
            rx = re.compile(pattern)
        except re.error as exc:
            return {"error": f"Invalid regex: {exc}", "matches": [], "count": 0}

        for p in targets:
            if not p.is_file():
                continue
            # Skip binary-ish files by extension
            if p.suffix in (".pyc", ".pyo", ".so", ".dll", ".exe", ".png", ".jpg", ".mp3", ".mp4"):
                continue
            try:
                with p.open("r", encoding="utf-8", errors="replace") as fh:
                    for i, line in enumerate(fh, start=1):
                        if rx.search(line):
                            matches.append({"file": str(p), "line": i, "text": line.rstrip("\n")})
                            if len(matches) >= max_results:
                                break
            except Exception:
                continue
            if len(matches) >= max_results:
                break

        return {"matches": matches, "count": len(matches)}

    def render_message(self, result: Dict[str, Any]) -> str:
        if "error" in result:
            return f"❌ grep: {result['error']}"
        lines = [f"🧵 {result['count']} match(es):"]
        for m in result.get("matches", [])[:20]:
            lines.append(f"  {m['file']}:{m['line']}  {m['text'][:120]}")
        if result["count"] > 20:
            lines.append(f"  … and {result['count'] - 20} more")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 7. TodoWriteTool
# ─────────────────────────────────────────────────────────────────────────────


class NativeTodoWriteTool(NativeTool):
    name = "todowrite"
    description = "Manage a todo / task list."
    prompt = "Add, update, or remove todos. Each todo has an id, text, and status."
    input_schema = {
        "type": "object",
        "properties": {
            "todos": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "text": {"type": "string"},
                        "status": {"type": "string", "enum": ["todo", "in_progress", "done"]},
                        "priority": {"type": "string", "enum": ["low", "normal", "high"]},
                    },
                    "required": ["id", "text", "status"],
                },
            },
            "mode": {"type": "string", "enum": ["replace", "append", "update"], "default": "replace"},
        },
        "required": ["todos"],
    }
    output_schema = {
        "type": "object",
        "properties": {
            "todos": {"type": "array"},
            "updated": {"type": "integer"},
        },
    }

    _store: Dict[str, List[Dict[str, Any]]] = {}
    _lock = threading.Lock()

    def call(self, exec_ctx: Dict[str, Any], **args: Any) -> Dict[str, Any]:
        session_id: str = exec_ctx.get("session_id", "default")
        todos: List[Dict[str, Any]] = args.get("todos", [])
        mode: str = args.get("mode", "replace")

        with self._lock:
            existing = self._store.get(session_id, [])

            if mode == "replace":
                merged = {t["id"]: t for t in todos}
            elif mode == "append":
                merged = {t["id"]: t for t in existing}
                for t in todos:
                    merged[t["id"]] = t
            else:  # update
                merged = {t["id"]: t for t in existing}
                for t in todos:
                    if t["id"] in merged:
                        merged[t["id"]].update(t)
                    else:
                        merged[t["id"]] = t

            new_list = list(merged.values())
            self._store[session_id] = new_list

        return {"todos": new_list, "updated": len(todos)}

    def render_message(self, result: Dict[str, Any]) -> str:
        lines = [f"📝 Todos ({len(result['todos'])} total):"]
        for t in result.get("todos", [])[:15]:
            icon = {"todo": "⬜", "in_progress": "🔄", "done": "✅"}.get(t.get("status"), "⬜")
            lines.append(f"  {icon} [{t.get('id')}] {t.get('text')} ({t.get('priority', 'normal')})")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 8. TaskCreateTool
# ─────────────────────────────────────────────────────────────────────────────


class NativeTaskCreateTool(NativeTool):
    name = "task"
    description = "Create a sub-task with description and metadata."
    prompt = "Create a named task that can be tracked. Returns a task_id."
    input_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "description": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["name", "description"],
    }
    output_schema = {
        "type": "object",
        "properties": {
            "task_id": {"type": "string"},
            "name": {"type": "string"},
            "created_at": {"type": "string"},
        },
    }

    _tasks: Dict[str, Dict[str, Any]] = {}
    _lock = threading.Lock()
    _counter = 0

    def call(self, exec_ctx: Dict[str, Any], **args: Any) -> Dict[str, Any]:
        name: str = args.get("name", "")
        description: str = args.get("description", "")
        tags: List[str] = args.get("tags", [])

        with self._lock:
            NativeTaskCreateTool._counter += 1
            task_id = f"task-{NativeTaskCreateTool._counter:04d}-{uuid.uuid4().hex[:6]}"

        task = {
            "task_id": task_id,
            "name": name,
            "description": description,
            "tags": tags,
            "created_at": _utc_now(),
            "status": "created",
        }
        with self._lock:
            self._tasks[task_id] = task
        return task

    def render_message(self, result: Dict[str, Any]) -> str:
        return f"📌 Created task [{result['task_id']}] {result['name']}"


# ─────────────────────────────────────────────────────────────────────────────
# 9. TaskOutputTool
# ─────────────────────────────────────────────────────────────────────────────


class NativeTaskOutputTool(NativeTool):
    name = "taskoutput"
    description = "Read the output / status of a previously created task."
    prompt = "Retrieve task details by task_id."
    input_schema = {
        "type": "object",
        "properties": {"task_id": {"type": "string"}},
        "required": ["task_id"],
    }
    output_schema = {
        "type": "object",
        "properties": {
            "found": {"type": "boolean"},
            "task": {"type": "object"},
        },
    }

    def call(self, exec_ctx: Dict[str, Any], **args: Any) -> Dict[str, Any]:
        task_id: str = args.get("task_id", "")
        task = NativeTaskCreateTool._tasks.get(task_id)
        if task:
            return {"found": True, "task": task}
        return {"found": False, "task": None}

    def render_message(self, result: Dict[str, Any]) -> str:
        if not result["found"]:
            return "❌ task not found"
        t = result["task"]
        return f"📋 [{t['task_id']}] {t['name']} — {t['status']} (created {t['created_at']})"


# ─────────────────────────────────────────────────────────────────────────────
# 10. WebSearchTool
# ─────────────────────────────────────────────────────────────────────────────


class NativeWebSearchTool(NativeTool):
    name = "websearch"
    description = "Search the web and return summarized results."
    prompt = "Perform a web search query. Returns title/link/snippet summaries. (Mock if no API key)."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "num_results": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    }
    output_schema = {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "link": {"type": "string"},
                        "snippet": {"type": "string"},
                    },
                },
            },
            "query": {"type": "string"},
        },
    }
    is_concurrency_safe = False

    def call(self, exec_ctx: Dict[str, Any], **args: Any) -> Dict[str, Any]:
        query: str = args.get("query", "")
        num_results: int = args.get("num_results", 5)

        # DuckDuckGo HTML scraping (no API key needed)
        ddg_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        try:
            req = urllib.request.Request(
                ddg_url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; Bot/0.1)"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except Exception as exc:
            return {"error": str(exc), "results": [], "query": query}

        results: List[Dict[str, str]] = []
        # Quick regex parse of DDG results
        result_blocks = re.findall(
            r'<a rel="nofollow" class="result__a" href="(.*?)">(.*?)</a>.*?<a class="result__snippet">(.*?)</a>',
            html,
            re.S,
        )
        for href, title, snippet in result_blocks[:num_results]:
            # Unescape basic HTML entities
            title = title.replace("<b>", "").replace("</b>", "").replace("&quot;", '"').replace("&#x27;", "'")
            snippet = snippet.replace("<b>", "").replace("</b>", "").replace("&quot;", '"').replace("&#x27;", "'")
            results.append({"title": title.strip(), "link": href.strip(), "snippet": snippet.strip()})

        if not results:
            # Fallback: mock results so demos never break
            results = [
                {"title": f"Result for '{query}'", "link": "#", "snippet": "(Search returned no parseable results — network or layout may have changed.)"}
            ]

        return {"results": results, "query": query}

    def render_message(self, result: Dict[str, Any]) -> str:
        if "error" in result:
            return f"❌ websearch: {result['error']}"
        lines = [f"🌐 Search: '{result['query']}'"]
        for r in result.get("results", []):
            lines.append(f"  • {r['title']}\n    {r['link']}\n    {_truncate(r['snippet'], 200)}")
        return "\n".join(lines)


# Need urllib.parse import for quote
import urllib.parse  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# 11. WebFetchTool
# ─────────────────────────────────────────────────────────────────────────────


class NativeWebFetchTool(NativeTool):
    name = "webfetch"
    description = "Fetch a URL and return its text content."
    prompt = "Download a web page and extract readable text. Truncates if too long."
    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "max_chars": {"type": "integer", "default": 8000},
        },
        "required": ["url"],
    }
    output_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "title": {"type": "string"},
            "text": {"type": "string"},
            "truncated": {"type": "boolean"},
        },
    }
    is_concurrency_safe = False

    def call(self, exec_ctx: Dict[str, Any], **args: Any) -> Dict[str, Any]:
        url: str = args.get("url", "")
        max_chars: int = args.get("max_chars", 8000)

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except Exception as exc:
            return {"error": str(exc), "url": url, "title": "", "text": "", "truncated": False}

        # Crude HTML→text extraction
        text = re.sub(r"<script[^>]*>.*?</script>", "", raw, flags=re.S)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        text = text.replace("&nbsp;", " ").replace("&quot;", '"').replace("&amp;", "&")
        text = " ".join(text.split())

        title_match = re.search(r"<title[^>]*>(.*?)</title>", raw, re.S)
        title = title_match.group(1).strip() if title_match else ""

        truncated = len(text) > max_chars
        return {
            "url": url,
            "title": title,
            "text": text[:max_chars] + ("..." if truncated else ""),
            "truncated": truncated,
        }

    def render_message(self, result: Dict[str, Any]) -> str:
        if "error" in result:
            return f"❌ webfetch: {result['error']}"
        t = result.get("title", "")
        flag = " (truncated)" if result.get("truncated") else ""
        return f"🌍 {t}{flag}\n{_truncate(result['text'], 600)}"


# ─────────────────────────────────────────────────────────────────────────────
# 12. AgentTool
# ─────────────────────────────────────────────────────────────────────────────


class NativeAgentTool(NativeTool):
    name = "agent"
    description = "Spawn a sub-agent with isolated context to perform work."
    prompt = "Create a sub-agent task. It runs in isolation and returns output."
    input_schema = {
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "Description of work for the sub-agent"},
            "instructions": {"type": "string", "description": "Detailed instructions"},
        },
        "required": ["task"],
    }
    output_schema = {
        "type": "object",
        "properties": {
            "agent_id": {"type": "string"},
            "status": {"type": "string"},
            "result": {"type": "string"},
        },
    }
    is_concurrency_safe = False

    _agents: Dict[str, Dict[str, Any]] = {}
    _lock = threading.Lock()
    _counter = 0

    def call(self, exec_ctx: Dict[str, Any], **args: Any) -> Dict[str, Any]:
        task_desc: str = args.get("task", "")
        instructions: str = args.get("instructions", "")

        with self._lock:
            NativeAgentTool._counter += 1
            agent_id = f"agent-{NativeAgentTool._counter:03d}-{uuid.uuid4().hex[:6]}"

        # Mock execution: echo instructions as "result"
        result_text = f"[Sub-agent {agent_id}]\nTask: {task_desc}\nInstructions: {instructions}\n\n(Mock result: sub-agent completed successfully.)"

        record = {
            "agent_id": agent_id,
            "status": "completed",
            "result": result_text,
            "created_at": _utc_now(),
        }
        with self._lock:
            self._agents[agent_id] = record
        return record

    def render_message(self, result: Dict[str, Any]) -> str:
        return f"🤖 Sub-agent {result['agent_id']} → {result['status']}"


# ─────────────────────────────────────────────────────────────────────────────
# 13. SkillTool
# ─────────────────────────────────────────────────────────────────────────────


class NativeSkillTool(NativeTool):
    name = "skill"
    description = "Load and execute a skill from the skills directory."
    prompt = "Run a named skill module. Looks in the configured skills directory."
    input_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Skill name / module name"},
            "args": {"type": "object", "default": {}, "description": "Arguments passed to the skill"},
        },
        "required": ["name"],
    }
    output_schema = {
        "type": "object",
        "properties": {"success": {"type": "boolean"}, "output": {"type": "string"}, "skill": {"type": "string"}},
    }

    def call(self, exec_ctx: Dict[str, Any], **args: Any) -> Dict[str, Any]:
        name: str = args.get("name", "")
        skill_args: Dict[str, Any] = args.get("args", {})
        skills_dir = Path(exec_ctx.get("skills_dir", "./skills"))

        skill_file = skills_dir / f"{name}.py"
        if not skill_file.exists():
            return {"success": False, "output": f"Skill not found: {skill_file}", "skill": name}

        # Mock: just read and echo first docstring line
        try:
            with skill_file.open("r", encoding="utf-8") as fh:
                lines = fh.readlines()[:10]
            doc = ""
            for line in lines:
                if line.strip().startswith('"""') or line.strip().startswith("'''"):
                    doc = line.strip().strip('"').strip("'")
                    break
            output = f"Skill '{name}' loaded. Doc hint: {doc or '(no docstring)'}"
            return {"success": True, "output": output, "skill": name}
        except Exception as exc:
            return {"success": False, "output": str(exc), "skill": name}

    def render_message(self, result: Dict[str, Any]) -> str:
        icon = "✅" if result["success"] else "❌"
        return f"{icon} skill '{result['skill']}': {result['output']}"


# ─────────────────────────────────────────────────────────────────────────────
# 14. BriefTool
# ─────────────────────────────────────────────────────────────────────────────


class NativeBriefTool(NativeTool):
    name = "brief"
    description = "Summarize conversation context for compaction."
    prompt = "Produce a condensed summary of the current session context."
    input_schema = {
        "type": "object",
        "properties": {
            "context": {"type": "string", "description": "Full context text to summarize"},
            "max_words": {"type": "integer", "default": 150},
        },
        "required": ["context"],
    }
    output_schema = {
        "type": "object",
        "properties": {"summary": {"type": "string"}, "original_length": {"type": "integer"}},
    }

    def call(self, exec_ctx: Dict[str, Any], **args: Any) -> Dict[str, Any]:
        full: str = args.get("context", "")
        max_words: int = args.get("max_words", 150)

        sentences = re.split(r"(?<=[.!?])\s+", full)
        summary_parts: List[str] = []
        word_count = 0
        for s in sentences:
            w = len(s.split())
            if word_count + w > max_words:
                break
            summary_parts.append(s)
            word_count += w

        return {"summary": " ".join(summary_parts), "original_length": len(full)}

    def render_message(self, result: Dict[str, Any]) -> str:
        ratio = len(result["summary"]) / max(1, result["original_length"])
        return f"📝 Brief ({ratio:.0%}): {result['summary'][:280]}"


# ─────────────────────────────────────────────────────────────────────────────
# 15. ConfigTool
# ─────────────────────────────────────────────────────────────────────────────


class NativeConfigTool(NativeTool):
    name = "config"
    description = "Read or write configuration settings."
    prompt = "Get or set a configuration key. Keys are stored in a simple JSON file."
    input_schema = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["get", "set", "list"], "default": "get"},
            "key": {"type": "string"},
            "value": {},
        },
        "required": [],
    }
    output_schema = {
        "type": "object",
        "properties": {"success": {"type": "boolean"}, "data": {}},
    }

    _config: Dict[str, Any] = {}
    _lock = threading.Lock()
    _persist_path: Optional[Path] = None

    def _persist(self) -> None:
        if self._persist_path:
            try:
                with self._persist_path.open("w", encoding="utf-8") as fh:
                    json.dump(self._config, fh, indent=2)
            except Exception:
                pass

    def _load(self) -> None:
        if self._persist_path and self._persist_path.exists():
            try:
                with self._persist_path.open("r", encoding="utf-8") as fh:
                    self._config = json.load(fh)
            except Exception:
                self._config = {}

    def call(self, exec_ctx: Dict[str, Any], **args: Any) -> Dict[str, Any]:
        cfg_path = exec_ctx.get("config_path")
        if cfg_path:
            NativeConfigTool._persist_path = Path(cfg_path)
            self._load()

        action: str = args.get("action", "get")
        key: str = args.get("key", "")
        value = args.get("value")

        with self._lock:
            if action == "list":
                return {"success": True, "data": dict(self._config)}
            if action == "get":
                return {"success": key in self._config, "data": self._config.get(key)}
            if action == "set":
                if key:
                    self._config[key] = value
                    self._persist()
                    return {"success": True, "data": value}
                return {"success": False, "data": "Missing key"}
        return {"success": False, "data": "Unknown action"}

    def render_message(self, result: Dict[str, Any]) -> str:
        if not result["success"]:
            return f"⚙️ config failed: {result['data']}"
        return f"⚙️ config → {json.dumps(result['data'], ensure_ascii=False)[:200]}"


# ─────────────────────────────────────────────────────────────────────────────
# 16. LSPTool (mock)
# ─────────────────────────────────────────────────────────────────────────────


class NativeLSPTool(NativeTool):
    name = "lsp"
    description = "Language Server Protocol integration (mock)."
    prompt = "Send an LSP method request. (Mock: returns fake responses for common methods)."
    input_schema = {
        "type": "object",
        "properties": {
            "method": {"type": "string", "description": "LSP method name"},
            "params": {"type": "object", "default": {}},
        },
        "required": ["method"],
    }
    output_schema = {
        "type": "object",
        "properties": {"success": {"type": "boolean"}, "result": {}},
    }
    is_concurrency_safe = False

    def call(self, exec_ctx: Dict[str, Any], **args: Any) -> Dict[str, Any]:
        method: str = args.get("method", "")
        params: Dict[str, Any] = args.get("params", {})

        # Mock responses for well-known methods
        mock_results: Dict[str, Any] = {
            "initialize": {"capabilities": {"textDocumentSync": 1, "hoverProvider": True, "completionProvider": {"triggerCharacters": ["." , ":"]}}},
            "textDocument/hover": {"contents": {"kind": "markdown", "value": "*(mock hover content)*"}},
            "textDocument/completion": {"isIncomplete": False, "items": [{"label": "mock_completion", "kind": 1}]},
            "textDocument/definition": {"uri": params.get("textDocument", {}).get("uri", ""), "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 1}}},
            "shutdown": None,
            "exit": None,
        }

        result = mock_results.get(method, {"note": "Unmocked LSP method — returning empty result"})
        return {"success": True, "result": result}

    def render_message(self, result: Dict[str, Any]) -> str:
        return f"🔌 LSP {result['result']}"


# ─────────────────────────────────────────────────────────────────────────────
# ToolRegistry
# ─────────────────────────────────────────────────────────────────────────────


class ToolRegistry:
    """Manages all tools: register, get, list, validate."""

    def __init__(self) -> None:
        self._tools: Dict[str, NativeTool] = {}
        self._lock = threading.Lock()

    def register(self, tool: NativeTool) -> None:
        with self._lock:
            self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[NativeTool]:
        with self._lock:
            return self._tools.get(name)

    def list_enabled(self) -> List[str]:
        with self._lock:
            return [name for name, t in self._tools.items() if t.is_enabled]

    def list_all(self) -> List[str]:
        with self._lock:
            return list(self._tools.keys())

    def validate_schema(self, name: str, args: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        tool = self.get(name)
        if not tool:
            return (False, f"Unknown tool: {name}")
        schema = tool.input_schema
        required = schema.get("required", [])
        props = schema.get("properties", {})
        for key in required:
            if key not in args:
                return (False, f"Missing required arg: {key}")
        for key, val in args.items():
            prop = props.get(key)
            if prop and "type" in prop:
                expected = prop["type"]
                actual = type(val).__name__
                type_map = {
                    "string": str,
                    "integer": int,
                    "number": (int, float),
                    "boolean": bool,
                    "array": list,
                    "object": dict,
                }
                if expected in type_map and not isinstance(val, type_map[expected]):
                    return (False, f"Type mismatch for '{key}': expected {expected}, got {actual}")
        return (True, None)

    def call(self, tool_name: str, exec_ctx: Dict[str, Any], **args: Any) -> Dict[str, Any]:
        tool = self.get(tool_name)
        if not tool:
            return {"error": f"Unknown tool: {tool_name}"}
        ok, err = self.validate_schema(tool_name, args)
        if not ok:
            return {"error": err}
        try:
            return tool.call(exec_ctx, **args)
        except Exception as exc:
            return {"error": f"Tool execution failed: {exc}", "traceback": traceback.format_exc()}

    def build_default_registry(self) -> "ToolRegistry":
        for cls in (
            NativeBashTool,
            NativeFileReadTool,
            NativeFileWriteTool,
            NativeFileEditTool,
            NativeGlobTool,
            NativeGrepTool,
            NativeTodoWriteTool,
            NativeTaskCreateTool,
            NativeTaskOutputTool,
            NativeWebSearchTool,
            NativeWebFetchTool,
            NativeAgentTool,
            NativeSkillTool,
            NativeBriefTool,
            NativeConfigTool,
            NativeLSPTool,
        ):
            self.register(cls())
        return self


# ─────────────────────────────────────────────────────────────────────────────
# Self-test runner
# ─────────────────────────────────────────────────────────────────────────────


def run_self_test() -> None:
    print("=" * 60)
    print("Claude Code Tools Native — Self-Test")
    print("=" * 60)

    registry = ToolRegistry().build_default_registry()
    ctx = {"cwd": ".", "session_id": f"demo-{uuid.uuid4().hex[:6]}"}

    tmp_dir = Path(tempfile.mkdtemp(prefix="cc_tools_test_"))
    demo_file = tmp_dir / "demo.py"
    demo_file.write_text("# hello world\nprint('hi')\n", encoding="utf-8")
    ctx["cwd"] = str(tmp_dir)

    def run(tool_name: str, **kwargs: Any) -> None:
        print(f"\n--- {tool_name} ---")
        result = registry.call(tool_name, ctx, **kwargs)
        tool = registry.get(tool_name)
        if tool:
            print(tool.render_message(result))
        else:
            print(json.dumps(result, indent=2))

    # 1 BashTool
    run("bash", command=f"echo 'hello from bash' && ls {tmp_dir}")

    # 2 FileReadTool
    run("read", path=str(demo_file))

    # 3 FileWriteTool
    run("write", path=str(tmp_dir / "new.txt"), content="fresh content")
    run("read", path=str(tmp_dir / "new.txt"))

    # 4 FileEditTool
    run("edit", path=str(demo_file), old_text="print('hi')", new_text="print('hello, edited')")
    run("read", path=str(demo_file))

    # 5 GlobTool
    run("glob", pattern="*.py")

    # 6 GrepTool
    run("grep", pattern="hello", path=str(tmp_dir))

    # 7 TodoWriteTool
    run("todowrite", todos=[{"id": "1", "text": "Build tools", "status": "done", "priority": "high"}])

    # 8 TaskCreateTool
    run("task", name="Research", description="Deep dive into Polymarket", tags=["trading", "hft"])

    # 9 TaskOutputTool
    tasks = NativeTaskCreateTool._tasks
    if tasks:
        first_id = next(iter(tasks))
        run("taskoutput", task_id=first_id)

    # 10 WebSearchTool
    run("websearch", query="python standard library", num_results=3)

    # 11 WebFetchTool
    run("webfetch", url="https://example.com", max_chars=500)

    # 12 AgentTool
    run("agent", task="Analyze orderbook", instructions="Fetch L2 data and compute imbalance.")

    # 13 SkillTool (mock skill dir)
    (tmp_dir / "skills").mkdir(exist_ok=True)
    (tmp_dir / "skills" / "test_skill.py").write_text('"""A test skill."""\n', encoding="utf-8")
    ctx["skills_dir"] = str(tmp_dir / "skills")
    run("skill", name="test_skill")

    # 14 BriefTool
    run("brief", context="This is a long conversation. We discussed many things. The user wants a summary. " * 20)

    # 15 ConfigTool
    run("config", action="set", key="theme", value="dark")
    run("config", action="get", key="theme")
    run("config", action="list")

    # 16 LSPTool
    run("lsp", method="initialize", params={})
    run("lsp", method="textDocument/hover", params={"textDocument": {"uri": "file:///test.py"}, "position": {"line": 1, "character": 5}})

    # Permission test: dangerous command
    print("\n--- Permission Block Test ---")
    perms = ToolPermissionContext.default()
    perms.add_rule("bash", "deny", pattern="rm -rf /")
    ctx_denied = dict(ctx, permissions=perms)
    res = registry.call("bash", ctx_denied, command="rm -rf /tmp/fake")
    # The deny pattern checks json dump; 'rm -rf /' won't match 'rm -rf /tmp/fake' so allow.
    # Let's test exact match via a stricter pattern:
    perms2 = ToolPermissionContext.default()
    perms2.add_rule("bash", "deny", pattern="rm -rf")
    ctx_denied2 = dict(ctx, permissions=perms2)
    res2 = registry.call("bash", ctx_denied2, command="rm -rf /tmp/fake")
    print(registry.get("bash").render_message(res2))

    print("\n" + "=" * 60)
    print(f"Enabled tools: {registry.list_enabled()}")
    print(f"All tools:     {registry.list_all()}")
    print("Self-test complete.")
    print("=" * 60)

    # Cleanup
    shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    run_self_test()
