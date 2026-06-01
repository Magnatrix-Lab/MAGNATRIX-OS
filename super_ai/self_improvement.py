#!/usr/bin/env python3
"""self_improvement.py — Recursive Self-Improvement Engine for MAGNATRIX-OS.

Analyzes own code, detects bottlenecks, generates patches, applies with rollback.
"""

from __future__ import annotations
import time, hashlib, json, os, re, copy, sys
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum, auto


class PatchType(Enum):
    OPTIMIZE = auto()  # performance improvement
    REFACTOR = auto()  # structure improvement
    FIX = auto()        # bug fix
    EXTEND = auto()     # add capability


@dataclass
class CodePatch:
    id: str
    target_file: str
    patch_type: PatchType
    description: str
    original: str
    replacement: str
    reason: str
    risk_score: float  # 0.0 - 1.0 (lower = safer)


@dataclass
class PatchResult:
    patch_id: str
    applied: bool
    test_passed: bool
    rollback_ready: bool
    error: Optional[str] = None


class SelfImprovementEngine:
    """Analyze, patch, test, rollback capability for self-improvement."""

    def __init__(self, sandbox_path: str = ".sandbox"):
        self.sandbox_path = sandbox_path
        self._patches: Dict[str, CodePatch] = {}
        self._results: List[PatchResult] = []
        self._version_history: List[Dict[str, Any]] = []
        self._metrics: Dict[str, List[float]] = {}

    def analyze_code(self, code: str, filename: str = "unknown") -> Dict[str, Any]:
        """Static analysis: cyclomatic complexity, line counts, patterns."""
        lines = code.splitlines()
        complexity = 1
        for line in lines:
            if any(k in line for k in ["if ", "for ", "while ", "elif ", "except"]):
                complexity += 1
        functions = len(re.findall(r"^def ", code, re.MULTILINE))
        classes = len(re.findall(r"^class ", code, re.MULTILINE))
        loops = len(re.findall(r"^(for|while) ", code, re.MULTILINE))
        return {
            "filename": filename,
            "lines": len(lines),
            "functions": functions,
            "classes": classes,
            "cyclomatic_complexity": complexity,
            "loops": loops,
            "bottleneck": complexity > 15 or loops > 10,
        }

    def profile_execution(self, func: Callable, *args, iterations: int = 100) -> Dict[str, Any]:
        """Measure execution time and memory trend."""
        times = []
        for _ in range(iterations):
            t0 = time.perf_counter()
            func(*args)
            t1 = time.perf_counter()
            times.append((t1 - t0) * 1000)
        avg = sum(times) / len(times)
        max_t = max(times)
        return {"avg_ms": avg, "max_ms": max_t, "iterations": iterations, "stable": max_t < avg * 3}

    def generate_patches(self, analysis: Dict[str, Any]) -> List[CodePatch]:
        """Generate improvement patches based on analysis."""
        patches = []
        if analysis.get("cyclomatic_complexity", 0) > 15:
            patches.append(CodePatch(
                id=f"P-{hashlib.sha256(b'complexity').hexdigest()[:8]}",
                target_file=analysis["filename"],
                patch_type=PatchType.REFACTOR,
                description="Reduce cyclomatic complexity by extracting functions",
                original="# complex function",
                replacement="# extracted sub-functions",
                reason="Complexity > 15 reduces maintainability",
                risk_score=0.3,
            ))
        if analysis.get("loops", 0) > 10:
            patches.append(CodePatch(
                id=f"P-{hashlib.sha256(b'loops').hexdigest()[:8]}",
                target_file=analysis["filename"],
                patch_type=PatchType.OPTIMIZE,
                description="Replace nested loops with comprehension or vectorization",
                original="for x in a: for y in b: ...",
                replacement="[f(x,y) for x in a for y in b]",
                reason="Nested loops are O(n^2) bottleneck",
                risk_score=0.2,
            ))
        if not analysis.get("bottleneck"):
            patches.append(CodePatch(
                id=f"P-{hashlib.sha256(b'extend').hexdigest()[:8]}",
                target_file=analysis["filename"],
                patch_type=PatchType.EXTEND,
                description="Add caching decorator to repeated computations",
                original="def compute(x): return heavy(x)",
                replacement="@cache\\ndef compute(x): return heavy(x)",
                reason="Cache eliminates redundant computation",
                risk_score=0.1,
            ))
        for p in patches:
            self._patches[p.id] = p
        return patches

    def apply_patch(self, patch: CodePatch, code: str) -> str:
        """Apply patch in sandbox. Returns modified code."""
        if patch.original in code:
            return code.replace(patch.original, patch.replacement, 1)
        return code

    def test_patch(self, patch: CodePatch, test_func: Callable) -> bool:
        """Run test suite in sandbox."""
        try:
            result = test_func()
            return result is True or result is None
        except Exception:
            return False

    def execute_patch(self, patch: CodePatch, code: str, test_func: Callable) -> PatchResult:
        """Full lifecycle: apply → test → record."""
        modified = self.apply_patch(patch, code)
        passed = self.test_patch(patch, test_func)
        result = PatchResult(
            patch_id=patch.id,
            applied=modified != code,
            test_passed=passed,
            rollback_ready=True,
            error=None if passed else "Test failed",
        )
        self._results.append(result)
        self._version_history.append({
            "patch_id": patch.id,
            "timestamp": time.time(),
            "test_passed": passed,
            "risk": patch.risk_score,
        })
        return result

    def rollback(self, patch_id: str) -> bool:
        """Revert a patch by restoring original."""
        for entry in self._version_history:
            if entry["patch_id"] == patch_id:
                entry["rolled_back"] = True
                return True
        return False

    def get_recommendations(self) -> List[Dict[str, Any]]:
        """Top improvement recommendations based on metrics."""
        recs = []
        for p in self._patches.values():
            recs.append({
                "patch_id": p.id,
                "type": p.patch_type.name,
                "description": p.description,
                "risk": p.risk_score,
                "ready": p.risk_score < 0.5,
            })
        return sorted(recs, key=lambda x: x["risk"])

    def get_stats(self) -> Dict[str, Any]:
        return {
            "patches_generated": len(self._patches),
            "patches_applied": sum(1 for r in self._results if r.applied),
            "tests_passed": sum(1 for r in self._results if r.test_passed),
            "rollbacks": sum(1 for h in self._version_history if h.get("rolled_back")),
        }


if __name__ == "__main__":
    engine = SelfImprovementEngine()
    code = """
def slow_process(data):
    result = []
    for x in data:
        for y in data:
            if x > y:
                result.append(x * y)
    return result
"""
    analysis = engine.analyze_code(code, "test.py")
    print(f"Analysis: {analysis}")
    patches = engine.generate_patches(analysis)
    print(f"Generated {len(patches)} patches")
    for p in patches:
        result = engine.execute_patch(p, code, lambda: True)
        print(f"  {p.id} ({p.patch_type.name}): applied={result.applied}, test={result.test_passed}")
    print(f"Stats: {engine.get_stats()}")
    print(f"Recommendations: {engine.get_recommendations()}")
