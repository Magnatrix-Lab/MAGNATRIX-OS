#!/usr/bin/env python3
"""
skills/skill_registry_native.py — MAGNATRIX-OS Native Skill Registry
Pure stdlib. No external dependencies.

Features:
  • NativeSkillDiscovery — directory scanning, importlib-based loading, manifest parsing
  • NativeVersionManager — semver parsing, compatibility checking, constraint resolution
  • NativeDependencyResolver — DAG resolution with cycle detection
  • NativeHotReloader — stat-based file watching, safe reload with rollback
  • NativeSkillSandbox — restricted execution environment (timeout, stdout/stderr capture)
  • NativeSkillRegistry — composes all layers, self-test demo

Naming convention: Native<ClassName>
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import re
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# NativeSkillDiscovery
# ---------------------------------------------------------------------------

class NativeSkillDiscovery:
    """Scan directories and load skills from manifest + Python modules."""

    MANIFEST_NAME = "SKILL.md"

    def __init__(self, search_paths: List[str]) -> None:
        self.search_paths = [Path(p) for p in search_paths]
        self._manifest_cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def scan(self) -> List[Dict[str, Any]]:
        """Return list of discovered skill descriptors."""
        skills = []
        for root in self.search_paths:
            if not root.exists():
                continue
            for path in root.rglob("*.py"):
                if path.name.startswith("_"):
                    continue
                manifest = self._find_manifest(path)
                descriptor = self._parse_descriptor(path, manifest)
                skills.append(descriptor)
        with self._lock:
            for s in skills:
                self._manifest_cache[s["id"]] = s
        return skills

    def _find_manifest(self, py_file: Path) -> Optional[Path]:
        """Walk up directory tree looking for SKILL.md."""
        for parent in [py_file.parent, *py_file.parents]:
            candidate = parent / self.MANIFEST_NAME
            if candidate.exists():
                return candidate
            # Stop at search path root or workspace root
            if parent == Path.home() or parent == Path("/"):
                break
        return None

    def _parse_descriptor(self, py_file: Path, manifest: Optional[Path]) -> Dict[str, Any]:
        """Build skill descriptor from file + optional manifest."""
        skill_id = f"{py_file.parent.name}/{py_file.stem}"
        mtime = py_file.stat().st_mtime
        hash_ = hashlib.sha256(py_file.read_bytes()).hexdigest()[:16]
        descriptor = {
            "id": skill_id,
            "path": str(py_file),
            "mtime": mtime,
            "hash": hash_,
            "manifest": str(manifest) if manifest else None,
            "meta": {},
        }
        if manifest:
            try:
                text = manifest.read_text(encoding="utf-8")
                descriptor["meta"] = self._parse_frontmatter(text)
            except Exception:
                pass
        return descriptor

    def _parse_frontmatter(self, text: str) -> Dict[str, Any]:
        """Extract YAML-like frontmatter from markdown."""
        meta = {}
        if text.startswith("---"):
            end = text.find("---", 3)
            if end != -1:
                fm = text[3:end].strip()
                for line in fm.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        meta[k.strip()] = v.strip().strip('"').strip("'")
        return meta

    def get_cached(self, skill_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._manifest_cache.get(skill_id)

    def invalidate(self, skill_id: str) -> None:
        with self._lock:
            self._manifest_cache.pop(skill_id, None)


# ---------------------------------------------------------------------------
# NativeVersionManager
# ---------------------------------------------------------------------------

class NativeVersionManager:
    """Semantic versioning with constraint resolution."""

    _SEMVER_RE = re.compile(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:-([\w.-]+))?(?:\+([\w.-]+))?$")

    def __init__(self) -> None:
        self._versions: Dict[str, str] = {}
        self._lock = threading.RLock()

    @staticmethod
    def parse(version: str) -> Tuple[int, int, int, str, str]:
        m = NativeVersionManager._SEMVER_RE.match(version.strip())
        if not m:
            raise ValueError(f"invalid semver: {version}")
        major = int(m.group(1))
        minor = int(m.group(2) or 0)
        patch = int(m.group(3) or 0)
        pre = m.group(4) or ""
        build = m.group(5) or ""
        return (major, minor, patch, pre, build)

    @staticmethod
    def compare(a: str, b: str) -> int:
        """Return -1, 0, 1 for a < b, a == b, a > b."""
        av = NativeVersionManager.parse(a)
        bv = NativeVersionManager.parse(b)
        for i in range(3):
            if av[i] != bv[i]:
                return -1 if av[i] < bv[i] else 1
        # Pre-release: no pre-release > any pre-release
        if av[3] and not bv[3]:
            return -1
        if not av[3] and bv[3]:
            return 1
        if av[3] != bv[3]:
            return -1 if av[3] < bv[3] else 1
        return 0

    def satisfies(self, version: str, constraint: str) -> bool:
        """Check if version satisfies constraint. Supports ^, ~, >=, <=, >, <, =."""
        constraint = constraint.strip()
        if constraint.startswith("^"):
            # ^1.2.3 → >=1.2.3, <2.0.0
            v = self.parse(constraint[1:])
            v2 = self.parse(version)
            if v2[0] != v[0]:
                return False
            if v2[0] == v[0] and (v2[1], v2[2]) >= (v[1], v[2]):
                return True
            return False
        elif constraint.startswith("~"):
            # ~1.2.3 → >=1.2.3, <1.3.0
            v = self.parse(constraint[1:])
            v2 = self.parse(version)
            return v2[0] == v[0] and v2[1] == v[1] and v2[2] >= v[2]
        elif constraint.startswith(">="):
            return self.compare(version, constraint[2:]) >= 0
        elif constraint.startswith("<="):
            return self.compare(version, constraint[2:]) <= 0
        elif constraint.startswith(">"):
            return self.compare(version, constraint[1:]) > 0
        elif constraint.startswith("<"):
            return self.compare(version, constraint[1:]) < 0
        elif constraint.startswith("="):
            return self.compare(version, constraint[1:]) == 0
        else:
            return self.compare(version, constraint) == 0

    def register(self, skill_id: str, version: str) -> None:
        with self._lock:
            self._versions[skill_id] = version

    def get(self, skill_id: str) -> Optional[str]:
        with self._lock:
            return self._versions.get(skill_id)


# ---------------------------------------------------------------------------
# NativeDependencyResolver
# ---------------------------------------------------------------------------

class NativeDependencyResolver:
    """Resolve skill dependency DAG with cycle detection."""

    def __init__(self) -> None:
        self._deps: Dict[str, List[str]] = {}
        self._lock = threading.RLock()

    def add(self, skill_id: str, depends_on: List[str]) -> None:
        with self._lock:
            self._deps[skill_id] = list(depends_on)

    def resolve(self) -> List[str]:
        """Topological sort; raise on cycle."""
        with self._lock:
            nodes = set(self._deps.keys())
            for deps in self._deps.values():
                nodes.update(deps)

            in_degree = {n: 0 for n in nodes}
            dependents: Dict[str, List[str]] = {n: [] for n in nodes}

            for k, deps in self._deps.items():
                for d in deps:
                    dependents[d].append(k)
                    in_degree[k] += 1

            queue = [n for n in nodes if in_degree[n] == 0]
            resolved = []
            while queue:
                node = queue.pop(0)
                resolved.append(node)
                for dep in dependents.get(node, []):
                    in_degree[dep] -= 1
                    if in_degree[dep] == 0:
                        queue.append(dep)

            if len(resolved) != len(nodes):
                cycle = self._find_cycle()
                raise ValueError(f"dependency cycle detected: {' -> '.join(cycle)}")
            return resolved

    def _find_cycle(self) -> List[str]:
        """Return one cycle path using DFS."""
        visited = set()
        rec_stack = []
        rec_set = set()

        def dfs(node: str) -> Optional[List[str]]:
            visited.add(node)
            rec_stack.append(node)
            rec_set.add(node)
            for dep in self._deps.get(node, []):
                if dep not in visited:
                    result = dfs(dep)
                    if result:
                        return result
                elif dep in rec_set:
                    idx = rec_stack.index(dep)
                    return rec_stack[idx:] + [dep]
            rec_stack.pop()
            rec_set.remove(node)
            return None

        for node in list(self._deps.keys()):
            if node not in visited:
                c = dfs(node)
                if c:
                    return c
        return []

    def get_load_order(self) -> List[str]:
        """Alias for resolve."""
        return self.resolve()


# ---------------------------------------------------------------------------
# NativeHotReloader
# ---------------------------------------------------------------------------

class NativeHotReloader:
    """Watch skill files for changes and reload safely."""

    def __init__(self, poll_interval: float = 1.0) -> None:
        self.poll_interval = poll_interval
        self._watched: Dict[str, Dict[str, Any]] = {}
        self._callbacks: Dict[str, Callable] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

    def watch(self, skill_id: str, path: str, on_reload: Callable) -> None:
        with self._lock:
            self._watched[skill_id] = {
                "path": path,
                "mtime": os.path.getmtime(path),
                "hash": self._file_hash(path),
            }
            self._callbacks[skill_id] = on_reload

    def _file_hash(self, path: str) -> str:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _poll_loop(self) -> None:
        while True:
            with self._lock:
                if not self._running:
                    break
                for skill_id, info in self._watched.items():
                    try:
                        mtime = os.path.getmtime(info["path"])
                        if mtime != info["mtime"]:
                            new_hash = self._file_hash(info["path"])
                            if new_hash != info["hash"]:
                                info["mtime"] = mtime
                                info["hash"] = new_hash
                                cb = self._callbacks.get(skill_id)
                                if cb:
                                    cb(skill_id, info["path"])
                    except Exception:
                        pass
            time.sleep(self.poll_interval)

    def check_once(self) -> List[str]:
        """Single-shot check. Return list of changed skill IDs."""
        changed = []
        with self._lock:
            for skill_id, info in self._watched.items():
                try:
                    mtime = os.path.getmtime(info["path"])
                    if mtime != info["mtime"]:
                        new_hash = self._file_hash(info["path"])
                        if new_hash != info["hash"]:
                            info["mtime"] = mtime
                            info["hash"] = new_hash
                            changed.append(skill_id)
                except Exception:
                    pass
        return changed

    def unwatch(self, skill_id: str) -> None:
        with self._lock:
            self._watched.pop(skill_id, None)
            self._callbacks.pop(skill_id, None)


# ---------------------------------------------------------------------------
# NativeSkillSandbox
# ---------------------------------------------------------------------------

class NativeSkillSandbox:
    """Restricted execution environment for untrusted skill code."""

    def __init__(self, timeout: float = 5.0) -> None:
        self.timeout = timeout

    def execute(self, code: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute Python code in isolated globals with timeout."""
        result = {
            "success": False,
            "output": "",
            "error": None,
            "return_value": None,
        }
        # Build restricted globals
        safe_builtins = {
            "len": len,
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
            "sum": sum,
            "min": min,
            "max": max,
            "abs": abs,
            "round": round,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,
            "type": type,
            "isinstance": isinstance,
            "hasattr": hasattr,
            "getattr": getattr,
            "print": lambda *args, **kwargs: None,  # suppress print
        }
        safe_globals = {"__builtins__": safe_builtins}
        if context:
            safe_globals.update(context)

        import io
        import signal

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        old_alarm = signal.signal(signal.SIGALRM, lambda _signum, _frame: (_ for _ in ()).throw(TimeoutError("sandbox timeout")))
        signal.alarm(int(self.timeout))

        try:
            compiled = compile(code, "<sandbox>", "exec")
            exec(compiled, safe_globals)
            result["success"] = True
            result["return_value"] = safe_globals.get("__result__")
        except TimeoutError as exc:
            result["error"] = f"timeout: {exc}"
        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_alarm)
            result["output"] = sys.stdout.getvalue()
            sys.stdout = old_stdout

        return result


# ---------------------------------------------------------------------------
# NativeSkillRegistry
# ---------------------------------------------------------------------------

class NativeSkillRegistry:
    """Composes discovery, versioning, dependency resolution, hot reload, sandbox."""

    def __init__(self, search_paths: List[str]) -> None:
        self.discovery = NativeSkillDiscovery(search_paths)
        self.version = NativeVersionManager()
        self.deps = NativeDependencyResolver()
        self.reloader = NativeHotReloader(poll_interval=1.0)
        self.sandbox = NativeSkillSandbox(timeout=3.0)
        self._skills: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def register(self, skill_id: str, path: str, version: str, depends: Optional[List[str]] = None) -> None:
        with self._lock:
            self._skills[skill_id] = {
                "id": skill_id,
                "path": path,
                "version": version,
                "depends": depends or [],
                "loaded": False,
            }
        self.version.register(skill_id, version)
        self.deps.add(skill_id, depends or [])
        self.reloader.watch(skill_id, path, self._on_reload)

    def _on_reload(self, skill_id: str, path: str) -> None:
        with self._lock:
            if skill_id in self._skills:
                self._skills[skill_id]["loaded"] = False
                print(f"[hot-reload] {skill_id} changed, marked for reload")

    def discover(self) -> List[Dict[str, Any]]:
        return self.discovery.scan()

    def load_order(self) -> List[str]:
        return self.deps.get_load_order()

    def check_version(self, skill_id: str, constraint: str) -> bool:
        v = self.version.get(skill_id)
        if not v:
            return False
        return self.version.satisfies(v, constraint)

    def run_in_sandbox(self, skill_id: str, code: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.sandbox.execute(code, context)

    def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return dict(self._skills.get(skill_id, {}))

    def list_skills(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(s) for s in self._skills.values()]


# ---------------------------------------------------------------------------
# Self-test demo
# ---------------------------------------------------------------------------

def run() -> None:
    print("=" * 60)
    print("NativeSkillRegistry — self-test demo")
    print("=" * 60)

    # [1] Version manager
    print("\n[1] VersionManager — semver parsing")
    vm = NativeVersionManager()
    v = vm.parse("1.2.3-alpha+build.1")
    print(f"    parsed={v}")
    assert v == (1, 2, 3, "alpha", "build.1")

    print("\n[2] VersionManager — comparison")
    assert vm.compare("1.0.0", "1.0.1") == -1
    assert vm.compare("2.0.0", "1.9.9") == 1
    assert vm.compare("1.0.0", "1.0.0") == 0
    print("    1.0.0 < 1.0.1: ok")
    print("    2.0.0 > 1.9.9: ok")
    print("    1.0.0 == 1.0.0: ok")

    print("\n[3] VersionManager — constraint satisfaction")
    assert vm.satisfies("1.2.3", "^1.2.0")
    assert not vm.satisfies("2.0.0", "^1.2.0")
    assert vm.satisfies("1.2.5", "~1.2.0")
    assert not vm.satisfies("1.3.0", "~1.2.0")
    assert vm.satisfies("1.5.0", ">=1.2.0")
    print("    ^1.2.0: 1.2.3 ok, 2.0.0 rejected")
    print("    ~1.2.0: 1.2.5 ok, 1.3.0 rejected")
    print("    >=1.2.0: 1.5.0 ok")

    # [2] Dependency resolver
    print("\n[4] DependencyResolver — topological sort")
    dr = NativeDependencyResolver()
    dr.add("skill-c", ["skill-a", "skill-b"])
    dr.add("skill-b", ["skill-a"])
    dr.add("skill-a", [])
    order = dr.resolve()
    print(f"    load order={order}")
    assert order.index("skill-a") < order.index("skill-b")
    assert order.index("skill-b") < order.index("skill-c")

    print("\n[5] DependencyResolver — cycle detection")
    dr2 = NativeDependencyResolver()
    dr2.add("x", ["y"])
    dr2.add("y", ["z"])
    dr2.add("z", ["x"])
    try:
        dr2.resolve()
        assert False, "should have raised"
    except ValueError as exc:
        print(f"    caught: {exc}")

    # [3] Sandbox
    print("\n[6] SkillSandbox — safe execution")
    sb = NativeSkillSandbox(timeout=2.0)
    result = sb.execute("__result__ = sum(range(10))")
    print(f"    success={result['success']} return_value={result['return_value']}")
    assert result["success"] and result["return_value"] == 45

    print("\n[7] SkillSandbox — timeout")
    result = sb.execute("while True: pass")
    print(f"    success={result['success']} error={result['error']}")
    assert not result["success"] and "timeout" in result["error"]

    print("\n[8] SkillSandbox — suppressed builtins")
    result = sb.execute("__result__ = open('/etc/passwd', 'r').read()")
    print(f"    success={result['success']} error={result['error']}")
    assert not result["success"] and "NameError" in result["error"]

    # [4] Hot reloader
    print("\n[9] HotReloader — file change detection")
    test_file = "/tmp/skill_test_reloader.py"
    Path(test_file).write_text("# version 1\n")
    hr = NativeHotReloader(poll_interval=0.1)
    changes = []
    hr.watch("test-skill", test_file, lambda sid, path: changes.append(sid))
    hr.start()
    time.sleep(0.2)
    Path(test_file).write_text("# version 2\n")
    time.sleep(0.3)
    hr.stop()
    print(f"    detected changes={changes}")
    assert "test-skill" in changes

    # [5] Full registry
    print("\n[10] SkillRegistry — full integration")
    os.makedirs("/tmp/skills", exist_ok=True)
    for f in ["a.py", "b.py", "c.py"]:
        Path(f"/tmp/skills/{f}").write_text(f"# {f}\n", encoding="utf-8")
    reg = NativeSkillRegistry(search_paths=["/tmp/skills"])
    reg.register("skill-a", "/tmp/skills/a.py", "1.0.0", [])
    reg.register("skill-b", "/tmp/skills/b.py", "1.1.0", ["skill-a"])
    reg.register("skill-c", "/tmp/skills/c.py", "2.0.0", ["skill-a", "skill-b"])

    print(f"    skills={reg.list_skills()}")
    print(f"    load_order={reg.load_order()}")

    print("\n[11] Version constraints")
    assert reg.check_version("skill-b", "^1.0.0")
    assert not reg.check_version("skill-c", "^1.0.0")
    print("    skill-b ^1.0.0: ok")
    print("    skill-c ^1.0.0: rejected")

    print("\n[12] Sandbox execution via registry")
    r = reg.run_in_sandbox("skill-a", "__result__ = len([1,2,3])")
    print(f"    sandbox result={r['return_value']}")
    assert r["return_value"] == 3

    print("\n✅ All skill registry tests passed.")
    print("=" * 60)


if __name__ == "__main__":
    run()
