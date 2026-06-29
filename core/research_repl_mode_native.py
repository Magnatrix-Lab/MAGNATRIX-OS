"""
research_repl_mode_native.py
MAGNATRIX-OS — Research REPL Mode

Inspired by gajae-code: rlm (research/REPL mode) for exploratory coding. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class REPLCommand:
    command_id: str
    input_code: str
    output: str
    error: str
    execution_time_ms: float
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class ResearchREPLMode:
    """Research REPL mode for exploratory coding."""

    def __init__(self, cache_dir: str = "./repl_mode"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.history: List[REPLCommand] = []
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "history.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.history = [REPLCommand(**c) for c in data]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "history.json", "w", encoding="utf-8") as f:
            json.dump([asdict(c) for c in self.history], f, indent=2)

    def execute(self, command_id: str, code: str) -> REPLCommand:
        """Simulate code execution."""
        import time
        start = time.time()
        try:
            # Safe evaluation of simple expressions
            if any(kw in code for kw in ["import", "exec", "eval", "open", "os.", "sys."]):
                output = "Blocked for security"
                error = "Security restriction"
            else:
                try:
                    result = eval(code, {"__builtins__": {}}, {})
                    output = str(result)[:1000]
                    error = ""
                except Exception as e:
                    output = ""
                    error = str(e)
        except Exception as e:
            output = ""
            error = str(e)
        duration = (time.time() - start) * 1000
        cmd = REPLCommand(
            command_id=command_id, input_code=code, output=output,
            error=error, execution_time_ms=round(duration, 2),
        )
        self.history.append(cmd)
        self._save()
        return cmd

    def get_history(self) -> List[REPLCommand]:
        return self.history

    def clear_history(self) -> None:
        self.history = []
        self._save()

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.history)
        errors = sum(1 for c in self.history if c.error)
        avg_time = sum(c.execution_time_ms for c in self.history) / max(1, total)
        return {"total_commands": total, "errors": errors, "avg_time_ms": round(avg_time, 2)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["ResearchREPLMode", "REPLCommand"]