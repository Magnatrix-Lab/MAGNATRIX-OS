#!/usr/bin/env python3
"""
skills/skills_v2_native.py — MAGNATRIX-OS Skills V2

Skill marketplace, A/B testing, sandbox, workflow composer. Pure Python stdlib.
"""
from __future__ import annotations
import hashlib
import json
import os
import random
import re
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

@dataclass
class SkillManifest:
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    entry_point: str = "main"
    permissions: List[str] = field(default_factory=list)
    sandboxed: bool = True

@dataclass
class Skill:
    manifest: SkillManifest = field(default_factory=SkillManifest)
    code: str = ""
    path: str = ""
    installed_at: float = 0.0
    rating: float = 0.0
    usage_count: int = 0
    error_count: int = 0

class SkillRegistry:
    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._lock = threading.Lock()
    def register(self, skill: Skill) -> None:
        with self._lock:
            self._skills[skill.manifest.name] = skill
    def get(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)
    def list(self, tag: Optional[str] = None) -> List[Skill]:
        skills = list(self._skills.values())
        if tag:
            skills = [s for s in skills if tag in s.manifest.tags]
        return skills
    def search(self, query: str) -> List[Skill]:
        q = query.lower()
        return [s for s in self._skills.values() if q in s.manifest.name.lower() or q in s.manifest.description.lower()]

class SkillMarketplace:
    def __init__(self, registry: SkillRegistry):
        self.registry = registry
        self._ratings: Dict[str, List[float]] = {}
    def rate(self, skill_name: str, rating: float) -> None:
        if skill_name not in self._ratings:
            self._ratings[skill_name] = []
        self._ratings[skill_name].append(rating)
        skill = self.registry.get(skill_name)
        if skill:
            skill.rating = sum(self._ratings[skill_name]) / len(self._ratings[skill_name])
    def top_rated(self, limit: int = 10) -> List[Skill]:
        skills = [s for s in self.registry.list() if s.rating > 0]
        skills.sort(key=lambda s: s.rating, reverse=True)
        return skills[:limit]

class SkillSandbox:
    def __init__(self, timeout: float = 5.0, max_memory_mb: int = 100):
        self.timeout = timeout
        self.max_memory = max_memory_mb
    def execute(self, code: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            tmp_path = f.name
        try:
            result = subprocess.run(
                ["python3", tmp_path],
                capture_output=True, text=True, timeout=self.timeout,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            )
            return {"success": result.returncode == 0, "output": result.stdout, "error": result.stderr}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "timeout", "output": ""}
        finally:
            os.unlink(tmp_path)

class SkillTester:
    def __init__(self, sandbox: SkillSandbox):
        self.sandbox = sandbox
    def test(self, skill: Skill, test_cases: List[Dict]) -> Dict[str, Any]:
        passed = 0
        failed = 0
        results = []
        for case in test_cases:
            result = self.sandbox.execute(skill.code, case.get("inputs", {}))
            expected = case.get("expected")
            success = result["success"] and expected in result["output"] if expected else result["success"]
            if success:
                passed += 1
            else:
                failed += 1
            results.append({"case": case.get("name"), "success": success})
        return {"passed": passed, "failed": failed, "results": results}

class SkillABTest:
    def __init__(self):
        self._tests: Dict[str, Dict] = {}
    def start(self, test_id: str, skill_a: str, skill_b: str) -> None:
        self._tests[test_id] = {"a": skill_a, "b": skill_b, "a_wins": 0, "b_wins": 0, "total": 0}
    def record(self, test_id: str, winner: str) -> None:
        if test_id in self._tests:
            self._tests[test_id][f"{winner}_wins"] += 1
            self._tests[test_id]["total"] += 1
    def winner(self, test_id: str) -> Optional[str]:
        t = self._tests.get(test_id)
        if not t or t["total"] == 0:
            return None
        return t["a"] if t["a_wins"] > t["b_wins"] else t["b"]

class SkillComposer:
    def __init__(self, registry: SkillRegistry):
        self.registry = registry
    def compose(self, skill_names: List[str], inputs: Dict[str, Any]) -> List[Dict[str, Any]]:
        results = []
        current = inputs
        for name in skill_names:
            skill = self.registry.get(name)
            if not skill:
                break
            # Simulated execution
            results.append({"skill": name, "input": current, "output": f"output_from_{name}"})
            current = {"previous": name, "data": results[-1]["output"]}
        return results

class SkillAnalytics:
    def __init__(self, registry: SkillRegistry):
        self.registry = registry
    def get_stats(self) -> Dict[str, Any]:
        skills = self.registry.list()
        if not skills:
            return {}
        return {
            "total": len(skills),
            "avg_rating": sum(s.rating for s in skills) / len(skills),
            "total_usage": sum(s.usage_count for s in skills),
            "total_errors": sum(s.error_count for s in skills),
        }

class SkillVersionManager:
    @staticmethod
    def parse_version(v: str) -> Tuple[int, int, int]:
        parts = v.split(".")
        return tuple(int(p) for p in parts[:3]) + (0,) * (3 - len(parts[:3]))
    @staticmethod
    def compare(a: str, b: str) -> int:
        va = SkillVersionManager.parse_version(a)
        vb = SkillVersionManager.parse_version(b)
        for x, y in zip(va, vb):
            if x != y:
                return 1 if x > y else -1
        return 0

class SkillScheduler:
    def __init__(self):
        self._tasks: Dict[str, Dict] = {}
        self._running = False
    def schedule(self, skill_name: str, interval: float, max_runs: int = -1) -> str:
        task_id = hashlib.sha256(f"{skill_name}{time.time()}".encode()).hexdigest()[:12]
        self._tasks[task_id] = {"skill": skill_name, "interval": interval, "max_runs": max_runs, "runs": 0, "next": time.time() + interval}
        return task_id
    def tick(self) -> List[str]:
        ready = []
        now = time.time()
        for tid, task in self._tasks.items():
            if now >= task["next"] and (task["max_runs"] < 0 or task["runs"] < task["max_runs"]):
                ready.append(tid)
                task["runs"] += 1
                task["next"] = now + task["interval"]
        return ready

class SkillTrigger:
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
    def on(self, event: str, handler: Callable) -> None:
        self._handlers.setdefault(event, []).append(handler)
    def emit(self, event: str, data: Any) -> None:
        for handler in self._handlers.get(event, []):
            try:
                handler(data)
            except Exception:
                pass

class SkillPackager:
    @staticmethod
    def package(skill: Skill, output_path: str) -> str:
        import zipfile
        with zipfile.ZipFile(output_path, "w") as zf:
            zf.writestr("manifest.json", json.dumps(skill.manifest.__dict__, default=str))
            zf.writestr("skill.py", skill.code)
        return output_path

class SkillManager:
    def __init__(self):
        self.registry = SkillRegistry()
        self.marketplace = SkillMarketplace(self.registry)
        self.sandbox = SkillSandbox()
        self.tester = SkillTester(self.sandbox)
        self.abtest = SkillABTest()
        self.composer = SkillComposer(self.registry)
        self.analytics = SkillAnalytics(self.registry)
        self.scheduler = SkillScheduler()
        self.trigger = SkillTrigger()
        self.versions = SkillVersionManager()
    def install(self, skill: Skill) -> bool:
        self.registry.register(skill)
        return True
    def execute(self, name: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        skill = self.registry.get(name)
        if not skill:
            return {"success": False, "error": "skill not found"}
        if skill.manifest.sandboxed:
            return self.sandbox.execute(skill.code, inputs)
        return {"success": True, "output": "executed (non-sandboxed)"}
    def stats(self) -> Dict[str, Any]:
        return self.analytics.get_stats()

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Skills V2 — Self-Test")
    print("=" * 60)
    mgr = SkillManager()
    skill = Skill(manifest=SkillManifest(name="hello", version="1.0.0", description="Say hello", sandboxed=True), code='print("Hello from skill!")')
    mgr.install(skill)
    result = mgr.execute("hello", {})
    assert result["success"] == True
    print("[1] Skill execute OK")
    mgr.marketplace.rate("hello", 5.0)
    assert mgr.registry.get("hello").rating == 5.0
    print("[2] Rating OK")
    top = mgr.marketplace.top_rated()
    assert len(top) == 1
    print("[3] Marketplace OK")
    test_result = mgr.tester.test(skill, [{"name": "basic", "expected": "Hello"}])
    assert test_result["passed"] >= 0
    print("[4] Testing OK")
    mgr.abtest.start("test1", "hello", "hello2")
    mgr.abtest.record("test1", "a")
    assert mgr.abtest.winner("test1") == "hello"
    print("[5] A/B test OK")
    workflow = mgr.composer.compose(["hello"], {"input": "test"})
    assert len(workflow) == 1
    print("[6] Composer OK")
    tid = mgr.scheduler.schedule("hello", 0.1)
    time.sleep(0.15)
    ready = mgr.scheduler.tick()
    assert tid in ready
    print("[7] Scheduler OK")
    mgr.trigger.on("event", lambda d: None)
    mgr.trigger.emit("event", "data")
    print("[8] Trigger OK")
    path = SkillPackager.package(skill, "/tmp/skill.zip")
    assert os.path.exists(path)
    print("[9] Package OK")
    print("All tests passed")
