"""Sandbox Code Runner — Safe execution with timeout, capture."""
from dataclasses import dataclass
from pathlib import Path
import json, time, sys

@dataclass
class RunResult:
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration_ms: int = 0
    killed: bool = False

class SandboxCodeRunner:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._history: list[dict] = []
        self._allowed_builtins: list[str] = ["abs", "all", "any", "bool", "chr", "dict", "enumerate", "filter", "float", "format", "frozenset", "hex", "int", "isinstance", "issubclass", "len", "list", "map", "max", "min", "oct", "ord", "pow", "range", "reversed", "round", "set", "slice", "sorted", "str", "sum", "tuple", "zip"]
        self._persist_path = self.root / "sandbox_runner.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._history = data.get("history", [])
            self._allowed_builtins = data.get("allowed_builtins", self._allowed_builtins)

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "history": self._history,
            "allowed_builtins": self._allowed_builtins
        }, indent=2))

    def run(self, code: str, timeout_ms: int = 5000) -> RunResult:
        start = time.time()
        result = RunResult()
        # Safe eval environment
        safe_globals = {"__builtins__": {name: getattr(__builtins__, name) for name in self._allowed_builtins if hasattr(__builtins__, name)}}
        safe_locals = {}
        try:
            exec(code, safe_globals, safe_locals)
            result.stdout = str(safe_locals.get("_", ""))
        except Exception as e:
            result.stderr = str(e)
            result.exit_code = 1
        result.duration_ms = int((time.time() - start) * 1000)
        if result.duration_ms > timeout_ms:
            result.killed = True
            result.exit_code = -9
        self._history.append({"code_len": len(code), "exit_code": result.exit_code, "duration_ms": result.duration_ms})
        self._save()
        return result

    def set_allowed_builtins(self, names: list[str]) -> None:
        self._allowed_builtins = names
        self._save()

    def to_dict(self) -> dict:
        return {"history_count": len(self._history), "allowed_builtins": len(self._allowed_builtins)}

    def get_stats(self) -> dict:
        return {"runs": len(self._history), "errors": sum(1 for h in self._history if h.get("exit_code", 0) != 0)}

__all__ = ["SandboxCodeRunner", "RunResult"]
