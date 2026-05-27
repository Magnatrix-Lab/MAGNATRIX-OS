#!/usr/bin/env python3
"""
MAGNATRIX-OS Opencode Bridge
"""
import os, json, subprocess
from ide.ide_integration_native import IDEBridge, IDEConfig, IDEResult
from typing import Dict, Any


class OpencodeBridge(IDEBridge):
    """Bridge to Opencode CLI."""

    def send_command(self, command: str, context: Dict[str, Any] = None) -> IDEResult:
        ctx = context or {}
        cmd = [self.config.executable or "opencode", "run", command]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=ctx.get("cwd"))
            return IDEResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
            )
        except Exception as e:
            return IDEResult(success=False, output="", error=str(e))

    def read_feedback(self):
        return []
