#!/usr/bin/env python3
"""
Test runner: discover all tests, run in order, generate report.
Pure Python stdlib + pytest.
"""

import os
import sys
import time
import json
import subprocess
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List

@dataclass
class TestResult:
    name: str
    passed: int
    failed: int
    skipped: int
    duration: float
    error: str = ""

class TestRunner:
    def __init__(self, root: Path):
        self.root = root
        self.results: List[TestResult] = []
        self.started = time.time()

    def discover(self) -> List[Path]:
        tests = []
        for p in sorted(self.root.rglob("test_*.py")):
            if p.name == "run_all_tests.py":
                continue
            tests.append(p)
        return tests

    def run_file(self, path: Path) -> TestResult:
        t0 = time.time()
        cmd = [sys.executable, "-m", "pytest", str(path), "-v", "--tb=short"]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.root,
            )
            out = proc.stdout + proc.stderr
            passed = out.count(" PASSED")
            failed = out.count(" FAILED")
            skipped = out.count(" SKIPPED")
            if proc.returncode != 0 and failed == 0:
                failed = 1
            return TestResult(
                name=path.name,
                passed=passed,
                failed=failed,
                skipped=skipped,
                duration=round(time.time() - t0, 3),
                error=out[-500:] if failed else "",
            )
        except subprocess.TimeoutExpired:
            return TestResult(path.name, 0, 1, 0, round(time.time() - t0, 3), "timeout")
        except Exception as e:
            return TestResult(path.name, 0, 1, 0, 0.0, str(e))

    def run(self):
        files = self.discover()
        if not files:
            print("No test files found.")
            return
        print(f"Discovered {len(files)} test file(s)\n")
        for f in files:
            print(f"Running {f.name} ...", flush=True)
            res = self.run_file(f)
            self.results.append(res)
            status = "✓" if res.failed == 0 else "✗"
            print(f"  {status} {res.passed} passed, {res.failed} failed, {res.skipped} skipped in {res.duration}s")
        print()

    def report(self):
        total = time.time() - self.started
        total_passed = sum(r.passed for r in self.results)
        total_failed = sum(r.failed for r in self.results)
        total_skipped = sum(r.skipped for r in self.results)
        print("=" * 50)
        print("TEST REPORT")
        print("=" * 50)
        for r in self.results:
            mark = "PASS" if r.failed == 0 else "FAIL"
            print(f"[{mark}] {r.name:40s} {r.duration:6.2f}s")
            if r.error:
                print(f"       {r.error[:200]}")
        print("-" * 50)
        print(f"Total: {total_passed} passed, {total_failed} failed, {total_skipped} skipped")
        print(f"Time:  {total:.2f}s")
        print("=" * 50)

        # JSON report
        report_path = self.root / "test_report.json"
        with open(report_path, "w") as f:
            json.dump({
                "total_time": round(total, 3),
                "passed": total_passed,
                "failed": total_failed,
                "skipped": total_skipped,
                "results": [asdict(r) for r in self.results],
            }, f, indent=2)
        print(f"JSON report saved to {report_path}")
        return 0 if total_failed == 0 else 1


def main():
    script_dir = Path(__file__).resolve().parent
    runner = TestRunner(script_dir)
    runner.run()
    sys.exit(runner.report())


if __name__ == "__main__":
    main()
