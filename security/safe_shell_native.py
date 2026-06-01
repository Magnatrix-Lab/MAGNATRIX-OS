"""security/safe_shell_native.py — Safe subprocess wrapper"""
from __future__ import annotations
import shlex
import subprocess
import threading
import time
from typing import List, Optional, Dict, Any

class SafeShell:
    """Safe shell execution. Rejects shell=True, validates commands."""

    ALLOWLIST = {
        'ls', 'cat', 'echo', 'pwd', 'cd', 'mkdir', 'rm', 'cp', 'mv',
        'touch', 'head', 'tail', 'grep', 'find', 'wc', 'sort', 'uniq',
        'git', 'python', 'python3', 'pip', 'pytest', 'curl', 'wget',
    }

    DENYLIST = {
        'rm', 'rmdir', 'mv', 'chmod', 'chown',
    }

    def __init__(self, timeout: float = 30.0, max_output: int = 100000):
        self.timeout = timeout
        self.max_output = max_output
        self._lock = threading.Lock()
        self._history: List[Dict[str, Any]] = []

    def validate_command(self, cmd: str) -> bool:
        """Check if command is in allowlist."""
        parts = cmd.split()
        if not parts:
            return False
        base_cmd = parts[0].strip()
        return base_cmd in self.ALLOWLIST

    def run(self, cmd: str, args: Optional[List[str]] = None, cwd: Optional[str] = None, 
            env: Optional[Dict[str, str]] = None, capture_output: bool = True) -> Dict[str, Any]:
        """Run command safely with shell=False."""
        if not self.validate_command(cmd):
            raise ValueError(f"Command '{cmd}' not in allowlist")

        args = args or []
        cmd_list = [cmd] + args

        start = time.time()
        try:
            result = subprocess.run(
                cmd_list,
                cwd=cwd,
                env=env,
                capture_output=capture_output,
                text=True,
                timeout=self.timeout,
                shell=False,
            )
            output = result.stdout[:self.max_output] if result.stdout else ""
            error = result.stderr[:self.max_output] if result.stderr else ""

            record = {
                "cmd": cmd,
                "args": args,
                "cwd": cwd,
                "returncode": result.returncode,
                "stdout_len": len(output),
                "stderr_len": len(error),
                "duration_ms": (time.time() - start) * 1000,
                "timestamp": time.time(),
            }
            with self._lock:
                self._history.append(record)

            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": output,
                "stderr": error,
                "duration_ms": (time.time() - start) * 1000,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Timeout after {self.timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return self._history.copy()

if __name__ == "__main__":
    print("SafeShell self-test")
    ss = SafeShell()
    r = ss.run("echo", ["hello"])
    assert r["success"]
    assert "hello" in r["stdout"]
    print("All tests pass")
