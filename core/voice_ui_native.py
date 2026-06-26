#!/usr/bin/env python3
"""Voice UI for MAGNATRIX-OS — Voice command interface."""
from __future__ import annotations
import re, time
from typing import Any, Dict, List, Optional

class VoiceUI:
    COMMANDS = {
        "start": ["start", "boot", "launch"],
        "stop": ["stop", "halt", "shutdown"],
        "status": ["status", "health", "check"],
        "list": ["list", "show", "display"],
        "help": ["help", "what can you do"],
    }

    def __init__(self) -> None:
        self._history: List[str] = []

    def parse_command(self, transcript: str) -> Dict[str, Any]:
        text = transcript.lower()
        for cmd, keywords in self.COMMANDS.items():
            if any(kw in text for kw in keywords):
                return {"command": cmd, "confidence": 0.9, "raw": transcript}
        return {"command": "unknown", "confidence": 0.0, "raw": transcript}

    def stats(self) -> Dict[str, Any]:
        return {"commands": len(self._history)}
