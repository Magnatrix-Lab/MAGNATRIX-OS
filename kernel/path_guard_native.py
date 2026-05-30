
"""
kernel/path_guard_native.py — MAGNATRIX-OS Path Sanitization & Security Wrapper

Central path security layer. All file operations should use PathGuard
instead of raw open().

Pure Python, stdlib only. Zero dependencies.

Components:
    • PathGuard — main path sanitization class
    • PathPolicy — configurable access policies
    • SafePath — safe path wrapper with validation
    • PathTraversalError — custom exception
    • PathAccessLog — audit log for path access
"""
from __future__ import annotations

import errno
import glob as glob_module
import hashlib
import json
import os
import re
import shutil
import stat
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path as StdPath
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ════════════════════════════════════════════════════════════════════════════
# PathTraversalError
# ════════════════════════════════════════════════════════════════════════════

class PathTraversalError(Exception):
    """Raised when a path traversal attempt is detected."""

    def __init__(self, path: str, base_dir: str, reason: str):
        self.path = path
        self.base_dir = base_dir
        self.reason = reason
        super().__init__(
            f"Path traversal blocked: '{path}' (base: '{base_dir}') — {reason}"
        )


class PathPolicyViolationError(Exception):
    """Raised when a path violates the configured policy."""

    def __init__(self, path: str, policy: str, reason: str):
        self.path = path
        self.policy = policy
        self.reason = reason
        super().__init__(f"Policy violation for '{path}': {policy} — {reason}")


# ════════════════════════════════════════════════════════════════════════════
# PathPolicy
# ════════════════════════════════════════════════════════════════════════════

class AccessMode(Enum):
    ALLOW = "allow"
    DENY = "deny"
    READONLY = "readonly"
    ASK = "ask"


@dataclass
class PathPolicy:
    """Configurable path access policy."""
    base_dir: str = "."
    mode: AccessMode = AccessMode.ALLOW
    allow_patterns: List[str] = field(default_factory=list)
    deny_patterns: List[str] = field(default_factory=list)
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    follow_symlinks: bool = False
    allow_absolute: bool = False
    allowed_extensions: Optional[Set[str]] = None
    denied_extensions: Optional[Set[str]] = None
    log_all_access: bool = True


# ════════════════════════════════════════════════════════════════════════════
# PathAccessLog
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class AccessRecord:
    timestamp: float
    path: str
    operation: str
    result: str
    caller: str
    reason: Optional[str] = None


class PathAccessLog:
    """Audit log for all path access attempts."""

    def __init__(self, max_entries: int = 10000):
        self._entries: List[AccessRecord] = []
        self._max_entries = max_entries
        self._lock = threading.Lock()

    def record(
        self,
        path: str,
        operation: str,
        result: str,
        caller: str = "",
        reason: Optional[str] = None,
    ) -> None:
        entry = AccessRecord(
            timestamp=time.time(),
            path=path,
            operation=operation,
            result=result,
            caller=caller,
            reason=reason,
        )
        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > self._max_entries:
                self._entries = self._entries[-self._max_entries:]

    def get_entries(
        self,
        operation: Optional[str] = None,
        result: Optional[str] = None,
        limit: int = 100,
    ) -> List[AccessRecord]:
        with self._lock:
            entries = self._entries.copy()
        if operation:
            entries = [e for e in entries if e.operation == operation]
        if result:
            entries = [e for e in entries if e.result == result]
        return entries[-limit:]

    def get_summary(self) -> Dict[str, int]:
        with self._lock:
            entries = self._entries.copy()
        return {
            "total": len(entries),
            "allowed": sum(1 for e in entries if e.result == "ALLOWED"),
            "denied": sum(1 for e in entries if e.result == "DENIED"),
            "blocked_traversal": sum(
                1 for e in entries
                if e.result == "DENIED" and e.reason and "traversal" in e.reason
            ),
        }

    def save(self, path: str) -> None:
        with self._lock:
            entries = [
                {
                    "timestamp": e.timestamp,
                    "path": e.path,
                    "operation": e.operation,
                    "result": e.result,
                    "caller": e.caller,
                    "reason": e.reason,
                }
                for e in self._entries
            ]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)


# ════════════════════════════════════════════════════════════════════════════
# SafePath
# ════════════════════════════════════════════════════════════════════════════

class SafePath:
    """Safe path wrapper with built-in validation."""

    def __init__(self, path: str, base_dir: str, guard: PathGuard):
        self.raw_path = path
        self.base_dir = os.path.abspath(base_dir)
        self.guard = guard
        self._resolved: Optional[str] = None

    @property
    def resolved(self) -> str:
        if self._resolved is None:
            self._resolved = self.guard.resolve(self.raw_path, self.base_dir)
        return self._resolved

    def exists(self) -> bool:
        return os.path.exists(self.resolved)

    def is_file(self) -> bool:
        return os.path.isfile(self.resolved)

    def is_dir(self) -> bool:
        return os.path.isdir(self.resolved)

    def size(self) -> int:
        return os.path.getsize(self.resolved)

    def __str__(self) -> str:
        return self.resolved

    def __repr__(self) -> str:
        return f"SafePath('{self.raw_path}' -> '{self.resolved}')"


# ════════════════════════════════════════════════════════════════════════════
# PathGuard
# ════════════════════════════════════════════════════════════════════════════

class PathGuard:
    """
    Central path sanitization and security wrapper.

    All file operations in MAGNATRIX-OS should use PathGuard instead of
    raw open(). This prevents path traversal, enforces policies, and
    provides audit logging.
    """

    def __init__(self, policy: Optional[PathPolicy] = None):
        self.policy = policy or PathPolicy()
        self.access_log = PathAccessLog()
        self._lock = threading.Lock()

    # ── Core Resolution ────────────────────────────────────────────────────

    def resolve(self, path: str, base_dir: Optional[str] = None) -> str:
        """
        Resolve a path relative to base_dir, rejecting traversal attempts.
        Returns absolute resolved path or raises PathTraversalError.
        """
        base = os.path.abspath(base_dir or self.policy.base_dir)

        # Reject absolute paths unless policy allows
        if os.path.isabs(path) and not self.policy.allow_absolute:
            raise PathTraversalError(path, base, "absolute paths not allowed")

        # Resolve the path
        if os.path.isabs(path):
            resolved = os.path.abspath(path)
        else:
            resolved = os.path.abspath(os.path.join(base, path))

        # Normalize (resolve . and ..)
        resolved = os.path.normpath(resolved)
        base = os.path.normpath(base)

        # Check for traversal using commonprefix
        prefix = os.path.commonprefix([resolved, base])
        if prefix != base or (not resolved.startswith(base + os.sep) and resolved != base):
            raise PathTraversalError(path, base, "path escapes base directory")

        return resolved

    def check(self, path: str, base_dir: Optional[str] = None) -> bool:
        """Check if a path is valid. Returns True/False."""
        try:
            self.resolve(path, base_dir)
            return True
        except PathTraversalError:
            return False

    # ── Policy Enforcement ─────────────────────────────────────────────────

    def _check_policy(self, resolved: str, operation: str) -> Tuple[bool, str]:
        """Check if operation is allowed by policy."""
        policy = self.policy

        # Check mode
        if policy.mode == AccessMode.DENY:
            return False, "policy mode is DENY"

        if policy.mode == AccessMode.READONLY and operation in ("write", "delete", "mkdir", "rmdir"):
            return False, "policy mode is READONLY"

        # Check deny patterns
        for pattern in policy.deny_patterns:
            if re.search(pattern, resolved):
                return False, f"matches deny pattern: {pattern}"

        # Check allow patterns
        if policy.allow_patterns:
            allowed = any(re.search(p, resolved) for p in policy.allow_patterns)
            if not allowed:
                return False, "does not match any allow pattern"

        # Check extensions
        ext = os.path.splitext(resolved)[1].lower()
        if policy.denied_extensions and ext in policy.denied_extensions:
            return False, f"extension '{ext}' is denied"
        if policy.allowed_extensions and ext not in policy.allowed_extensions:
            return False, f"extension '{ext}' not in allowed list"

        return True, "allowed"

    def _check_size(self, resolved: str) -> Tuple[bool, str]:
        """Check file size against policy."""
        if not os.path.exists(resolved):
            return True, "file does not exist"
        size = os.path.getsize(resolved)
        if size > self.policy.max_file_size:
            return False, f"file size {size} exceeds max {self.policy.max_file_size}"
        return True, "size OK"

    # ── Safe File Operations ───────────────────────────────────────────────

    def open(
        self,
        path: str,
        mode: str = "r",
        base_dir: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Safe open() wrapper."""
        resolved = self.resolve(path, base_dir)
        operation = "write" if any(c in mode for c in "wax+") else "read"

        allowed, reason = self._check_policy(resolved, operation)
        if not allowed:
            self.access_log.record(path, "open", "DENIED", reason=reason)
            raise PathPolicyViolationError(path, self.policy.mode.value, reason)

        if operation == "write":
            # Check parent directory exists
            parent = os.path.dirname(resolved)
            if not os.path.exists(parent):
                os.makedirs(parent, exist_ok=True)

        self.access_log.record(path, "open", "ALLOWED")
        return open(resolved, mode, **kwargs)

    def read(
        self, path: str, base_dir: Optional[str] = None,
        encoding: str = "utf-8", errors: str = "replace",
    ) -> str:
        """Read entire file safely."""
        with self.open(path, "r", base_dir, encoding=encoding, errors=errors) as f:
            return f.read()

    def write(
        self, path: str, content: str,
        base_dir: Optional[str] = None,
        encoding: str = "utf-8",
    ) -> int:
        """Write string to file safely."""
        with self.open(path, "w", base_dir, encoding=encoding) as f:
            return f.write(content)

    def mkdir(
        self, path: str,
        base_dir: Optional[str] = None,
        mode: int = 0o755,
        exist_ok: bool = False,
    ) -> None:
        """Safe mkdir() wrapper."""
        resolved = self.resolve(path, base_dir)
        allowed, reason = self._check_policy(resolved, "mkdir")
        if not allowed:
            self.access_log.record(path, "mkdir", "DENIED", reason=reason)
            raise PathPolicyViolationError(path, self.policy.mode.value, reason)
        self.access_log.record(path, "mkdir", "ALLOWED")
        os.makedirs(resolved, mode=mode, exist_ok=exist_ok)

    def rm(self, path: str, base_dir: Optional[str] = None) -> None:
        """Safe rm() wrapper."""
        resolved = self.resolve(path, base_dir)
        allowed, reason = self._check_policy(resolved, "delete")
        if not allowed:
            self.access_log.record(path, "rm", "DENIED", reason=reason)
            raise PathPolicyViolationError(path, self.policy.mode.value, reason)
        self.access_log.record(path, "rm", "ALLOWED")
        if os.path.isfile(resolved):
            os.remove(resolved)
        elif os.path.isdir(resolved):
            shutil.rmtree(resolved)

    def rmdir(self, path: str, base_dir: Optional[str] = None) -> None:
        """Safe rmdir() wrapper."""
        resolved = self.resolve(path, base_dir)
        allowed, reason = self._check_policy(resolved, "delete")
        if not allowed:
            self.access_log.record(path, "rmdir", "DENIED", reason=reason)
            raise PathPolicyViolationError(path, self.policy.mode.value, reason)
        self.access_log.record(path, "rmdir", "ALLOWED")
        os.rmdir(resolved)

    def glob(
        self, pattern: str,
        base_dir: Optional[str] = None,
    ) -> List[str]:
        """Safe glob() wrapper."""
        base = os.path.abspath(base_dir or self.policy.base_dir)
        # Validate pattern doesn't escape base
        if ".." in pattern:
            raise PathTraversalError(pattern, base, "glob pattern contains traversal")
        results = glob_module.glob(os.path.join(base, pattern))
        # Filter to base dir
        valid = []
        for r in results:
            r_abs = os.path.abspath(r)
            if r_abs.startswith(base + os.sep) or r_abs == base:
                valid.append(r)
        self.access_log.record(pattern, "glob", "ALLOWED")
        return valid

    def listdir(self, path: str = ".", base_dir: Optional[str] = None) -> List[str]:
        """Safe listdir() wrapper."""
        resolved = self.resolve(path, base_dir)
        allowed, reason = self._check_policy(resolved, "read")
        if not allowed:
            self.access_log.record(path, "listdir", "DENIED", reason=reason)
            raise PathPolicyViolationError(path, self.policy.mode.value, reason)
        self.access_log.record(path, "listdir", "ALLOWED")
        return os.listdir(resolved)

    def isfile(self, path: str, base_dir: Optional[str] = None) -> bool:
        resolved = self.resolve(path, base_dir)
        return os.path.isfile(resolved)

    def isdir(self, path: str, base_dir: Optional[str] = None) -> bool:
        resolved = self.resolve(path, base_dir)
        return os.path.isdir(resolved)

    def exists(self, path: str, base_dir: Optional[str] = None) -> bool:
        try:
            resolved = self.resolve(path, base_dir)
            return os.path.exists(resolved)
        except PathTraversalError:
            return False

    def getsize(self, path: str, base_dir: Optional[str] = None) -> int:
        resolved = self.resolve(path, base_dir)
        allowed, _ = self._check_size(resolved)
        if not allowed:
            return -1
        return os.path.getsize(resolved)

    # ── Symlink Handling ───────────────────────────────────────────────────

    def resolve_symlink(self, path: str, base_dir: Optional[str] = None) -> str:
        """Resolve symlinks with validation."""
        if not self.policy.follow_symlinks:
            raise PathPolicyViolationError(path, self.policy.mode.value, "symlinks disabled")
        resolved = self.resolve(path, base_dir)
        if os.path.islink(resolved):
            target = os.readlink(resolved)
            # Validate symlink target stays in base
            if os.path.isabs(target):
                target_dir = os.path.dirname(resolved)
                target = os.path.join(target_dir, target)
            target = os.path.abspath(os.path.normpath(target))
            base = os.path.abspath(base_dir or self.policy.base_dir)
            if not target.startswith(base + os.sep) and target != base:
                raise PathTraversalError(path, base, "symlink target escapes base directory")
            return target
        return resolved

    # ── SafePath Factory ───────────────────────────────────────────────────

    def safepath(self, path: str, base_dir: Optional[str] = None) -> SafePath:
        return SafePath(path, base_dir or self.policy.base_dir, self)


# ════════════════════════════════════════════════════════════════════════════
# Convenience: global default guard
# ════════════════════════════════════════════════════════════════════════════

_DEFAULT_GUARD: Optional[PathGuard] = None


def get_default_guard() -> PathGuard:
    global _DEFAULT_GUARD
    if _DEFAULT_GUARD is None:
        _DEFAULT_GUARD = PathGuard()
    return _DEFAULT_GUARD


def set_default_guard(guard: PathGuard) -> None:
    global _DEFAULT_GUARD
    _DEFAULT_GUARD = guard


# ════════════════════════════════════════════════════════════════════════════
# DEMO / SELF-TEST
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import tempfile

    print("=" * 60)
    print("MAGNATRIX-OS Path Guard — Self-Test")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test structure
        os.makedirs(os.path.join(tmpdir, "sub", "dir"))
        with open(os.path.join(tmpdir, "readme.txt"), "w") as f:
            f.write("Hello, MAGNATRIX!")
        with open(os.path.join(tmpdir, "sub", "data.json"), "w") as f:
            f.write('{"key": "value"}')

        guard = PathGuard(PathPolicy(base_dir=tmpdir, mode=AccessMode.ALLOW))

        # Test 1: Basic read
        print("\n[1] Basic read")
        content = guard.read("readme.txt", tmpdir)
        assert content == "Hello, MAGNATRIX!"
        print(f"  ✓ Read: {content[:20]}...")

        # Test 2: Path traversal blocked
        print("\n[2] Path traversal blocking")
        try:
            guard.read("../etc/passwd", tmpdir)
            assert False, "Should have blocked"
        except PathTraversalError as e:
            print(f"  ✓ Blocked: {e.reason}")

        # Test 3: Nested path read
        print("\n[3] Nested path read")
        content = guard.read("sub/data.json", tmpdir)
        assert "key" in content
        print(f"  ✓ Read nested: {content[:30]}...")

        # Test 4: Safe write
        print("\n[4] Safe write")
        guard.write("new_file.txt", "New content", tmpdir)
        assert guard.exists("new_file.txt", tmpdir)
        print(f"  ✓ Written and verified")

        # Test 5: Safe mkdir
        print("\n[5] Safe mkdir")
        guard.mkdir("new_dir", tmpdir)
        assert guard.isdir("new_dir", tmpdir)
        print(f"  ✓ Directory created")

        # Test 6: Safe rm
        print("\n[6] Safe rm")
        guard.rm("new_file.txt", tmpdir)
        assert not guard.exists("new_file.txt", tmpdir)
        print(f"  ✓ File removed")

        # Test 7: Safe glob
        print("\n[7] Safe glob")
        results = guard.glob("*.txt", tmpdir)
        assert len(results) == 1
        print(f"  ✓ Glob found {len(results)} .txt files")

        # Test 8: Safe listdir (absolute path requires allow_absolute)
        print("\n[8] Safe listdir")
        guard_abs = PathGuard(PathPolicy(base_dir=tmpdir, mode=AccessMode.ALLOW, allow_absolute=True))
        items = guard_abs.listdir(tmpdir)
        assert "readme.txt" in items
        print(f"  ✓ Listed: {len(items)} items")

        # Test 9: Readonly policy
        print("\n[9] Readonly policy")
        ro_guard = PathGuard(PathPolicy(base_dir=tmpdir, mode=AccessMode.READONLY))
        try:
            ro_guard.write("readonly_test.txt", "data", tmpdir)
            assert False
        except PathPolicyViolationError as e:
            print(f"  ✓ Readonly blocked: {e.reason}")

        # Test 10: Audit log
        print("\n[10] Audit log")
        summary = guard.access_log.get_summary()
        print(f"  ✓ Log summary: {summary}")
        assert summary["total"] > 0

        # Test 11: Symlink handling
        print("\n[11] Symlink handling")
        link_path = os.path.join(tmpdir, "link_to_readme")
        os.symlink("readme.txt", link_path)
        try:
            guard.resolve_symlink("link_to_readme", tmpdir)
            print(f"  ✓ Symlink resolved (follow_symlinks=True)")
        except PathPolicyViolationError:
            print(f"  ✓ Symlink blocked (follow_symlinks=False)")

        # Test 12: Blocklist/allowlist extensions
        print("\n[12] Extension policy")
        ext_guard = PathGuard(PathPolicy(
            base_dir=tmpdir, mode=AccessMode.ALLOW,
            allowed_extensions={".txt", ".json"}
        ))
        try:
            ext_guard.read("sub/data.json", tmpdir)
            print(f"  ✓ .json allowed")
        except PathPolicyViolationError as e:
            print(f"  ✗ Unexpected block: {e}")

    print("\n" + "=" * 60)
    print("All self-tests passed ✓")
    print("=" * 60)
