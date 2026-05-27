#!/usr/bin/env python3
"""
MAGNATRIX-OS Cline Bridge (VS Code Extension)
"""
import os, json, subprocess
from ide.ide_integration_native import IDEBridge, IDEConfig, IDEResult
from typing import Dict, Any


class ClineBridge(IDEBridge):
    """Bridge to Cline VS Code extension."""

    def send_command(self, command: str, context: Dict[str, Any] = None) -> IDEResult:
        ctx = context or {}
        # Cline operates via VS Code extension API
        # We queue commands via a shared JSON file
        queue_file = os.path.expanduser("~/.magnatrix/cline_cmd.json")
        os.makedirs(os.path.dirname(queue_file), exist_ok=True)
        try:
            with open(queue_file, "w") as f:
                json.dump({
                    "command": command,
                    "context": ctx,
                    "timestamp": __import__("time").time(),
                    "source": "magnatrix",
                }, f)
            return IDEResult(
                success=True,
                output=f"Command queued for Cline: {command[:60]}...",
                metadata={"queue_file": queue_file},
            )
        except Exception as e:
            return IDEResult(success=False, output="", error=str(e))

    def read_feedback(self):
        feedback_file = os.path.expanduser("~/.magnatrix/cline_feedback.json")
        if os.path.exists(feedback_file):
            try:
                with open(feedback_file) as f:
                    return [json.load(f)]
            except Exception:
                pass
        return []
