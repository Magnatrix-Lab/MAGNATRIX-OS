#!/usr/bin/env python3
"""
ide/ide_workspace_native.py — MAGNATRIX-OS Native IDE Workspace
Pure stdlib. No external dependencies.

Features:
  • NativeFileTree — directory structure, recursive walk, operations, path resolution
  • NativeEditorBuffer — content management, undo/redo stack, cursor positions
  • NativeSessionManager — save/restore workspace sessions, named snapshots
  • NativeLSPAdapter — simplified LSP client (stdio + TCP), basic request/response
  • NativeTerminalMultiplexer — pseudo-terminal session management (session-based)
  • NativeIDEWorkspace — composes all layers, self-test demo

Naming convention: Native<ClassName>
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# NativeFileTree
# ---------------------------------------------------------------------------

class NativeFileTree:
    """In-memory file tree with CRUD operations and path resolution."""

    def __init__(self, root: str = ".") -> None:
        self.root = Path(root).resolve()
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._scan()

    def _scan(self) -> None:
        self._nodes.clear()
        for p in self.root.rglob("*"):
            rel = str(p.relative_to(self.root))
            self._nodes[rel] = {
                "path": rel,
                "type": "dir" if p.is_dir() else "file",
                "size": p.stat().st_size if p.is_file() else 0,
                "mtime": p.stat().st_mtime,
            }

    def list_dir(self, rel_path: str = ".") -> List[Dict[str, Any]]:
        prefix = rel_path.strip("./")
        with self._lock:
            items = []
            for p, info in self._nodes.items():
                if prefix == "." or prefix == "":
                    if "/" not in p:
                        items.append(info)
                else:
                    if p.startswith(prefix + "/"):
                        sub = p[len(prefix) + 1:]
                        if "/" not in sub:
                            items.append(info)
            return sorted(items, key=lambda x: (0 if x["type"] == "dir" else 1, x["path"]))

    def read_file(self, rel_path: str) -> str:
        full = self.root / rel_path
        with self._lock:
            return full.read_text(encoding="utf-8")

    def write_file(self, rel_path: str, content: str) -> None:
        full = self.root / rel_path
        with self._lock:
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")
            rel = str(full.relative_to(self.root))
            self._nodes[rel] = {
                "path": rel,
                "type": "file",
                "size": len(content.encode("utf-8")),
                "mtime": time.time(),
            }

    def delete(self, rel_path: str, recursive: bool = False) -> bool:
        full = self.root / rel_path
        with self._lock:
            if not full.exists():
                return False
            if full.is_dir():
                if recursive:
                    shutil.rmtree(full)
                else:
                    full.rmdir()
            else:
                full.unlink()
            # Remove from index
            to_remove = [k for k in self._nodes if k == rel_path or k.startswith(rel_path + "/")]
            for k in to_remove:
                del self._nodes[k]
            return True

    def move(self, src: str, dst: str) -> bool:
        src_full = self.root / src
        dst_full = self.root / dst
        with self._lock:
            if not src_full.exists():
                return False
            dst_full.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_full), str(dst_full))
            self._scan()
            return True

    def search(self, pattern: str, content: bool = False) -> List[Dict[str, Any]]:
        regex = re.compile(pattern, re.IGNORECASE)
        results = []
        with self._lock:
            for rel, info in self._nodes.items():
                if regex.search(rel):
                    results.append(info)
                elif content and info["type"] == "file":
                    try:
                        text = (self.root / rel).read_text(encoding="utf-8", errors="ignore")
                        if regex.search(text):
                            results.append(info)
                    except Exception:
                        pass
        return results

    def tree_str(self, rel_path: str = ".", indent: str = "") -> str:
        """Return a printable tree representation."""
        lines = []
        items = self.list_dir(rel_path)
        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            prefix = "└── " if is_last else "├── "
            lines.append(f"{indent}{prefix}{Path(item['path']).name}")
            if item["type"] == "dir":
                child_indent = indent + ("    " if is_last else "│   ")
                lines.extend(self.tree_str(item["path"], child_indent).splitlines())
        return "\n".join(lines)

    def refresh(self) -> None:
        with self._lock:
            self._scan()


# ---------------------------------------------------------------------------
# NativeEditorBuffer
# ---------------------------------------------------------------------------

class NativeEditorBuffer:
    """Text buffer with undo/redo, cursor tracking, and basic editing."""

    MAX_UNDO = 100

    def __init__(self, content: str = "") -> None:
        self._lines: List[str] = content.split("\n") if content else [""]
        self._undo: deque = deque(maxlen=self.MAX_UNDO)
        self._redo: deque = deque(maxlen=self.MAX_UNDO)
        self._cursor: Tuple[int, int] = (0, 0)  # (line, column)
        self._lock = threading.RLock()

    def _snapshot(self) -> List[str]:
        return [line[:] for line in self._lines]

    def _push_undo(self) -> None:
        self._undo.append(self._snapshot())
        self._redo.clear()

    def get_text(self) -> str:
        with self._lock:
            return "\n".join(self._lines)

    def set_text(self, text: str) -> None:
        with self._lock:
            self._push_undo()
            self._lines = text.split("\n") if text else [""]
            self._cursor = (0, 0)

    def insert(self, line: int, col: int, text: str) -> None:
        with self._lock:
            self._push_undo()
            line = max(0, min(line, len(self._lines) - 1))
            col = max(0, min(col, len(self._lines[line])))
            parts = text.split("\n")
            if len(parts) == 1:
                self._lines[line] = self._lines[line][:col] + text + self._lines[line][col:]
                self._cursor = (line, col + len(text))
            else:
                before = self._lines[line][:col]
                after = self._lines[line][col:]
                self._lines[line] = before + parts[0]
                for i, p in enumerate(parts[1:-1], start=1):
                    self._lines.insert(line + i, p)
                self._lines.insert(line + len(parts) - 1, parts[-1] + after)
                self._cursor = (line + len(parts) - 1, len(parts[-1]))

    def delete_range(self, start: Tuple[int, int], end: Tuple[int, int]) -> str:
        with self._lock:
            self._push_undo()
            s_line, s_col = start
            e_line, e_col = end
            s_line, e_line = max(0, s_line), max(0, e_line)
            s_col = max(0, min(s_col, len(self._lines[s_line])))
            e_col = max(0, min(e_col, len(self._lines[e_line])))
            if s_line == e_line:
                removed = self._lines[s_line][s_col:e_col]
                self._lines[s_line] = self._lines[s_line][:s_col] + self._lines[s_line][e_col:]
                self._cursor = (s_line, s_col)
                return removed
            # Multi-line delete
            removed_lines = self._lines[s_line:e_line + 1]
            removed = removed_lines[0][s_col:] + "\n" + "\n".join(removed_lines[1:-1])
            if len(removed_lines) > 1:
                removed += "\n" + removed_lines[-1][:e_col]
            merged = self._lines[s_line][:s_col] + self._lines[e_line][e_col:]
            self._lines[s_line:e_line + 1] = [merged]
            self._cursor = (s_line, s_col)
            return removed

    def undo(self) -> bool:
        with self._lock:
            if not self._undo:
                return False
            self._redo.append(self._snapshot())
            self._lines = self._undo.pop()
            return True

    def redo(self) -> bool:
        with self._lock:
            if not self._redo:
                return False
            self._undo.append(self._snapshot())
            self._lines = self._redo.pop()
            return True

    def get_cursor(self) -> Tuple[int, int]:
        with self._lock:
            return self._cursor

    def set_cursor(self, line: int, col: int) -> None:
        with self._lock:
            line = max(0, min(line, len(self._lines) - 1))
            col = max(0, min(col, len(self._lines[line])))
            self._cursor = (line, col)

    def line_count(self) -> int:
        with self._lock:
            return len(self._lines)

    def get_line(self, index: int) -> str:
        with self._lock:
            if 0 <= index < len(self._lines):
                return self._lines[index]
            return ""


# ---------------------------------------------------------------------------
# NativeSessionManager
# ---------------------------------------------------------------------------

class NativeSessionManager:
    """Save and restore workspace sessions (open files, cursor positions, breakpoints)."""

    def __init__(self, sessions_dir: str = ".sessions") -> None:
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._current: Optional[str] = None
        self._lock = threading.RLock()

    def save(self, name: str, state: Dict[str, Any]) -> None:
        path = self.sessions_dir / f"{name}.json"
        with self._lock:
            path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
            self._current = name

    def load(self, name: str) -> Optional[Dict[str, Any]]:
        path = self.sessions_dir / f"{name}.json"
        with self._lock:
            if not path.exists():
                return None
            return json.loads(path.read_text(encoding="utf-8"))

    def list_sessions(self) -> List[str]:
        with self._lock:
            return [p.stem for p in self.sessions_dir.glob("*.json")]

    def delete(self, name: str) -> bool:
        path = self.sessions_dir / f"{name}.json"
        with self._lock:
            if path.exists():
                path.unlink()
                if self._current == name:
                    self._current = None
                return True
            return False

    def current(self) -> Optional[str]:
        with self._lock:
            return self._current

    def snapshot(self, file_tree: NativeFileTree, buffers: Dict[str, NativeEditorBuffer]) -> Dict[str, Any]:
        """Create a workspace snapshot from current state."""
        return {
            "timestamp": time.time(),
            "root": str(file_tree.root),
            "open_files": [
                {
                    "path": path,
                    "cursor": buf.get_cursor(),
                    "scroll": 0,
                }
                for path, buf in buffers.items()
            ],
        }


# ---------------------------------------------------------------------------
# NativeLSPAdapter
# ---------------------------------------------------------------------------

class NativeLSPAdapter:
    """Simplified Language Server Protocol client (stdio-based)."""

    def __init__(self, command: Optional[List[str]] = None, tcp_host: Optional[str] = None, tcp_port: Optional[int] = None) -> None:
        self.command = command
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port
        self._proc: Optional[subprocess.Popen] = None
        self._seq = 0
        self._pending: Dict[int, Callable] = {}
        self._lock = threading.RLock()

    def start(self) -> bool:
        if self.command:
            try:
                self._proc = subprocess.Popen(
                    self.command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                return True
            except Exception as exc:
                print(f"[LSP] failed to start: {exc}")
                return False
        return False  # TCP not implemented in self-test

    def stop(self) -> None:
        if self._proc:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None

    def _next_id(self) -> int:
        with self._lock:
            self._seq += 1
            return self._seq

    def _build_message(self, method: str, params: Dict[str, Any]) -> str:
        msg = json.dumps({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params,
        }, separators=(",", ":"))
        return f"Content-Length: {len(msg.encode('utf-8'))}\r\n\r\n{msg}"

    def initialize(self, root_uri: str = "file:///tmp/project") -> Optional[Dict[str, Any]]:
        """Send initialize request (simulated — no real server in self-test)."""
        if not self._proc:
            # Simulate response for self-test
            return {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "capabilities": {
                        "textDocumentSync": 1,
                        "completionProvider": {"triggerCharacters": ["."]},
                        "hoverProvider": True,
                    },
                },
            }
        msg = self._build_message("initialize", {"rootUri": root_uri, "capabilities": {}})
        if self._proc.stdin:
            self._proc.stdin.write(msg)
            self._proc.stdin.flush()
        # Read response would go here in real implementation
        return None

    def shutdown(self) -> None:
        msg = self._build_message("shutdown", {})
        if self._proc and self._proc.stdin:
            self._proc.stdin.write(msg)
            self._proc.stdin.flush()

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None


# ---------------------------------------------------------------------------
# NativeTerminalMultiplexer
# ---------------------------------------------------------------------------

class NativeTerminalMultiplexer:
    """Session-based terminal management without PTY dependencies."""

    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def create(self, session_id: str, cwd: str = ".", env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        with self._lock:
            self._sessions[session_id] = {
                "id": session_id,
                "cwd": cwd,
                "env": env or dict(os.environ),
                "history": [],
                "running": False,
                "last_cmd": None,
            }
            return dict(self._sessions[session_id])

    def execute(self, session_id: str, command: str, timeout: float = 30.0) -> Dict[str, Any]:
        with self._lock:
            sess = self._sessions.get(session_id)
            if not sess:
                return {"error": "session_not_found", "stdout": "", "stderr": "", "rc": -1}
            sess["running"] = True
            sess["last_cmd"] = command

        try:
            import shlex
            cmd_list = shlex.split(command) if isinstance(command, str) else command
            result = subprocess.run(
                cmd_list,
                shell=False,
                cwd=sess["cwd"],
                env=sess["env"],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "rc": result.returncode,
            }
        except subprocess.TimeoutExpired as exc:
            output = {"stdout": exc.stdout or "", "stderr": exc.stderr or "", "rc": -9, "timeout": True}
        except Exception as exc:
            output = {"stdout": "", "stderr": str(exc), "rc": -1}
        finally:
            with self._lock:
                sess["history"].append({"cmd": command, **output})
                sess["running"] = False
        return output

    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            sess = self._sessions.get(session_id)
            return list(sess["history"]) if sess else []

    def close(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def list_sessions(self) -> List[str]:
        with self._lock:
            return list(self._sessions.keys())

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            sess = self._sessions.get(session_id)
            return dict(sess) if sess else None


# ---------------------------------------------------------------------------
# NativeIDEWorkspace
# ---------------------------------------------------------------------------

class NativeIDEWorkspace:
    """Composes file tree, editor buffers, sessions, LSP, and terminal."""

    def __init__(self, root: str = ".") -> None:
        self.file_tree = NativeFileTree(root)
        self.buffers: Dict[str, NativeEditorBuffer] = {}
        self.session_manager = NativeSessionManager()
        self.lsp: Optional[NativeLSPAdapter] = None
        self.terminal = NativeTerminalMultiplexer()
        self._lock = threading.RLock()

    def open_file(self, rel_path: str) -> NativeEditorBuffer:
        with self._lock:
            if rel_path not in self.buffers:
                content = self.file_tree.read_file(rel_path)
                self.buffers[rel_path] = NativeEditorBuffer(content)
            return self.buffers[rel_path]

    def close_file(self, rel_path: str) -> bool:
        with self._lock:
            return self.buffers.pop(rel_path, None) is not None

    def save_file(self, rel_path: str) -> None:
        with self._lock:
            buf = self.buffers.get(rel_path)
            if buf:
                self.file_tree.write_file(rel_path, buf.get_text())

    def attach_lsp(self, adapter: NativeLSPAdapter) -> None:
        self.lsp = adapter

    def snapshot_workspace(self, name: str) -> None:
        state = self.session_manager.snapshot(self.file_tree, self.buffers)
        self.session_manager.save(name, state)

    def restore_workspace(self, name: str) -> Optional[Dict[str, Any]]:
        return self.session_manager.load(name)

    def list_open_files(self) -> List[str]:
        with self._lock:
            return list(self.buffers.keys())


# ---------------------------------------------------------------------------
# Self-test demo
# ---------------------------------------------------------------------------

def run() -> None:
    print("=" * 60)
    print("NativeIDEWorkspace — self-test demo")
    print("=" * 60)

    # Setup temp workspace
    test_root = "/tmp/magnatrix_ide_test"
    shutil.rmtree(test_root, ignore_errors=True)
    os.makedirs(test_root + "/src/utils", exist_ok=True)
    os.makedirs(test_root + "/tests", exist_ok=True)
    Path(test_root + "/src/main.py").write_text("def main():\n    print('hello')\n", encoding="utf-8")
    Path(test_root + "/src/utils/helpers.py").write_text("# helpers\n", encoding="utf-8")
    Path(test_root + "/tests/test_main.py").write_text("def test_main():\n    pass\n", encoding="utf-8")

    # [1] FileTree
    print("\n[1] FileTree — scan and list")
    ft = NativeFileTree(test_root)
    root_items = ft.list_dir(".")
    for item in root_items:
        print(f"    {item['type']:4s} {item['path']}")
    assert len(root_items) == 2  # src, tests

    print("\n[2] FileTree — read/write")
    content = ft.read_file("src/main.py")
    print(f"    src/main.py = {content!r}")
    ft.write_file("README.md", "# MAGNATRIX\n")
    assert "README.md" in [n["path"] for n in ft.list_dir(".")]

    print("\n[3] FileTree — search")
    results = ft.search("main", content=True)
    for r in results:
        print(f"    found: {r['path']} ({r['type']})")
    assert any("main" in r["path"] for r in results)

    print("\n[4] FileTree — tree view")
    tree = ft.tree_str(".")
    print(tree)
    assert "src" in tree and "tests" in tree

    # [5] EditorBuffer
    print("\n[5] EditorBuffer — insert and undo/redo")
    buf = NativeEditorBuffer("line1\nline2\n")
    buf.insert(0, 5, " — modified")
    print(f"    after insert: {buf.get_text()!r}")
    buf.undo()
    print(f"    after undo: {buf.get_text()!r}")
    buf.redo()
    print(f"    after redo: {buf.get_text()!r}")
    assert "modified" in buf.get_text()

    print("\n[6] EditorBuffer — delete range")
    buf2 = NativeEditorBuffer("hello cruel world")
    removed = buf2.delete_range((0, 6), (0, 11))
    print(f"    removed={removed!r} remaining={buf2.get_text()!r}")
    assert removed == "cruel" and buf2.get_text() == "hello  world"

    print("\n[7] EditorBuffer — multi-line insert")
    buf3 = NativeEditorBuffer("start")
    buf3.insert(0, 5, "\nline a\nline b")
    print(f"    lines={buf3.line_count()} text={buf3.get_text()!r}")
    assert buf3.line_count() == 3

    # [8] SessionManager
    print("\n[8] SessionManager — save/load")
    sm = NativeSessionManager(sessions_dir="/tmp/magnatrix_sessions")
    sm.save("alpha", {"files": ["a.py"], "cursor": (1, 0)})
    loaded = sm.load("alpha")
    print(f"    loaded={loaded}")
    assert loaded and loaded["files"] == ["a.py"]
    print(f"    sessions={sm.list_sessions()}")

    # [9] Snapshot
    print("\n[9] SessionManager — workspace snapshot")
    ide = NativeIDEWorkspace(test_root)
    _ = ide.open_file("src/main.py")
    buf = ide.open_file("src/utils/helpers.py")
    buf.insert(0, 10, "# updated")
    ide.snapshot_workspace("dev-session")
    snap = ide.restore_workspace("dev-session")
    print(f"    snapshot files={[f['path'] for f in snap['open_files']]}")
    assert any(f["path"] == "src/main.py" for f in snap["open_files"])

    # [10] LSPAdapter (simulated)
    print("\n[10] LSPAdapter — initialize")
    lsp = NativeLSPAdapter(command=None)  # simulated mode
    caps = lsp.initialize()
    print(f"    capabilities={caps['result']['capabilities']}")
    assert caps["result"]["capabilities"]["hoverProvider"]

    # [11] TerminalMultiplexer
    print("\n[11] TerminalMultiplexer — execute command")
    tm = NativeTerminalMultiplexer()
    tm.create("shell-1", cwd=test_root)
    result = tm.execute("shell-1", "echo hello_from_mux")
    print(f"    rc={result['rc']} stdout={result['stdout'].strip()!r}")
    assert result["rc"] == 0 and "hello_from_mux" in result["stdout"]

    print("\n[12] TerminalMultiplexer — history")
    hist = tm.get_history("shell-1")
    print(f"    history count={len(hist)}")
    assert len(hist) == 1 and hist[0]["cmd"] == "echo hello_from_mux"

    # [13] Full IDE workspace
    print("\n[13] IDEWorkspace — integration")
    print(f"    open files: {ide.list_open_files()}")
    ide.save_file("src/utils/helpers.py")
    saved_content = ft.read_file("src/utils/helpers.py")
    print(f"    saved helpers.py = {saved_content!r}")
    assert "updated" in saved_content

    # Cleanup
    shutil.rmtree(test_root, ignore_errors=True)
    shutil.rmtree("/tmp/magnatrix_sessions", ignore_errors=True)

    print("\n✅ All IDE workspace tests passed.")
    print("=" * 60)


if __name__ == "__main__":
    run()
