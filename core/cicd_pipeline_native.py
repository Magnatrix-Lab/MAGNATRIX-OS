#!/usr/bin/env python3
"""
CI/CD Pipeline Native — Pure-Python Build Automation for MAGNATRIX-OS
=====================================================================
Zero-dependency continuous integration, delivery, and deployment engine.
Covers: build automation, test running, release packaging, auto-deploy,
pipeline orchestration, artifact registry, dashboard integration, health checks.

Author:    GQRIS (MAGNATRIX-OS)
File:      core/cicd_pipeline_native.py
Version:   1.0.0
"""

from __future__ import annotations

import ast
import compileall
import enum
import hashlib
import importlib.util
import json
import os
import pathlib
import py_compile
import queue
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import traceback
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_BASE_DIR = "/mnt/agents/MAGNATRIX-OS"
ARTIFACT_DIR = os.path.join(DEFAULT_BASE_DIR, "artifacts")
LOG_DIR = os.path.join(DEFAULT_BASE_DIR, "logs", "cicd")
CACHE_DIR = os.path.join(DEFAULT_BASE_DIR, ".cicd_cache")
DASHBOARD_HOOK_URL = "http://localhost:8765/cicd/status"

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


class BuildStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


class DeployStrategy(enum.Enum):
    HOT_RELOAD = "hot_reload"
    BLUE_GREEN = "blue_green"
    ROLLING = "rolling"
    CANARY = "canary"


@dataclass(frozen=True, slots=True)
class ModuleInfo:
    name: str
    path: str
    relative_path: str
    size: int
    mtime: float
    hash: str
    imports: Tuple[str, ...]
    imports_internal: Tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TestResult:
    file: str
    status: BuildStatus
    duration: float
    stdout: str
    stderr: str
    exit_code: int
    coverage: float = 0.0


@dataclass(frozen=True, slots=True)
class Artifact:
    name: str
    version: str
    path: str
    checksum: str
    size: int
    created_at: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PipelineStage:
    name: str
    condition: Optional[Callable[[PipelineContext], bool]] = None
    steps: Tuple[Callable[[PipelineContext], None], ...] = field(default_factory=tuple)
    allow_failure: bool = False
    timeout: float = 300.0


@dataclass
class PipelineContext:
    build_id: str
    start_time: float
    base_dir: str
    target_dir: str
    modules: List[ModuleInfo] = field(default_factory=list)
    build_order: List[str] = field(default_factory=list)
    test_results: List[TestResult] = field(default_factory=list)
    artifacts: List[Artifact] = field(default_factory=list)
    deployed_version: str = ""
    previous_version: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)
    status: Dict[str, BuildStatus] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def log(self, message: str) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        entry = f"[{ts}] {message}"
        with self.lock:
            self.logs.append(entry)

    def set(self, key: str, value: Any) -> None:
        with self.lock:
            self.variables[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        with self.lock:
            return self.variables.get(key, default)


# ---------------------------------------------------------------------------
# 1. Build Automation — Module Discovery & Compilation
# ---------------------------------------------------------------------------


class BuildAutomation:
    """Discovers native modules, checks syntax, builds dependency graph, orders builds."""

    def __init__(self, base_dir: str = DEFAULT_BASE_DIR) -> None:
        self.base_dir = pathlib.Path(base_dir).resolve()
        self.cache_file = pathlib.Path(CACHE_DIR) / "build_cache.json"
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Dict[str, Any]] = self._load_cache()

    # --- discovery ----------------------------------------------------------

    def discover_modules(self, pattern: str = "*_native.py") -> List[ModuleInfo]:
        modules: List[ModuleInfo] = []
        for py_file in sorted(self.base_dir.rglob(pattern)):
            if "__pycache__" in str(py_file):
                continue
            info = self._analyze_module(py_file)
            if info:
                modules.append(info)
        return modules

    def _analyze_module(self, path: pathlib.Path) -> Optional[ModuleInfo]:
        rel = path.relative_to(self.base_dir)
        name = str(rel).replace(os.sep, ".").replace(".py", "")
        try:
            src = path.read_text(encoding="utf-8")
        except Exception:
            return None
        size = path.stat().st_size
        mtime = path.stat().st_mtime
        file_hash = hashlib.sha256(src.encode()).hexdigest()[:16]

        # Parse imports
        imports: List[str] = []
        imports_internal: List[str] = []
        try:
            tree = ast.parse(src)
        except SyntaxError:
            return None

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imports.append(module)
                # Detect internal MAGNATRIX-OS imports
                if module.startswith("MAGNATRIX") or module.startswith("core") or module.startswith("ai") or module.startswith("trading") or module.startswith("knowledge") or module.startswith("runtime") or module.startswith("data") or module.startswith("security") or module.startswith("kernel") or module.startswith("governance") or module.startswith("research") or module.startswith("infrastructure") or module.startswith("protocol") or module.startswith("multimodal") or module.startswith("observability") or module.startswith("p2p_mesh") or module.startswith("queue") or module.startswith("registry") or module.startswith("api_gateway") or module.startswith("streaming") or module.startswith("workflows") or module.startswith("uncensored") or module.startswith("web_ui") or module.startswith("ide") or module.startswith("tests") or module.startswith("skills") or module.startswith("auto_repo_hunter") or module.startswith("packaging") or module.startswith("collective_brain"):
                    imports_internal.append(module)

        return ModuleInfo(
            name=name,
            path=str(path),
            relative_path=str(rel),
            size=size,
            mtime=mtime,
            hash=file_hash,
            imports=tuple(imports),
            imports_internal=tuple(imports_internal),
        )

    # --- compilation check --------------------------------------------------

    def compile_check(self, modules: List[ModuleInfo]) -> Tuple[List[str], List[str]]:
        passed: List[str] = []
        failed: List[str] = []
        for mod in modules:
            try:
                py_compile.compile(mod.path, doraise=True)
                passed.append(mod.name)
            except py_compile.PyCompileError as e:
                failed.append(f"{mod.name}: {e}")
        return passed, failed

    # --- dependency graph -------------------------------------------------

    def build_dependency_graph(self, modules: List[ModuleInfo]) -> Dict[str, Set[str]]:
        graph: Dict[str, Set[str]] = {m.name: set() for m in modules}
        name_to_mod = {m.name: m for m in modules}

        for mod in modules:
            for imp in mod.imports_internal:
                # Match import to internal module name
                for candidate in name_to_mod:
                    if candidate.endswith(imp.split(".")[-1]) or candidate == imp or candidate.replace(".", "_") == imp.replace(".", "_"):
                        if candidate != mod.name:
                            graph[mod.name].add(candidate)
        return graph

    def detect_cycles(self, graph: Dict[str, Set[str]]) -> List[List[str]]:
        cycles: List[List[str]] = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in graph.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor, path + [neighbor])
                elif neighbor in rec_stack:
                    idx = path.index(neighbor) if neighbor in path else 0
                    cycle = path[idx:] + [neighbor]
                    cycles.append(cycle)
            rec_stack.remove(node)

        for node in graph:
            if node not in visited:
                dfs(node, [node])
        return cycles

    def topological_order(self, graph: Dict[str, Set[str]]) -> List[str]:
        in_degree = {n: 0 for n in graph}
        for deps in graph.values():
            for d in deps:
                if d in in_degree:
                    in_degree[d] += 1

        # Kahn's algorithm
        ready = [n for n, d in in_degree.items() if d == 0]
        order: List[str] = []
        while ready:
            node = ready.pop(0)
            order.append(node)
            for dependent, deps in graph.items():
                if node in deps:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        ready.append(dependent)
        return order

    # --- incremental build --------------------------------------------------

    def incremental_build_needed(self, modules: List[ModuleInfo]) -> List[ModuleInfo]:
        changed: List[ModuleInfo] = []
        for mod in modules:
            cached = self._cache.get(mod.name)
            if not cached or cached.get("hash") != mod.hash:
                changed.append(mod)
        return changed

    def save_cache(self, modules: List[ModuleInfo]) -> None:
        for mod in modules:
            self._cache[mod.name] = {"hash": mod.hash, "mtime": mod.mtime}
        self.cache_file.write_text(json.dumps(self._cache, indent=2), encoding="utf-8")

    def _load_cache(self) -> Dict[str, Dict[str, Any]]:
        if self.cache_file.exists():
            try:
                return json.loads(self.cache_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    # --- run ----------------------------------------------------------------

    def run(self, ctx: PipelineContext) -> None:
        ctx.log("BuildAutomation: discovering modules...")
        modules = self.discover_modules()
        ctx.modules = modules
        ctx.set("total_modules", len(modules))
        ctx.log(f"BuildAutomation: found {len(modules)} native modules")

        # Incremental
        changed = self.incremental_build_needed(modules)
        ctx.set("changed_modules", [m.name for m in changed])
        ctx.log(f"BuildAutomation: {len(changed)} modules changed since last build")

        # Compile check
        ctx.log("BuildAutomation: running compile check...")
        passed, failed = self.compile_check(modules)
        ctx.set("compile_passed", passed)
        ctx.set("compile_failed", failed)
        if failed:
            for f in failed:
                ctx.log(f"BuildAutomation: COMPILE ERROR: {f}")
        ctx.log(f"BuildAutomation: compile check — {len(passed)} passed, {len(failed)} failed")

        # Dependency graph
        graph = self.build_dependency_graph(modules)
        ctx.set("dependency_graph", {k: list(v) for k, v in graph.items()})
        cycles = self.detect_cycles(graph)
        ctx.set("cycles", cycles)
        if cycles:
            for c in cycles:
                ctx.log(f"BuildAutomation: CYCLE DETECTED: {' -> '.join(c)}")
        order = self.topological_order(graph)
        ctx.build_order = order
        ctx.set("build_order", order)
        ctx.log(f"BuildAutomation: topological build order has {len(order)} modules")

        self.save_cache(modules)
        ctx.log("BuildAutomation: cache updated")


# ---------------------------------------------------------------------------
# 2. Test Runner — Auto-Discovery, Parallel Execution, Coverage
# ---------------------------------------------------------------------------


class TestRunner:
    """Discovers and runs test files, collects coverage, reports results."""

    def __init__(self, base_dir: str = DEFAULT_BASE_DIR, max_workers: int = 4) -> None:
        self.base_dir = pathlib.Path(base_dir)
        self.max_workers = max_workers

    def discover_tests(self, pattern: str = "test_*.py") -> List[pathlib.Path]:
        tests: List[pathlib.Path] = []
        for p in sorted(self.base_dir.rglob(pattern)):
            tests.append(p)
        # Also look for *_test.py
        for p in sorted(self.base_dir.rglob("*_test.py")):
            if p not in tests:
                tests.append(p)
        return sorted(tests)

    def run_single_test(self, test_path: pathlib.Path, timeout: float = 60.0) -> TestResult:
        start = time.time()
        try:
            # Run with python -m py_compile + exec for simple tests
            proc = subprocess.run(
                [sys.executable, str(test_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.base_dir),
            )
            duration = time.time() - start
            status = BuildStatus.SUCCESS if proc.returncode == 0 else BuildStatus.FAILED
            if proc.returncode != 0 and duration >= timeout:
                status = BuildStatus.TIMEOUT

            # Naive coverage estimation: count lines starting with "def test_" vs executed
            coverage = self._estimate_coverage(test_path, proc.stdout + proc.stderr)

            return TestResult(
                file=str(test_path.relative_to(self.base_dir)),
                status=status,
                duration=duration,
                stdout=proc.stdout[-2000:] if len(proc.stdout) > 2000 else proc.stdout,
                stderr=proc.stderr[-2000:] if len(proc.stderr) > 2000 else proc.stderr,
                exit_code=proc.returncode,
                coverage=coverage,
            )
        except subprocess.TimeoutExpired:
            return TestResult(
                file=str(test_path.relative_to(self.base_dir)),
                status=BuildStatus.TIMEOUT,
                duration=time.time() - start,
                stdout="",
                stderr="Test timed out",
                exit_code=-1,
                coverage=0.0,
            )
        except Exception as e:
            return TestResult(
                file=str(test_path.relative_to(self.base_dir)),
                status=BuildStatus.FAILED,
                duration=time.time() - start,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                coverage=0.0,
            )

    def _estimate_coverage(self, test_path: pathlib.Path, output: str) -> float:
        # Very naive: count test functions and compare to "OK" or "PASS" mentions
        try:
            src = test_path.read_text(encoding="utf-8")
        except Exception:
            return 0.0
        test_count = len(re.findall(r"^def\s+test_", src, re.MULTILINE))
        if test_count == 0:
            return 0.0
        pass_mentions = len(re.findall(r"\b(OK|PASS|passed|success)\b", output, re.IGNORECASE))
        return min(100.0, (pass_mentions / test_count) * 100.0)

    def run(self, ctx: PipelineContext, sequential: bool = False) -> None:
        ctx.log("TestRunner: discovering test files...")
        tests = self.discover_tests()
        ctx.set("test_files", [str(t) for t in tests])
        ctx.log(f"TestRunner: found {len(tests)} test files")

        results: List[TestResult] = []
        if sequential or len(tests) <= 1:
            for t in tests:
                ctx.log(f"TestRunner: running {t.name}...")
                results.append(self.run_single_test(t))
        else:
            ctx.log(f"TestRunner: running {len(tests)} tests in parallel (max {self.max_workers} workers)")
            q: queue.Queue[Tuple[int, TestResult]] = queue.Queue()
            threads: List[threading.Thread] = []

            def worker(idx: int, test_path: pathlib.Path) -> None:
                q.put((idx, self.run_single_test(test_path)))

            for i, t in enumerate(tests):
                th = threading.Thread(target=worker, args=(i, t))
                th.start()
                threads.append(th)
                # Limit concurrent
                if len(threads) >= self.max_workers:
                    threads[0].join(timeout=120)
                    threads.pop(0)

            for th in threads:
                th.join(timeout=120)

            # Collect
            temp_results: Dict[int, TestResult] = {}
            while not q.empty():
                idx, result = q.get()
                temp_results[idx] = result
            results = [temp_results[i] for i in range(len(tests)) if i in temp_results]

        ctx.test_results = results
        passed = sum(1 for r in results if r.status == BuildStatus.SUCCESS)
        failed = sum(1 for r in results if r.status != BuildStatus.SUCCESS)
        avg_coverage = sum(r.coverage for r in results) / len(results) if results else 0.0
        ctx.set("test_passed", passed)
        ctx.set("test_failed", failed)
        ctx.set("test_coverage_avg", round(avg_coverage, 2))
        ctx.log(f"TestRunner: {passed} passed, {failed} failed, avg coverage {avg_coverage:.1f}%")

        for r in results:
            if r.status != BuildStatus.SUCCESS:
                ctx.log(f"TestRunner: FAIL {r.file} — exit={r.exit_code}, stderr={r.stderr[:120]}")


# ---------------------------------------------------------------------------
# 3. Release Packager — Version Bump, Changelog, Package, Checksum
# ---------------------------------------------------------------------------


class ReleasePackager:
    """Versions releases, generates changelogs, creates distributable archives."""

    def __init__(self, base_dir: str = DEFAULT_BASE_DIR, artifact_dir: str = ARTIFACT_DIR) -> None:
        self.base_dir = pathlib.Path(base_dir)
        self.artifact_dir = pathlib.Path(artifact_dir)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.version_file = self.base_dir / "VERSION"
        self.changelog_file = self.base_dir / "CHANGELOG.md"

    def get_current_version(self) -> str:
        if self.version_file.exists():
            return self.version_file.read_text(encoding="utf-8").strip()
        return "0.0.0"

    def bump_version(self, bump_type: str = "patch") -> str:
        version = self.get_current_version()
        parts = version.split(".")
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            parts = ["0", "0", "0"]
        major, minor, patch = map(int, parts)
        if bump_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif bump_type == "minor":
            minor += 1
            patch = 0
        else:
            patch += 1
        new_version = f"{major}.{minor}.{patch}"
        self.version_file.write_text(new_version + "\n", encoding="utf-8")
        return new_version

    def generate_changelog(self, ctx: PipelineContext) -> str:
        version = ctx.get("new_version", "unknown")
        build_id = ctx.build_id
        modules = ctx.get("total_modules", 0)
        passed = ctx.get("test_passed", 0)
        failed = ctx.get("test_failed", 0)
        lines = [
            f"## [{version}] — {time.strftime('%Y-%m-%d')}",
            "",
            f"- Build ID: `{build_id}`",
            f"- Modules: {modules}",
            f"- Tests: {passed} passed, {failed} failed",
            f"- Build order: {len(ctx.build_order)} modules",
            f"- Cycles detected: {len(ctx.get('cycles', []))}",
            "",
        ]
        # Append to changelog
        existing = ""
        if self.changelog_file.exists():
            existing = self.changelog_file.read_text(encoding="utf-8")
        new_entry = "\n".join(lines)
        self.changelog_file.write_text(new_entry + "\n" + existing, encoding="utf-8")
        return new_entry

    def package(self, ctx: PipelineContext, fmt: str = "tar.gz") -> Artifact:
        version = ctx.get("new_version", "dev")
        build_id = ctx.build_id
        name = f"magnatrix-os-{version}-{build_id}"

        # Create temp staging
        staging = pathlib.Path(tempfile.mkdtemp(prefix="magnatrix_pkg_"))
        target = staging / f"magnatrix-os-{version}"
        shutil.copytree(self.base_dir, target, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".cicd_cache", "artifacts"))

        # Write build manifest
        manifest = {
            "version": version,
            "build_id": build_id,
            "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "modules": ctx.build_order,
            "tests": {"passed": ctx.get("test_passed", 0), "failed": ctx.get("test_failed", 0)},
        }
        (target / "BUILD_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        # Package
        if fmt == "tar.gz":
            out_path = self.artifact_dir / f"{name}.tar.gz"
            with tarfile.open(out_path, "w:gz") as tar:
                tar.add(target, arcname=target.name)
        elif fmt == "zip":
            out_path = self.artifact_dir / f"{name}.zip"
            with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in target.rglob("*"):
                    zf.write(f, arcname=str(f.relative_to(staging)))
        else:
            raise ValueError(f"Unsupported format: {fmt}")

        # Checksum
        checksum = hashlib.sha256(out_path.read_bytes()).hexdigest()
        (out_path.parent / f"{out_path.name}.sha256").write_text(checksum + "\n", encoding="utf-8")

        # Cleanup staging
        shutil.rmtree(staging)

        artifact = Artifact(
            name=name,
            version=version,
            path=str(out_path),
            checksum=checksum,
            size=out_path.stat().st_size,
            created_at=time.time(),
            metadata=manifest,
        )
        ctx.artifacts.append(artifact)
        return artifact

    def run(self, ctx: PipelineContext, bump_type: str = "patch") -> None:
        ctx.log("ReleasePackager: bumping version...")
        new_version = self.bump_version(bump_type)
        ctx.set("new_version", new_version)
        ctx.log(f"ReleasePackager: version bumped to {new_version}")

        ctx.log("ReleasePackager: generating changelog...")
        changelog = self.generate_changelog(ctx)
        ctx.set("changelog", changelog)
        ctx.log("ReleasePackager: changelog updated")

        ctx.log("ReleasePackager: packaging release...")
        artifact = self.package(ctx, fmt="tar.gz")
        ctx.log(f"ReleasePackager: artifact created — {artifact.name} ({artifact.size} bytes)")
        ctx.log(f"ReleasePackager: SHA256 {artifact.checksum}")


# ---------------------------------------------------------------------------
# 4. Auto-Deploy — Hot Reload, Blue-Green, Rollback
# ---------------------------------------------------------------------------


class AutoDeploy:
    """Deployment automation with hot-reload, blue-green, and rollback support."""

    def __init__(self, base_dir: str = DEFAULT_BASE_DIR) -> None:
        self.base_dir = pathlib.Path(base_dir)
        self.deploy_dir = self.base_dir / "deploy"
        self.active_link = self.deploy_dir / "active"
        self.green_dir = self.deploy_dir / "green"
        self.blue_dir = self.deploy_dir / "blue"
        self.deploy_dir.mkdir(parents=True, exist_ok=True)
        self.green_dir.mkdir(exist_ok=True)
        self.blue_dir.mkdir(exist_ok=True)
        self._lock = threading.Lock()

    def _current_color(self) -> str:
        if self.active_link.exists() and os.readlink(self.active_link) == str(self.green_dir):
            return "green"
        return "blue"

    def hot_reload(self, ctx: PipelineContext) -> None:
        ctx.log("AutoDeploy: hot-reloading modules...")
        reloaded = 0
        for mod_name in ctx.build_order:
            mod_path = self.base_dir / f"{mod_name.replace('.', os.sep)}.py"
            if mod_path.exists():
                # In a real system, this would trigger module reload
                # Here we simulate by touching the file to signal readiness
                os.utime(mod_path, None)
                reloaded += 1
        ctx.set("hot_reloaded_count", reloaded)
        ctx.log(f"AutoDeploy: hot-reloaded {reloaded} modules")

    def blue_green_deploy(self, ctx: PipelineContext, artifact: Artifact) -> None:
        current = self._current_color()
        next_color = "blue" if current == "green" else "green"
        next_dir = self.blue_dir if next_color == "blue" else self.green_dir

        ctx.log(f"AutoDeploy: blue-green deploy — current={current}, next={next_color}")

        # Extract artifact to next dir
        if tarfile.is_tarfile(artifact.path):
            with tarfile.open(artifact.path, "r:gz") as tar:
                tar.extractall(path=next_dir.parent)
        # Move extracted folder to next_dir
        extracted = next_dir.parent / f"magnatrix-os-{artifact.version}"
        if extracted.exists():
            if next_dir.exists():
                shutil.rmtree(next_dir)
            shutil.move(str(extracted), str(next_dir))

        # Atomic switch
        with self._lock:
            if self.active_link.exists() or os.path.islink(self.active_link):
                os.unlink(self.active_link)
            os.symlink(str(next_dir), str(self.active_link))

        ctx.set("deployed_color", next_color)
        ctx.set("deployed_version", artifact.version)
        ctx.log(f"AutoDeploy: switched to {next_color} — version {artifact.version}")

    def rollback(self, ctx: PipelineContext) -> bool:
        current = self._current_color()
        prev_color = "blue" if current == "green" else "green"
        prev_dir = self.blue_dir if prev_color == "blue" else self.green_dir

        if not prev_dir.exists():
            ctx.log("AutoDeploy: rollback failed — previous deployment not found")
            return False

        with self._lock:
            if self.active_link.exists() or os.path.islink(self.active_link):
                os.unlink(self.active_link)
            os.symlink(str(prev_dir), str(self.active_link))

        ctx.set("deployed_color", prev_color)
        ctx.log(f"AutoDeploy: rolled back to {prev_color}")
        return True

    def run(self, ctx: PipelineContext, strategy: DeployStrategy = DeployStrategy.BLUE_GREEN) -> None:
        if not ctx.artifacts:
            ctx.log("AutoDeploy: no artifacts to deploy")
            return
        artifact = ctx.artifacts[-1]

        if strategy == DeployStrategy.HOT_RELOAD:
            self.hot_reload(ctx)
        elif strategy == DeployStrategy.BLUE_GREEN:
            self.blue_green_deploy(ctx, artifact)
        else:
            ctx.log(f"AutoDeploy: strategy {strategy.value} not fully implemented, using hot reload")
            self.hot_reload(ctx)


# ---------------------------------------------------------------------------
# 5. Pipeline Orchestrator — Stages, Conditions, Timeouts
# ---------------------------------------------------------------------------


class PipelineOrchestrator:
    """GitHub Actions / GitLab CI equivalent — stage-based pipeline execution."""

    def __init__(self) -> None:
        self.stages: List[PipelineStage] = []

    def add_stage(self, stage: PipelineStage) -> None:
        self.stages.append(stage)

    def run(self, ctx: PipelineContext) -> None:
        ctx.log("PipelineOrchestrator: starting pipeline execution...")
        for stage in self.stages:
            ctx.status[stage.name] = BuildStatus.IN_PROGRESS
            ctx.log(f"PipelineOrchestrator: stage '{stage.name}' starting")

            # Condition check
            if stage.condition and not stage.condition(ctx):
                ctx.status[stage.name] = BuildStatus.SKIPPED
                ctx.log(f"PipelineOrchestrator: stage '{stage.name}' skipped (condition)")
                continue

            try:
                start = time.time()
                for step in stage.steps:
                    if time.time() - start > stage.timeout:
                        raise TimeoutError(f"Stage '{stage.name}' exceeded {stage.timeout}s")
                    step(ctx)
                ctx.status[stage.name] = BuildStatus.SUCCESS
                ctx.log(f"PipelineOrchestrator: stage '{stage.name}' completed")
            except Exception as e:
                ctx.status[stage.name] = BuildStatus.FAILED
                ctx.log(f"PipelineOrchestrator: stage '{stage.name}' FAILED — {e}")
                if not stage.allow_failure:
                    ctx.log("PipelineOrchestrator: aborting pipeline (stage failure)")
                    break

        summary = {k: v.value for k, v in ctx.status.items()}
        ctx.set("pipeline_summary", summary)
        ctx.log(f"PipelineOrchestrator: pipeline complete — {summary}")


# ---------------------------------------------------------------------------
# 6. Artifact Registry — Local Storage, Versioning, Retention
# ---------------------------------------------------------------------------


class ArtifactRegistry:
    """Local artifact registry with metadata, retention, and lookup."""

    def __init__(self, artifact_dir: str = ARTIFACT_DIR) -> None:
        self.artifact_dir = pathlib.Path(artifact_dir)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.artifact_dir / "registry_index.json"
        self._index: List[Dict[str, Any]] = self._load_index()

    def _load_index(self) -> List[Dict[str, Any]]:
        if self.index_file.exists():
            try:
                return json.loads(self.index_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return []

    def _save_index(self) -> None:
        self.index_file.write_text(json.dumps(self._index, indent=2), encoding="utf-8")

    def register(self, artifact: Artifact) -> None:
        entry = {
            "name": artifact.name,
            "version": artifact.version,
            "path": artifact.path,
            "checksum": artifact.checksum,
            "size": artifact.size,
            "created_at": artifact.created_at,
            "metadata": artifact.metadata,
        }
        self._index.append(entry)
        self._save_index()

    def list_artifacts(self, version: Optional[str] = None) -> List[Dict[str, Any]]:
        if version:
            return [a for a in self._index if a["version"] == version]
        return list(self._index)

    def get_artifact(self, name: str) -> Optional[Dict[str, Any]]:
        for a in reversed(self._index):
            if a["name"] == name:
                return a
        return None

    def apply_retention(self, max_count: int = 10, max_age_days: int = 30) -> None:
        cutoff = time.time() - (max_age_days * 86400)
        to_remove: List[Dict[str, Any]] = []
        # Sort by created_at desc
        sorted_index = sorted(self._index, key=lambda x: x["created_at"], reverse=True)
        kept = sorted_index[:max_count]
        removed = sorted_index[max_count:]
        for a in removed:
            if a["created_at"] < cutoff:
                to_remove.append(a)
                path = pathlib.Path(a["path"])
                if path.exists():
                    path.unlink()
                checksum_path = path.parent / f"{path.name}.sha256"
                if checksum_path.exists():
                    checksum_path.unlink()

        self._index = [a for a in self._index if a not in to_remove]
        self._save_index()

    def run(self, ctx: PipelineContext) -> None:
        ctx.log("ArtifactRegistry: registering artifacts...")
        for artifact in ctx.artifacts:
            self.register(artifact)
            ctx.log(f"ArtifactRegistry: registered {artifact.name}")
        ctx.log("ArtifactRegistry: applying retention policy...")
        self.apply_retention(max_count=10, max_age_days=30)
        ctx.log("ArtifactRegistry: retention applied")
        ctx.set("registry_count", len(self._index))


# ---------------------------------------------------------------------------
# 7. Dashboard Integration — Status Hook
# ---------------------------------------------------------------------------


class DashboardIntegration:
    """Pushes pipeline status to the web dashboard server."""

    def __init__(self, hook_url: str = DASHBOARD_HOOK_URL) -> None:
        self.hook_url = hook_url

    def push_status(self, ctx: PipelineContext) -> bool:
        payload = {
            "build_id": ctx.build_id,
            "status": {k: v.value for k, v in ctx.status.items()},
            "summary": {
                "modules": ctx.get("total_modules", 0),
                "changed": len(ctx.get("changed_modules", [])),
                "tests_passed": ctx.get("test_passed", 0),
                "tests_failed": ctx.get("test_failed", 0),
                "version": ctx.get("new_version", "unknown"),
                "artifacts": len(ctx.artifacts),
            },
            "logs": ctx.logs[-50:],
            "timestamp": time.time(),
        }
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.hook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception as e:
            ctx.log(f"DashboardIntegration: push failed — {e}")
            return False

    def run(self, ctx: PipelineContext) -> None:
        ctx.log("DashboardIntegration: pushing status to dashboard...")
        ok = self.push_status(ctx)
        ctx.set("dashboard_pushed", ok)
        ctx.log(f"DashboardIntegration: push {'OK' if ok else 'FAILED'}")


# ---------------------------------------------------------------------------
# 8. Health Check — Post-Deploy Verification & Smoke Tests
# ---------------------------------------------------------------------------


class HealthCheck:
    """Verifies deployment health through smoke tests and module checks."""

    def __init__(self, base_dir: str = DEFAULT_BASE_DIR) -> None:
        self.base_dir = pathlib.Path(base_dir)

    def smoke_compile_all(self, ctx: PipelineContext) -> Tuple[List[str], List[str]]:
        passed: List[str] = []
        failed: List[str] = []
        for mod in ctx.modules:
            try:
                py_compile.compile(mod.path, doraise=True)
                passed.append(mod.name)
            except Exception:
                failed.append(mod.name)
        return passed, failed

    def smoke_import_check(self, ctx: PipelineContext) -> Tuple[List[str], List[str]]:
        passed: List[str] = []
        failed: List[str] = []
        for mod in ctx.modules[:20]:  # Limit for speed
            try:
                spec = importlib.util.spec_from_file_location(mod.name, mod.path)
                if spec and spec.loader:
                    mod_obj = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod_obj)
                    passed.append(mod.name)
            except Exception as e:
                failed.append(f"{mod.name}: {e}")
        return passed, failed

    def verify_deployment(self, ctx: PipelineContext) -> bool:
        ctx.log("HealthCheck: running smoke tests...")
        c_passed, c_failed = self.smoke_compile_all(ctx)
        i_passed, i_failed = self.smoke_import_check(ctx)
        healthy = len(c_failed) == 0 and len(i_failed) == 0
        ctx.set("health_compile_passed", c_passed)
        ctx.set("health_compile_failed", c_failed)
        ctx.set("health_import_passed", i_passed)
        ctx.set("health_import_failed", i_failed)
        ctx.set("deployment_healthy", healthy)
        ctx.log(f"HealthCheck: compile {len(c_passed)}/{len(c_passed)+len(c_failed)} OK, import {len(i_passed)}/{len(i_passed)+len(i_failed)} OK")
        if not healthy:
            for f in c_failed + i_failed:
                ctx.log(f"HealthCheck: SMOKE FAIL — {f}")
        return healthy

    def run(self, ctx: PipelineContext) -> None:
        healthy = self.verify_deployment(ctx)
        ctx.log(f"HealthCheck: deployment {'HEALTHY' if healthy else 'UNHEALTHY'}")


# ---------------------------------------------------------------------------
# Master Engine — CICDPipelineEngine
# ---------------------------------------------------------------------------


class CICDPipelineEngine:
    """Master orchestrator combining all 8 subsystems into a single pipeline."""

    def __init__(self, base_dir: str = DEFAULT_BASE_DIR) -> None:
        self.base_dir = base_dir
        self.builder = BuildAutomation(base_dir)
        self.tester = TestRunner(base_dir)
        self.packager = ReleasePackager(base_dir)
        self.deployer = AutoDeploy(base_dir)
        self.orchestrator = PipelineOrchestrator()
        self.registry = ArtifactRegistry()
        self.dashboard = DashboardIntegration()
        self.health = HealthCheck(base_dir)
        self._build_pipeline()

    def _build_pipeline(self) -> None:
        # Stage 1: Build
        self.orchestrator.add_stage(PipelineStage(
            name="build",
            steps=(self.builder.run,),
            timeout=120.0,
        ))

        # Stage 2: Test (only if build passed)
        self.orchestrator.add_stage(PipelineStage(
            name="test",
            condition=lambda ctx: ctx.status.get("build") == BuildStatus.SUCCESS,
            steps=(lambda ctx: self.tester.run(ctx, sequential=False),),
            timeout=300.0,
        ))

        # Stage 3: Security Scan (stub — always passes for now)
        self.orchestrator.add_stage(PipelineStage(
            name="security-scan",
            condition=lambda ctx: ctx.status.get("test") == BuildStatus.SUCCESS,
            steps=(self._security_scan,),
            timeout=60.0,
        ))

        # Stage 4: Package
        self.orchestrator.add_stage(PipelineStage(
            name="package",
            condition=lambda ctx: ctx.status.get("security-scan") == BuildStatus.SUCCESS,
            steps=(self.packager.run,),
            timeout=120.0,
        ))

        # Stage 5: Deploy
        self.orchestrator.add_stage(PipelineStage(
            name="deploy",
            condition=lambda ctx: ctx.status.get("package") == BuildStatus.SUCCESS,
            steps=(self._deploy_step,),
            timeout=120.0,
        ))

        # Stage 6: Registry
        self.orchestrator.add_stage(PipelineStage(
            name="registry-update",
            condition=lambda ctx: ctx.status.get("package") == BuildStatus.SUCCESS,
            steps=(self.registry.run,),
            timeout=60.0,
            allow_failure=True,
        ))

        # Stage 7: Dashboard
        self.orchestrator.add_stage(PipelineStage(
            name="dashboard-push",
            steps=(self.dashboard.run,),
            timeout=30.0,
            allow_failure=True,
        ))

        # Stage 8: Health Check
        self.orchestrator.add_stage(PipelineStage(
            name="health-check",
            condition=lambda ctx: ctx.status.get("deploy") == BuildStatus.SUCCESS,
            steps=(self.health.run,),
            timeout=120.0,
        ))

    def _security_scan(self, ctx: PipelineContext) -> None:
        ctx.log("SecurityScan: scanning for secrets and unsafe patterns...")
        issues = 0
        dangerous = ["eval(", "exec(", "subprocess.call", "os.system", "input("]
        for mod in ctx.modules:
            try:
                src = pathlib.Path(mod.path).read_text(encoding="utf-8")
                for d in dangerous:
                    if d in src:
                        issues += 1
                        ctx.log(f"SecurityScan: WARNING {mod.name} contains '{d}'")
            except Exception:
                pass
        ctx.set("security_issues", issues)
        ctx.log(f"SecurityScan: {issues} potential issues found")

    def _deploy_step(self, ctx: PipelineContext) -> None:
        strategy = ctx.get("deploy_strategy", "blue_green")
        deploy_strategy = DeployStrategy(strategy)
        self.deployer.run(ctx, deploy_strategy)

    def create_build(self, deploy_strategy: str = "blue_green") -> PipelineContext:
        build_id = f"build-{time.strftime('%Y%m%d-%H%M%S')}-{os.urandom(2).hex()}"
        ctx = PipelineContext(
            build_id=build_id,
            start_time=time.time(),
            base_dir=self.base_dir,
            target_dir=self.base_dir,
        )
        ctx.set("deploy_strategy", deploy_strategy)
        ctx.log(f"CICDPipelineEngine: build {build_id} created")
        return ctx

    def run(self, ctx: PipelineContext) -> PipelineContext:
        ctx.log("CICDPipelineEngine: pipeline starting...")
        self.orchestrator.run(ctx)
        elapsed = time.time() - ctx.start_time
        ctx.set("elapsed_seconds", round(elapsed, 2))
        ctx.log(f"CICDPipelineEngine: pipeline finished in {elapsed:.2f}s")
        return ctx

    def generate_report(self, ctx: PipelineContext) -> str:
        lines = [
            f"# CI/CD Pipeline Report — {ctx.build_id}",
            "",
            f"**Duration:** {ctx.get('elapsed_seconds', 0):.2f}s  ",
            f"**Version:** {ctx.get('new_version', 'N/A')}  ",
            f"**Modules:** {ctx.get('total_modules', 0)}  ",
            f"**Tests:** {ctx.get('test_passed', 0)} passed, {ctx.get('test_failed', 0)} failed  ",
            f"**Coverage:** {ctx.get('test_coverage_avg', 0):.1f}%  ",
            f"**Security Issues:** {ctx.get('security_issues', 0)}  ",
            f"**Cycles:** {len(ctx.get('cycles', []))}  ",
            f"**Deployment Healthy:** {ctx.get('deployment_healthy', False)}  ",
            "",
            "## Pipeline Stages",
            "",
            "| Stage | Status |",
            "|-------|--------|",
        ]
        for stage_name, status in ctx.status.items():
            icon = "✅" if status == BuildStatus.SUCCESS else "❌" if status == BuildStatus.FAILED else "⏭️"
            lines.append(f"| {stage_name} | {icon} {status.value} |")

        lines += [
            "",
            "## Build Order (Top 20)",
            "",
        ]
        for mod in ctx.build_order[:20]:
            lines.append(f"- {mod}")
        if len(ctx.build_order) > 20:
            lines.append(f"- ... and {len(ctx.build_order) - 20} more")

        lines += [
            "",
            "## Artifacts",
            "",
        ]
        for art in ctx.artifacts:
            lines.append(f"- `{art.name}` — {art.size} bytes, SHA256 `{art.checksum[:16]}...`")

        lines += [
            "",
            "## Recent Logs",
            "",
            "```",
        ]
        for log in ctx.logs[-20:]:
            lines.append(log)
        lines.append("```")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Self-Contained Demo / Mock Pipeline Run
# ---------------------------------------------------------------------------


def demo_mock_pipeline() -> None:
    """Runs a full mock pipeline with synthetic data to demonstrate all features."""
    print("=" * 70)
    print("CICD Pipeline Native — Self-Contained Demo")
    print("=" * 70)

    # Create a temporary project structure for demo
    demo_dir = pathlib.Path(tempfile.mkdtemp(prefix="magnatrix_demo_"))
    core_dir = demo_dir / "core"
    core_dir.mkdir()
    ai_dir = demo_dir / "ai"
    ai_dir.mkdir()
    test_dir = demo_dir / "tests"
    test_dir.mkdir()

    # Write mock modules with dependencies
    (core_dir / "config_manager_native.py").write_text("""
class ConfigManagerNative:
    def run(self): return True
""", encoding="utf-8")

    (core_dir / "integration_hub_native.py").write_text("""
import core.config_manager_native as config
class IntegrationHubNative:
    def run(self): return True
""", encoding="utf-8")

    (ai_dir / "llm_model_serving_native.py").write_text("""
import core.config_manager_native
import core.integration_hub_native
class LLMModelServingNative:
    def run(self): return True
""", encoding="utf-8")

    # Write a test file
    (test_dir / "test_core.py").write_text("""
def test_config():
    assert True
def test_integration():
    assert True
""", encoding="utf-8")

    # Write VERSION
    (demo_dir / "VERSION").write_text("0.1.0\n", encoding="utf-8")

    # Run pipeline
    engine = CICDPipelineEngine(str(demo_dir))
    ctx = engine.create_build(deploy_strategy="hot_reload")
    ctx = engine.run(ctx)

    # Report
    print()
    print(engine.generate_report(ctx))
    print()
    print("=" * 70)
    print(f"Demo complete. Build ID: {ctx.build_id}")
    print(f"Pipeline status: { {k: v.value for k, v in ctx.status.items()} }")
    print("=" * 70)

    # Cleanup
    shutil.rmtree(demo_dir)


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------


def run() -> None:
    """Main entry point for MAGNATRIX-OS CI/CD Pipeline."""
    # Check if running on real MAGNATRIX-OS or demo mode
    if os.path.isdir(DEFAULT_BASE_DIR):
        print("Running on MAGNATRIX-OS production...")
        engine = CICDPipelineEngine()
        ctx = engine.create_build(deploy_strategy="blue_green")
        ctx = engine.run(ctx)
        report = engine.generate_report(ctx)
        print(report)
        # Save report
        log_path = pathlib.Path(LOG_DIR)
        log_path.mkdir(parents=True, exist_ok=True)
        (log_path / f"{ctx.build_id}.md").write_text(report, encoding="utf-8")
    else:
        demo_mock_pipeline()


if __name__ == "__main__":
    run()
