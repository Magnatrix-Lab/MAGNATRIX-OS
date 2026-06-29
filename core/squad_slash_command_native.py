"""Squad Slash Command — Parser for /squad manager, /squad worker, etc."""
from dataclasses import dataclass
from pathlib import Path
import json
import re

@dataclass
class SlashCommand:
    raw: str = ""
    command: str = ""  # setup | init | manager | worker | inspector | status | stop
    args: list[str] = None
    kwargs: dict = None
    workspace: str = ""
    parsed: bool = False

    def __post_init__(self):
        if self.args is None:
            self.args = []
        if self.kwargs is None:
            self.kwargs = {}

class SquadSlashCommand:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._command_history: list[SlashCommand] = []
        self._handlers: dict[str, dict] = {
            "setup": {"description": "Install /squad command for AI tools", "needs_workspace": False},
            "init": {"description": "Initialize workspace", "needs_workspace": False},
            "manager": {"description": "Assign manager role", "needs_workspace": True},
            "worker": {"description": "Assign worker role", "needs_workspace": True},
            "inspector": {"description": "Assign inspector role", "needs_workspace": True},
            "status": {"description": "Show squad status", "needs_workspace": True},
            "stop": {"description": "Stop agent", "needs_workspace": True},
            "leave": {"description": "Leave workspace", "needs_workspace": True},
        }
        self._persist_path = self.root / "squad_commands.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._command_history = [SlashCommand(**c) for c in data.get("history", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "history": [c.__dict__ for c in self._command_history]
        }, indent=2))

    def parse(self, raw: str) -> SlashCommand:
        cmd = SlashCommand(raw=raw)
        # Parse: /squad manager --workspace=myproject
        # or: squad manager myproject
        parts = raw.strip().split()
        if not parts:
            return cmd

        idx = 0
        if parts[0] == "/squad" or parts[0] == "squad":
            idx = 1

        if idx < len(parts):
            cmd.command = parts[idx]
            idx += 1

        # Parse remaining args and kwargs
        while idx < len(parts):
            part = parts[idx]
            if part.startswith("--"):
                key_val = part[2:].split("=", 1)
                if len(key_val) == 2:
                    cmd.kwargs[key_val[0]] = key_val[1]
                else:
                    cmd.kwargs[key_val[0]] = True
            elif part.startswith("-"):
                cmd.kwargs[part[1:]] = True
            else:
                cmd.args.append(part)
            idx += 1

        cmd.workspace = cmd.kwargs.get("workspace", cmd.kwargs.get("w", ""))
        cmd.parsed = cmd.command in self._handlers
        self._command_history.append(cmd)
        self._save()
        return cmd

    def is_valid(self, command: str) -> bool:
        return command in self._handlers

    def get_handler(self, command: str) -> dict | None:
        return self._handlers.get(command)

    def list_commands(self) -> list[str]:
        return list(self._handlers.keys())

    def to_dict(self) -> dict:
        return {"command_count": len(self._handlers), "history": len(self._command_history)}

    def get_stats(self) -> dict:
        executed = {}
        for c in self._command_history:
            executed[c.command] = executed.get(c.command, 0) + 1
        return {"commands": len(self._handlers), "executed": len(self._command_history), "by_command": executed}

__all__ = ["SquadSlashCommand", "SlashCommand"]
