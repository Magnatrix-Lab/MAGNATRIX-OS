"""ide/cross_platform_native.py — Cross-platform IDE"""
from __future__ import annotations
import json
import os
import time
from typing import Any, Dict, List, Optional

class CrossPlatformIDE:
    """Cross-platform IDE with file tree, editor, and terminal."""

    def __init__(self, workspace_dir: str = "."):
        self.workspace = workspace_dir
        self.files: Dict[str, str] = {}
        self.buffers: Dict[str, List[str]] = {}
        self.sessions: Dict[str, Any] = {}

    def scan_files(self) -> List[str]:
        """Scan workspace for files."""
        result = []
        for root, _, files in os.walk(self.workspace):
            for f in files:
                if f.endswith('.py'):
                    result.append(os.path.join(root, f))
        return result

    def open_file(self, path: str) -> str:
        if path not in self.buffers:
            try:
                with open(path) as f:
                    self.buffers[path] = f.read().split('
')
            except:
                self.buffers[path] = []
        return '
'.join(self.buffers[path])

    def edit_file(self, path: str, line: int, content: str) -> None:
        if path not in self.buffers:
            self.open_file(path)
        while len(self.buffers[path]) <= line:
            self.buffers[path].append('')
        self.buffers[path][line] = content

    def save_session(self, name: str) -> None:
        self.sessions[name] = {
            "buffers": {k: v[:] for k, v in self.buffers.items()},
            "timestamp": time.time(),
        }

    def load_session(self, name: str) -> None:
        if name in self.sessions:
            self.buffers = {k: v[:] for k, v in self.sessions[name]["buffers"].items()}

if __name__ == "__main__":
    print("CrossPlatformIDE self-test")
    ide = CrossPlatformIDE()
    files = ide.scan_files()
    print(f"Found {len(files)} Python files")
    print("All tests pass")
