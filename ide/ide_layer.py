"""
MAGNATRIX — IDE Integration Layer
═══════════════════════════════════
Layer 12: IDE — adapters untuk VS Code, Cline, web-to-app.

Features:
- VS Code extension bridge (LSP-like communication)
- Cline integration (agentic IDE assistant)
- Web-to-app converter (web page -> native app)
- Code completion provider
- Inline chat / copilot-style assistance
- File watcher & auto-sync
- Terminal integration

Author: MAGNATRIX-OS
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import textwrap
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


@dataclass
class CodeSnippet:
    file_path: str
    language: str
    content: str
    start_line: int = 1
    end_line: int = 0
    imports: List[str] = field(default_factory=list)
    symbols: List[str] = field(default_factory=list)


class VSCodeBridge:
    """Bridge ke VS Code extension — communicate via stdio atau socket."""

    def __init__(self, workspace_dir: Optional[str] = None):
        self.workspace_dir = workspace_dir or os.getcwd()
        self._callbacks: Dict[str, Callable] = {}
        self._task_queue: asyncio.Queue = asyncio.Queue()

    def register_handler(self, method: str, handler: Callable) -> None:
        self._callbacks[method] = handler

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        method = request.get("method", "")
        handler = self._callbacks.get(method)
        if not handler:
            return {"error": f"Method '{method}' not supported"}
        try:
            if asyncio.iscoroutinefunction(handler):
                return await handler(request.get("params", {}))
            return handler(request.get("params", {}))
        except Exception as e:
            return {"error": str(e)}

    async def get_workspace_files(self, pattern: str = "**/*.py") -> Dict[str, Any]:
        """List files di workspace dengan pattern."""
        try:
            import glob
            files = glob.glob(os.path.join(self.workspace_dir, pattern), recursive=True)
            return {"success": True, "files": files, "count": len(files)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def read_file_range(self, file_path: str, start: int = 1, end: int = 50) -> Dict[str, Any]:
        try:
            p = Path(file_path)
            if not p.exists():
                return {"success": False, "error": "File not found"}
            lines = p.read_text(encoding="utf-8").splitlines()
            selected = lines[start - 1:end]
            return {
                "success": True,
                "content": "\n".join(selected),
                "start_line": start,
                "end_line": min(end, len(lines)),
                "total_lines": len(lines),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def apply_edit(self, file_path: str, start: int, end: int, replacement: str) -> Dict[str, Any]:
        try:
            p = Path(file_path)
            lines = p.read_text(encoding="utf-8").splitlines()
            new_lines = lines[:start - 1] + replacement.splitlines() + lines[end:]
            p.write_text("\n".join(new_lines), encoding="utf-8")
            return {"success": True, "file": file_path, "lines_changed": end - start + 1}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def run_terminal(self, command: str, cwd: Optional[str] = None) -> Dict[str, Any]:
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd or self.workspace_dir,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
            return {
                "success": proc.returncode == 0,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "returncode": proc.returncode,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class ClineAdapter:
    """Adapter untuk Cline — agentic IDE assistant integration."""

    def __init__(self):
        self._context: List[Dict[str, Any]] = []
        self._capabilities = {
            "code_edit": True,
            "terminal": True,
            "browser": True,
            "file_read": True,
            "file_write": True,
        }

    async def process_task(self, task: str, file_context: Optional[str] = None) -> Dict[str, Any]:
        """Process task dari Cline — return structured action plan."""
        # In production: forward ke LLM dan parse actions
        return {
            "success": True,
            "task": task,
            "actions": [
                {"type": "read", "file": file_context},
                {"type": "think", "content": "Analyze requirements"},
                {"type": "edit", "file": file_context, "description": "Apply changes"},
            ],
            "capabilities": self._capabilities,
        }

    async def execute_action(self, action: Dict[str, Any], bridge: VSCodeBridge) -> Dict[str, Any]:
        action_type = action.get("type")
        if action_type == "read":
            return await bridge.read_file_range(action.get("file", ""))
        elif action_type == "edit":
            return await bridge.apply_edit(
                action.get("file", ""),
                action.get("start", 1),
                action.get("end", 1),
                action.get("replacement", ""),
            )
        elif action_type == "terminal":
            return await bridge.run_terminal(action.get("command", ""))
        return {"success": False, "error": f"Unknown action type: {action_type}"}


class WebToAppConverter:
    """Convert web page/component ke native application scaffold."""

    def __init__(self):
        self._templates = {
            "react": self._react_template,
            "electron": self._electron_template,
            "tauri": self._tauri_template,
            "flutter": self._flutter_template,
        }

    async def convert(self, url: str, target: str = "electron") -> Dict[str, Any]:
        """Scrape web page dan generate native app scaffold."""
        # In production: scrape + analyze DOM structure + generate code
        template_fn = self._templates.get(target, self._electron_template)
        scaffold = template_fn(url)
        return {
            "success": True,
            "target": target,
            "scaffold": scaffold,
            "files_generated": len(scaffold),
        }

    def _react_template(self, url: str) -> Dict[str, str]:
        return {
            "src/App.jsx": f"export default function App() {{ return <iframe src='{url}' style={{{{width:'100%',height:'100vh',border:'none'}}}} />; }}",
            "package.json": json.dumps({"name": "magnatrix-webapp", "dependencies": {"react": "^18"}}, indent=2),
        }

    def _electron_template(self, url: str) -> Dict[str, str]:
        return {
            "main.js": f"const {{app, BrowserWindow}} = require('electron');\nlet win;\napp.whenReady().then(() => {{ win = new BrowserWindow({{width:1280,height:800}}); win.loadURL('{url}'); }});",
            "package.json": json.dumps({"name": "magnatrix-desktop", "main": "main.js", "dependencies": {"electron": "^28"}}, indent=2),
        }

    def _tauri_template(self, url: str) -> Dict[str, str]:
        return {
            "src-tauri/tauri.conf.json": json.dumps({"build": {"devUrl": url}, "windows": [{"title": "MAGNATRIX", "width": 1280, "height": 800}]}, indent=2),
        }

    def _flutter_template(self, url: str) -> Dict[str, str]:
        return {
            "lib/main.dart": f"import 'package:flutter/material.dart';\nimport 'package:webview_flutter/webview_flutter.dart';\nvoid main() => runApp(MaterialApp(home: Scaffold(body: WebView(initialUrl: '{url}'))));",
        }


class IDELayer:
    """Main IDE orchestrator — combines VS Code, Cline, web-to-app."""

    def __init__(self):
        self.vscode = VSCodeBridge()
        self.cline = ClineAdapter()
        self.web2app = WebToAppConverter()

    async def assist(self, request: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Main IDE assistance entry point."""
        return await self.cline.process_task(request, context)

    async def convert_webpage(self, url: str, target: str = "electron") -> Dict[str, Any]:
        return await self.web2app.convert(url, target)

    def healthcheck(self) -> bool:
        return True
