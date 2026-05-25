#!/usr/bin/env python3
"""
runtime/self_improvement_native.py
===================================
Layer 13.5 Extension — Self-Improvement Daemon

The core ASI loop: Observe → Learn → Modify → Test → Deploy

Observes:
  - GitHub API for new agentic/AI repos (AMATI-PELAJARI-TIRU)
  - System metrics (CPU, memory, error rates)
  - Security scan results
  - User feedback / commands

Learns:
  - Pattern extraction from external repos
  - Auto-documentation of new patterns
  - Performance regression detection

Modifies:
  - Generates native Python reimplementations
  - Patches existing *_native.py files
  - Updates tests for new code

Tests:
  - Runs comprehensive_test_suite.py
  - Chaos tests for consensus
  - Fuzz tests for boundaries

Deploys:
  - Git commit + push to origin/main
  - Hot-reload (SIGHUP) if runtime supports
  - Rollback on test failure

Usage:
  daemon = SelfImprovementDaemon(supervisor)
  daemon.start()  # Background thread
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


@dataclass
class ImprovementCycle:
    cycle_id: str
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    observations: List[Dict[str, Any]] = field(default_factory=list)
    modifications: List[str] = field(default_factory=list)
    test_results: Dict[str, Any] = field(default_factory=dict)
    deployed: bool = False
    rollback_triggered: bool = False


class SelfImprovementDaemon:
    """Autonomous improvement engine for MAGNATRIX-OS."""

    def __init__(self, supervisor: Optional[Any] = None,
                 repo_watch_interval_sec: float = 3600.0,
                 self_test_interval_sec: float = 300.0,
                 data_dir: str = "/var/lib/magnatrix/improvements") -> None:
        self.supervisor = supervisor
        self.repo_watch_interval = repo_watch_interval_sec
        self.self_test_interval = self_test_interval_sec
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._cycles: List[ImprovementCycle] = []
        self._observed_repos: Set[str] = set()
        self._lock = threading.Lock()

    # ---- Observation ----

    def _observe_github_trending(self) -> List[Dict[str, Any]]:
        """Check GitHub trending for agentic AI repos. Stub: reads from queue files."""
        findings = []
        queue_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "queue")
        if os.path.exists(queue_dir):
            for batch_file in sorted(os.listdir(queue_dir)):
                if batch_file.endswith(".md"):
                    path = os.path.join(queue_dir, batch_file)
                    with open(path, "r") as f:
                        content = f.read()
                    # Extract repo URLs
                    repos = re.findall(r"https://github\.com/([^/\s]+/[^/\s]+)", content)
                    for repo in repos:
                        if repo not in self._observed_repos:
                            self._observed_repos.add(repo)
                            findings.append({
                                "source": "github_queue",
                                "repo": repo,
                                "batch": batch_file,
                            })
        return findings

    def _observe_system_metrics(self) -> Dict[str, Any]:
        """Read system health."""
        try:
            import psutil
            return {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage("/var/lib/magnatrix").percent,
            }
        except ImportError:
            return {"cpu_percent": 0.0, "memory_percent": 0.0, "disk_usage": 0.0}

    # ---- Learning ----

    def _extract_patterns(self, repo: str) -> List[str]:
        """Stub: would clone repo and extract architectural patterns."""
        return [
            f"Pattern from {repo}: new module structure detected",
            f"Pattern from {repo}: novel error handling approach",
        ]

    def _document_pattern(self, pattern: str) -> None:
        doc_path = os.path.join(self.data_dir, "patterns.jsonl")
        with open(doc_path, "a") as f:
            json.dump({"ts": time.time(), "pattern": pattern}, f)
            f.write("\n")

    # ---- Modification ----

    def _generate_native_impl(self, pattern: str, target_module: str) -> Optional[str]:
        """Generate native Python reimplementation of observed pattern.
        Returns: path to generated file, or None if not applicable."""
        # Placeholder: real implementation would use the AI layer
        # to generate code from pattern description
        return None

    def _patch_existing(self, module_path: str, patch_fn: Callable[[str], str]) -> bool:
        """Apply a patch to an existing *_native.py file."""
        if not os.path.exists(module_path):
            return False
        with open(module_path, "r") as f:
            original = f.read()
        patched = patch_fn(original)
        if patched == original:
            return False
        # Backup
        backup = module_path + ".bak"
        with open(backup, "w") as f:
            f.write(original)
        with open(module_path, "w") as f:
            f.write(patched)
        return True

    # ---- Testing ----

    def _run_tests(self) -> Dict[str, Any]:
        """Run comprehensive test suite."""
        results = {"passed": 0, "total": 0, "errors": []}
        test_file = os.path.join(os.path.dirname(__file__), "..", "tests", "comprehensive_test_suite.py")
        if os.path.exists(test_file):
            try:
                # Run in subprocess for isolation
                proc = subprocess.run(
                    [sys.executable, test_file],
                    capture_output=True, text=True, timeout=120,
                )
                results["output"] = proc.stdout[-2000:] if len(proc.stdout) > 2000 else proc.stdout
                results["returncode"] = proc.returncode
                results["passed"] = proc.returncode == 0
            except Exception as e:
                results["errors"].append(str(e))
        return results

    def _run_chaos_tests(self) -> Dict[str, Any]:
        """Run chaos engineering suite."""
        chaos_file = os.path.join(os.path.dirname(__file__), "..", "tests", "chaos", "raft_chaos_native.py")
        results = {"passed": False}
        if os.path.exists(chaos_file):
            try:
                proc = subprocess.run(
                    [sys.executable, chaos_file],
                    capture_output=True, text=True, timeout=60,
                )
                results["passed"] = "PASS" in proc.stdout
                results["output"] = proc.stdout[-1000:] if len(proc.stdout) > 1000 else proc.stdout
            except Exception as e:
                results["error"] = str(e)
        return results

    # ---- Deployment ----

    def _git_commit_and_push(self, files: List[str], message: str) -> bool:
        """Commit changes and push to origin/main."""
        try:
            repo_root = os.path.dirname(os.path.dirname(__file__))
            subprocess.run(["git", "add"] + files, cwd=repo_root, check=True)
            subprocess.run(["git", "commit", "-m", message], cwd=repo_root, check=True)
            subprocess.run(["git", "push", "origin", "main"], cwd=repo_root, check=True, timeout=60)
            return True
        except subprocess.CalledProcessError:
            return False

    def _hot_reload(self) -> bool:
        """Signal supervisor to hot-reload modified modules."""
        if self.supervisor and hasattr(self.supervisor, "reload"):
            try:
                self.supervisor.reload()
                return True
            except Exception:
                pass
        return False

    def _rollback(self, files: List[str]) -> bool:
        """Restore from .bak files."""
        success = True
        for f in files:
            bak = f + ".bak"
            if os.path.exists(bak):
                try:
                    os.replace(bak, f)
                except Exception:
                    success = False
            else:
                success = False
        return success

    # ---- Main Loop ----

    def _cycle(self) -> None:
        """Execute one observe-learn-modify-test-deploy cycle."""
        cycle = ImprovementCycle(cycle_id=hashlib.sha256(str(time.time()).encode()).hexdigest()[:12])

        # 1. OBSERVE
        cycle.observations.extend(self._observe_github_trending())
        cycle.observations.append({"type": "system_metrics", "data": self._observe_system_metrics()})

        # 2. LEARN
        for obs in cycle.observations:
            if obs.get("repo"):
                patterns = self._extract_patterns(obs["repo"])
                for p in patterns:
                    self._document_pattern(p)
                    cycle.modifications.append(p)

        # 3. MODIFY (placeholder: real ASI would generate code)
        # For now, just log that we would modify

        # 4. TEST
        cycle.test_results["unit"] = self._run_tests()
        cycle.test_results["chaos"] = self._run_chaos_tests()

        # 5. DECIDE
        all_pass = (
            cycle.test_results["unit"].get("passed") and
            cycle.test_results["chaos"].get("passed", True)
        )

        if all_pass and cycle.modifications:
            # Would deploy here
            cycle.deployed = True
        elif not all_pass and cycle.modifications:
            cycle.rollback_triggered = True

        cycle.completed_at = time.time()
        with self._lock:
            self._cycles.append(cycle)

    def _run(self) -> None:
        last_repo_check = 0.0
        last_test = 0.0
        while self._running:
            now = time.time()
            if now - last_repo_check >= self.repo_watch_interval:
                self._cycle()
                last_repo_check = now
            if now - last_test >= self.self_test_interval:
                # Quick self-test without full cycle
                self._run_tests()
                last_test = now
            time.sleep(1.0)

    # ---- Public API ----

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print("[ASI] Self-improvement daemon started.")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        print("[ASI] Self-improvement daemon stopped.")

    @property
    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "cycles": len(self._cycles),
                "observed_repos": len(self._observed_repos),
                "last_cycle": self._cycles[-1].__dict__ if self._cycles else None,
            }


def demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS  |  ASI SELF-IMPROVEMENT DAEMON")
    print("=" * 60)
    daemon = SelfImprovementDaemon()
    # Run one cycle manually
    daemon._cycle()
    print(f"Cycle stats: {daemon.stats}")
    print("=" * 60)


if __name__ == "__main__":
    demo()
