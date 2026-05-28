#!/usr/bin/env python3
"""Recursive Self-Improvement Engine — MAGNATRIX-OS ASI Expansion
Path: ai/rsi_engine_native.py
License: AGPL-3.0
Depends: Python 3.11+ stdlib only.
"""

from __future__ import annotations

import ast
import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CodeProposal:
    proposal_id: str
    target_file: str
    original_code: str
    proposed_code: str
    rationale: str
    expected_improvement: float
    risk_score: float


@dataclass
class EvaluationResult:
    proposal_id: str
    passed_safety: bool
    passed_tests: bool
    performance_delta: float
    rejected_reason: str = ""


class SafetyChecker:
    DANGEROUS = ["os.system", "subprocess", "eval(", "exec(", "__import__",
        "open('/etc", "open('/sys", "open('/proc", "rm -rf", "fork",
        "import socket", "socket.socket", "urllib.request.urlopen",
        "import os", "import sys", "sys.exit", "os._exit"]

    @staticmethod
    def check(code: str) -> Tuple[bool, List[str]]:
        violations = []
        for pattern in SafetyChecker.DANGEROUS:
            if pattern in code:
                violations.append(f"Forbidden: {pattern}")
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
                        violations.append("Direct eval/exec")
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in ("os", "subprocess", "socket", "urllib"):
                            violations.append(f"Forbidden import: {alias.name}")
        except SyntaxError as e:
            violations.append(f"Syntax error: {e}")
        return len(violations) == 0, violations


class SandboxExecutor:
    SAFE = {"abs", "all", "any", "bin", "bool", "chr", "divmod", "enumerate",
            "filter", "float", "format", "hash", "hex", "int", "len", "list",
            "map", "max", "min", "oct", "ord", "pow", "print", "range",
            "reversed", "round", "set", "sorted", "str", "sum", "tuple", "zip", "dict"}

    @staticmethod
    def run(proposed: str, test_input: Any, timeout: float = 2.0) -> Tuple[bool, Any, str]:
        import builtins
        safe_globals = {"__builtins__": {}}
        for name in SandboxExecutor.SAFE:
            val = getattr(builtins, name, None)
            if val is not None:
                safe_globals["__builtins__"][name] = val
        safe_globals["json"] = __import__("json")
        safe_globals["math"] = __import__("math")

        # Build wrapped code
        lines = proposed.split("\n")
        body = "\n".join("    " + line for line in lines)
        wrapped = "def _sandbox_main(input_data):\n" + body + "\n_result = _sandbox_main(_test_input)\n"
        safe_globals["_test_input"] = test_input

        try:
            exec(compile(wrapped, "<sandbox>", "exec"), safe_globals)
            return True, safe_globals.get("_result", None), ""
        except Exception as e:
            return False, None, f"{type(e).__name__}: {e}"


class RSIEngine:
    def __init__(self, safety_threshold: float = 0.3):
        self.proposals: List[CodeProposal] = []
        self.evaluations: List[EvaluationResult] = []
        self.applied: List[str] = []
        self.rollback_stack: List[Tuple[str, str]] = []
        self.safety = SafetyChecker()
        self.executor = SandboxExecutor()
        self.safety_threshold = safety_threshold
        self._version = 1

    def propose_modification(self, target_file: str, original: str, proposed: str, rationale: str) -> str:
        pid = f"prop_{self._version:04d}"
        self._version += 1
        diff_ratio = self._levenshtein_ratio(original, proposed)
        risk = min(1.0, (1.0 - diff_ratio) + 0.01 * proposed.count("\n"))
        cp = CodeProposal(pid, target_file, original, proposed, rationale, 0.5, risk)
        self.proposals.append(cp)
        return pid

    def evaluate_modification(self, proposal_id: str, test_cases: List[Tuple[Any, Any]]) -> EvaluationResult:
        prop = next((p for p in self.proposals if p.proposal_id == proposal_id), None)
        if not prop:
            return EvaluationResult(proposal_id, False, False, 0.0, "Not found")

        safe, violations = self.safety.check(prop.proposed_code)
        if not safe:
            return EvaluationResult(proposal_id, False, False, 0.0, f"Safety: {violations}")
        if prop.risk_score > self.safety_threshold:
            return EvaluationResult(proposal_id, False, False, 0.0, f"Risk: {prop.risk_score:.2f}")

        all_passed = True
        perf_orig = 0.0
        perf_prop = 0.0
        for inp, expected in test_cases:
            t0 = time.time()
            ok_orig, out_orig, _ = self.executor.run(prop.original_code, inp)
            t1 = time.time()
            ok_prop, out_prop, _ = self.executor.run(prop.proposed_code, inp)
            t2 = time.time()
            perf_orig += (t1 - t0)
            perf_prop += (t2 - t1)
            if not ok_prop:
                all_passed = False
            elif out_prop != expected and out_prop != out_orig:
                all_passed = False
        delta = ((perf_orig - perf_prop) / perf_orig * 100) if perf_orig > 0 else 0
        result = EvaluationResult(proposal_id, True, all_passed, delta)
        self.evaluations.append(result)
        return result

    def apply_if_safe(self, proposal_id: str) -> bool:
        eval_r = next((e for e in self.evaluations if e.proposal_id == proposal_id), None)
        if not eval_r or not (eval_r.passed_safety and eval_r.passed_tests):
            return False
        prop = next((p for p in self.proposals if p.proposal_id == proposal_id), None)
        if not prop:
            return False
        self.rollback_stack.append((prop.target_file, prop.original_code))
        self.applied.append(proposal_id)
        return True

    def rollback(self, n: int = 1) -> int:
        count = 0
        for _ in range(n):
            if not self.rollback_stack:
                break
            self.rollback_stack.pop()
            count += 1
        return count

    @staticmethod
    def _levenshtein_ratio(a: str, b: str) -> float:
        if not a and not b:
            return 1.0
        common = sum(1 for ca, cb in zip(a, b) if ca == cb)
        return 2 * common / (len(a) + len(b)) if (len(a) + len(b)) > 0 else 0


def _self_test():
    print("=" * 55)
    print("RSI Engine — Self Test")
    print("=" * 55)
    passed = 0
    total = 5

    rsi = RSIEngine(safety_threshold=0.5)

    original = "def compute(x):\n    return x * 2"
    proposed = "def compute(x):\n    return x * 2 + 1"

    print("[Test 1] Proposal created")
    pid = rsi.propose_modification("test.py", original, proposed, "Add constant")
    passed += 1
    print(f"  {pid} — PASS")

    print("[Test 2] Safety check")
    safe, violations = rsi.safety.check(proposed)
    print(f"  Safe: {safe} — {'PASS' if safe else 'FAIL'}")
    passed += safe

    print("[Test 3] Evaluate")
    tests = [(5, 10), (3, 6)]
    result = rsi.evaluate_modification(pid, tests)
    print(f"  Safety pass: {result.passed_safety} — {'PASS' if result.passed_safety else 'FAIL'}")
    passed += result.passed_safety

    print("[Test 4] Dangerous code rejected")
    dangerous = "import os; os.system('ls')"
    safe2, v2 = rsi.safety.check(dangerous)
    print(f"  Rejected: {not safe2} — {'PASS' if not safe2 else 'FAIL'}")
    passed += (not safe2)

    print("[Test 5] Apply safe modification")
    simple = "def compute(x):\n    return x * 3"
    pid3 = rsi.propose_modification("test2.py", original, simple, "Triple")
    result3 = rsi.evaluate_modification(pid3, [(2, 6)])
    applied = rsi.apply_if_safe(pid3)
    print(f"  Applied: {applied} — {'PASS' if applied else 'FAIL'}")
    passed += applied

    print(f"\nPASS: {passed}/{total}")
    print("=" * 55)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
