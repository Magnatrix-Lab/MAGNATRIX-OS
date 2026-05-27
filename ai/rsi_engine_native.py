#!/usr/bin/env python3
"""RSI Engine — MAGNATRIX-OS ASI Expansion
Path: ai/rsi_engine_native.py
License: AGPL-3.0
Depends: Python 3.11+ stdlib only.

Recursive Self-Improvement: propose code patches, evaluate against benchmark,
keep best, rollback on regression. No internet access. All ops inside repo.
"""

from __future__ import annotations
import ast, hashlib, logging, os, random, sys, tempfile, time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

@dataclass
class Patch:
    target_file: str; line_start: int; line_end: int; replacement: str; patch_id: str

@dataclass
class BenchmarkResult:
    patch_id: str; score: float; latency: float; tests_passed: int; tests_total: int

class RSIEngine:
    """Propose, evaluate, and apply self-modifications."""

    def __init__(self, repo_path: str):
        self.repo = Path(repo_path)
        self.history: List[Tuple[Patch, BenchmarkResult]] = []
        self.best_score = 0.0
        self._backup: Dict[str, str] = {}

    def _backup_file(self, path: Path) -> None:
        if str(path) not in self._backup:
            self._backup[str(path)] = path.read_text()

    def _restore_file(self, path: Path) -> None:
        if str(path) in self._backup:
            path.write_text(self._backup[str(path)])

    def propose_patch(self, target: str, mutation_type: str = "random") -> Patch:
        """Generate a code patch via simple mutation."""
        path = self.repo / target
        if not path.exists():
            return Patch(target, 0, 0, "", "null")
        lines = path.read_text().split("\n")
        if len(lines) < 3:
            return Patch(target, 0, 0, "", "null")
        # Simple mutation: replace a numeric constant
        idx = random.randint(0, len(lines) - 1)
        original = lines[idx]
        mutated = original
        for digit in "0123456789":
            if digit in mutated:
                mutated = mutated.replace(digit, str((int(digit) + 1) % 10), 1)
                break
        pid = hashlib.sha256(f"{target}:{idx}:{time.time()}".encode()).hexdigest()[:8]
        return Patch(target, idx, idx + 1, mutated, pid)

    def apply_patch(self, patch: Patch) -> bool:
        path = self.repo / patch.target_file
        if not path.exists(): return False
        self._backup_file(path)
        lines = path.read_text().split("\n")
        if patch.line_start >= len(lines): return False
        lines[patch.line_start:patch.line_end] = patch.replacement.split("\n")
        path.write_text("\n".join(lines))
        return True

    def rollback(self, patch: Patch) -> None:
        path = self.repo / patch.target_file
        self._restore_file(path)

    def evaluate(self, patch: Patch, test_fn: Callable[[], Tuple[int, int, float]]) -> BenchmarkResult:
        """Run benchmark. Returns (tests_passed, tests_total, score)."""
        ok = self.apply_patch(patch)
        if not ok:
            return BenchmarkResult(patch.patch_id, 0.0, 0.0, 0, 0)
        start = time.time()
        try:
            passed, total, score = test_fn()
        except Exception as e:
            passed, total, score = 0, 0, 0.0
            logging.warning(f"Benchmark error: {e}")
        latency = time.time() - start
        if score < self.best_score:
            self.rollback(patch)
        else:
            self.best_score = score
            self.history.append((patch, BenchmarkResult(patch.patch_id, score, latency, passed, total)))
        return BenchmarkResult(patch.patch_id, score, latency, passed, total)

    def improve(self, target: str, iterations: int = 10, test_fn: Optional[Callable] = None) -> List[BenchmarkResult]:
        results = []
        for i in range(iterations):
            patch = self.propose_patch(target)
            if test_fn:
                r = self.evaluate(patch, test_fn)
                results.append(r)
        return results

def _self_test():
    print("=" * 55)
    print("RSI Engine — Self Test")
    print("=" * 55)
    passed, total = 0, 5

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        (repo / "test.py").write_text("x = 5\ny = 10\nresult = x + y\n")
        rsi = RSIEngine(tmp)

        patch = rsi.propose_patch("test.py")
        ok = patch.patch_id != "null"
        print(f"  [Test 1] Patch proposed: {ok} — {'PASS' if ok else 'FAIL'}")
        passed += ok

        ok = rsi.apply_patch(patch)
        print(f"  [Test 2] Patch applied: {ok} — {'PASS' if ok else 'FAIL'}")
        passed += ok

        content = (repo / "test.py").read_text()
        ok = content != "x = 5\ny = 10\nresult = x + y\n"
        print(f"  [Test 3] File changed: {ok} — {'PASS' if ok else 'FAIL'}")
        passed += ok

        rsi.rollback(patch)
        content2 = (repo / "test.py").read_text()
        ok = content2 == "x = 5\ny = 10\nresult = x + y\n"
        print(f"  [Test 4] Rollback works: {ok} — {'PASS' if ok else 'FAIL'}")
        passed += ok

        def dummy_test():
            return (3, 3, 1.0)
        r = rsi.evaluate(patch, dummy_test)
        ok = r.tests_passed == 3
        print(f"  [Test 5] Benchmark: {r.tests_passed}/{r.tests_total} — {'PASS' if ok else 'FAIL'}")
        passed += ok

    print("=" * 55)
    print(f"PASS: {passed}/{total} tests")
    print("=" * 55)
    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    _self_test()
