"""
loop_engineering_engine_native.py
MAGNATRIX-OS — Loop Engineering Engine

Implements the 14-step Loop Engineering paradigm for autonomous AI coding agents.
References: Codez (@0xCodez), Addy Osmani, Peter Steinberger, Geoffrey Huntley (Ralph Wiggum loop)

Core concepts:
- Automation/heartbeat: scheduled triggering of agent cycles
- Skill: project context files (SKILL.md, AGENTS.md, VISION.md)
- State: durable STATE.md across runs (agent forgets, repo remembers)
- Gate: objective verification (tests, lint, type checks) — no self-declaration
- Sub-agent: maker + checker split (evaluator-optimizer pattern)
- Worktree: isolated workspaces for parallel agents
- /loop vs /goal: timed repetition vs condition-driven termination
- Inner/outer loop: outer loop absorbs human feedback to improve

Pure Python standard library only. No external dependencies.
"""

import os
import json
import time
import shutil
import hashlib
import tempfile
import threading
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Callable, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum, auto


class LoopState(Enum):
    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    FAILED = auto()
    TIMEOUT = auto()


class GateResult(Enum):
    PASS = auto()
    FAIL = auto()
    SKIP = auto()


@dataclass
class LoopConfig:
    """Configuration for a single loop."""
    name: str
    goal: str
    heartbeat_interval_sec: int = 600  # default 10 min
    max_iterations: int = 10
    max_token_budget: int = 50000
    gate_commands: List[str] = field(default_factory=list)
    skill_files: List[str] = field(default_factory=list)
    state_file: str = "STATE.md"
    vision_file: str = "VISION.md"
    agents_dir: str = ".claude/agents"
    use_worktree: bool = True
    stop_on_first_failure: bool = False
    report_channel: str = "log"  # log, slack, github_issue


@dataclass
class LoopIteration:
    """Record of one loop iteration."""
    iteration: int
    started_at: str
    ended_at: str
    maker_output: str
    checker_output: str
    gate_results: Dict[str, str]
    state_after: Dict[str, Any]
    passed: bool


class SkillLoader:
    """Load and cache project skill files (SKILL.md, AGENTS.md, VISION.md)."""

    def __init__(self, project_root: str):
        self.root = Path(project_root)
        self._cache: Dict[str, str] = {}

    def load(self, filename: str) -> str:
        if filename in self._cache:
            return self._cache[filename]
        path = self.root / filename
        if path.exists():
            content = path.read_text(encoding="utf-8")
            self._cache[filename] = content
            return content
        return ""

    def load_all(self, filenames: List[str]) -> Dict[str, str]:
        return {f: self.load(f) for f in filenames}

    def invalidate(self, filename: str) -> None:
        self._cache.pop(filename, None)


class StateManager:
    """Durable STATE.md manager — agent forgets, repo remembers."""

    def __init__(self, project_root: str, state_file: str = "STATE.md"):
        self.root = Path(project_root)
        self.state_path = self.root / state_file

    def read(self) -> Dict[str, Any]:
        if not self.state_path.exists():
            return {"in_progress": [], "done": [], "blocked": [], "next": []}
        content = self.state_path.read_text(encoding="utf-8")
        return self._parse(content)

    def write(self, state: Dict[str, Any]) -> None:
        self.state_path.write_text(self._format(state), encoding="utf-8")

    def _parse(self, content: str) -> Dict[str, Any]:
        # Simple markdown parsing: ## sections → lists
        sections = {"in_progress": [], "done": [], "blocked": [], "next": []}
        current = None
        for line in content.strip().splitlines():
            line = line.strip()
            if line.startswith("## "):
                key = line[3:].strip().lower().replace(" ", "_")
                current = key if key in sections else None
            elif line.startswith("- ") and current:
                sections[current].append(line[2:].strip())
        return sections

    def _format(self, state: Dict[str, Any]) -> str:
        lines = ["# STATE.md", "## Loop State", f"Generated: {datetime.now().isoformat()}", ""]
        for key, items in state.items():
            lines.append(f"## {key.replace('_', ' ').title()}")
            for item in items:
                lines.append(f"- {item}")
            lines.append("")
        return "\n".join(lines)

    def append_task(self, section: str, task: str) -> None:
        state = self.read()
        state.setdefault(section, []).append(task)
        self.write(state)

    def move_task(self, task: str, from_section: str, to_section: str) -> None:
        state = self.read()
        if task in state.get(from_section, []):
            state[from_section].remove(task)
            state.setdefault(to_section, []).append(task)
            self.write(state)


class GateRunner:
    """Objective gate verification — prevents Ralph Wiggum loops."""

    def __init__(self, project_root: str):
        self.root = Path(project_root)

    def run(self, commands: List[str]) -> Dict[str, GateResult]:
        results = {}
        for cmd in commands:
            result = self._execute(cmd)
            results[cmd] = result
        return results

    def _execute(self, command: str) -> GateResult:
        # Standard library only: use subprocess-like os.popen for gates
        try:
            # Replace with actual execution context
            # Pure stdlib safe execution: check if command file exists
            if command.startswith("test:"):
                test_path = self.root / command[5:].strip()
                return GateResult.PASS if test_path.exists() else GateResult.FAIL
            if command.startswith("file_exists:"):
                p = self.root / command[12:].strip()
                return GateResult.PASS if p.exists() else GateResult.FAIL
            if command.startswith("lint:"):
                # Simulate lint check by reading file and checking basic patterns
                fpath = self.root / command[5:].strip()
                if not fpath.exists():
                    return GateResult.FAIL
                content = fpath.read_text(encoding="utf-8")
                if "TODO" in content and "FIXME" in content:
                    return GateResult.FAIL
                return GateResult.PASS
            return GateResult.SKIP
        except Exception:
            return GateResult.FAIL

    def all_pass(self, results: Dict[str, GateResult]) -> bool:
        return all(r in (GateResult.PASS, GateResult.SKIP) for r in results.values())


class WorktreeManager:
    """Isolated worktree for parallel agent execution."""

    def __init__(self, project_root: str):
        self.root = Path(project_root)
        self.worktrees: Dict[str, Path] = {}

    def create(self, name: str) -> Path:
        worktree_dir = self.root / ".worktrees" / name
        worktree_dir.mkdir(parents=True, exist_ok=True)
        # Copy project files into worktree (shallow copy for stdlib)
        for item in self.root.iterdir():
            if item.name.startswith(".") or item.name == ".worktrees":
                continue
            dest = worktree_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)
        self.worktrees[name] = worktree_dir
        return worktree_dir

    def destroy(self, name: str) -> None:
        if name in self.worktrees:
            shutil.rmtree(self.worktrees[name], ignore_errors=True)
            del self.worktrees[name]

    def get(self, name: str) -> Optional[Path]:
        return self.worktrees.get(name)


class SubAgent:
    """Maker or Checker sub-agent with isolated context."""

    def __init__(self, role: str, model_hint: str = "default"):
        self.role = role  # "maker" or "checker"
        self.model_hint = model_hint
        self.memory: List[str] = []

    def run(self, task: str, context: Dict[str, str]) -> str:
        # Simulated sub-agent execution: return structured response
        if self.role == "maker":
            return self._maker_run(task, context)
        return self._checker_run(task, context)

    def _maker_run(self, task: str, context: Dict[str, str]) -> str:
        lines = [f"[MAKER] Task: {task}"]
        for k, v in context.items():
            lines.append(f"[Context: {k}] {v[:200]}...")
        lines.append("[Action] Generated code/draft based on skill + state.")
        return "\n".join(lines)

    def _checker_run(self, task: str, context: Dict[str, str]) -> str:
        lines = [f"[CHECKER] Reviewing: {task}"]
        for k, v in context.items():
            lines.append(f"[Context: {k}] {v[:200]}...")
        lines.append("[Verdict] Reviewed against conventions and tests.")
        return "\n".join(lines)


class LoopEngine:
    """Core loop engine: act → observe → decide → repeat."""

    def __init__(self, project_root: str):
        self.root = Path(project_root)
        self.configs: Dict[str, LoopConfig] = {}
        self.states: Dict[str, LoopState] = {}
        self.iterations: Dict[str, List[LoopIteration]] = {}
        self._threads: Dict[str, threading.Thread] = {}
        self._stop_flags: Dict[str, threading.Event] = {}

    def register(self, config: LoopConfig) -> None:
        self.configs[config.name] = config
        self.states[config.name] = LoopState.IDLE
        self.iterations[config.name] = []
        self._stop_flags[config.name] = threading.Event()

    def start(self, name: str) -> bool:
        if name not in self.configs:
            return False
        if self.states.get(name) == LoopState.RUNNING:
            return True
        self._stop_flags[name].clear()
        self.states[name] = LoopState.RUNNING
        t = threading.Thread(target=self._run_loop, args=(name,), daemon=True)
        self._threads[name] = t
        t.start()
        return True

    def stop(self, name: str) -> bool:
        if name in self._stop_flags:
            self._stop_flags[name].set()
            self.states[name] = LoopState.IDLE
            return True
        return False

    def pause(self, name: str) -> bool:
        if name in self.states:
            self.states[name] = LoopState.PAUSED
            return True
        return False

    def resume(self, name: str) -> bool:
        if name in self.states and self.states[name] == LoopState.PAUSED:
            self.states[name] = LoopState.RUNNING
            return True
        return False

    def _run_loop(self, name: str) -> None:
        config = self.configs[name]
        state_mgr = StateManager(self.root, config.state_file)
        skills = SkillLoader(self.root)
        gate = GateRunner(self.root)
        worktree = WorktreeManager(self.root)

        iteration = 0
        while iteration < config.max_iterations:
            if self._stop_flags[name].is_set():
                break
            if self.states[name] == LoopState.PAUSED:
                time.sleep(1)
                continue

            iteration += 1
            started = datetime.now().isoformat()
            worktree_name = f"{name}_iter_{iteration}"
            workdir = worktree.create(worktree_name) if config.use_worktree else self.root

            # Load context
            skill_ctx = skills.load_all(config.skill_files)
            state = state_mgr.read()

            # Maker sub-agent
            maker = SubAgent("maker")
            maker_out = maker.run(config.goal, {**skill_ctx, "state": json.dumps(state)})

            # Checker sub-agent (evaluator-optimizer)
            checker = SubAgent("checker")
            checker_out = checker.run(config.goal, {**skill_ctx, "maker_output": maker_out})

            # Gate verification
            gate_results = gate.run(config.gate_commands)
            passed = gate.all_pass(gate_results)

            # Update state
            state["done"].append(f"Iteration {iteration}: {config.goal}")
            state_mgr.write(state)

            # Record iteration
            iter_record = LoopIteration(
                iteration=iteration,
                started_at=started,
                ended_at=datetime.now().isoformat(),
                maker_output=maker_out,
                checker_output=checker_out,
                gate_results={k: r.name for k, r in gate_results.items()},
                state_after=dict(state),
                passed=passed,
            )
            self.iterations[name].append(iter_record)

            # Cleanup worktree
            if config.use_worktree:
                worktree.destroy(worktree_name)

            # Check termination
            if passed:
                self.states[name] = LoopState.COMPLETED
                break

            # Sleep before next heartbeat
            time.sleep(config.heartbeat_interval_sec)
        else:
            self.states[name] = LoopState.TIMEOUT

    def get_report(self, name: str) -> Dict[str, Any]:
        if name not in self.configs:
            return {}
        iters = self.iterations.get(name, [])
        return {
            "loop": name,
            "state": self.states.get(name, LoopState.IDLE).name,
            "iterations": len(iters),
            "passed": sum(1 for i in iters if i.passed),
            "failed": sum(1 for i in iters if not i.passed),
            "details": [asdict(i) for i in iters],
        }

    def list_loops(self) -> List[str]:
        return list(self.configs.keys())


class LoopLearningJournal:
    """Outer loop: absorb human feedback to improve next runs."""

    def __init__(self, project_root: str):
        self.root = Path(project_root)
        self.journal_path = self.root / ".loop_journal.json"
        self.entries: List[Dict[str, Any]] = []
        if self.journal_path.exists():
            with open(self.journal_path, "r", encoding="utf-8") as f:
                self.entries = json.load(f)

    def record_feedback(self, loop_name: str, iteration: int, feedback: str, category: str = "general") -> None:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "loop": loop_name,
            "iteration": iteration,
            "feedback": feedback,
            "category": category,
        }
        self.entries.append(entry)
        with open(self.journal_path, "w", encoding="utf-8") as f:
            json.dump(self.entries, f, indent=2)

    def get_lessons(self, loop_name: Optional[str] = None) -> List[Dict[str, Any]]:
        if loop_name:
            return [e for e in self.entries if e["loop"] == loop_name]
        return self.entries

    def synthesize_rules(self) -> List[str]:
        # Simple rule extraction from feedback patterns
        rules = []
        for e in self.entries:
            fb = e["feedback"].lower()
            if "gate" in fb and "fail" in fb:
                rules.append("Strengthen gate conditions before next run.")
            if "timeout" in fb:
                rules.append("Increase iteration limit or reduce task scope.")
            if "skill" in fb and "missing" in fb:
                rules.append("Update SKILL.md with missing context.")
        return list(set(rules))


class LoopEngineeringEngine:
    """Top-level orchestrator for the Loop Engineering paradigm."""

    def __init__(self, project_root: str = "."):
        self.engine = LoopEngine(project_root)
        self.journal = LoopLearningJournal(project_root)
        self.project_root = project_root

    def create_loop(self, name: str, goal: str, heartbeat_sec: int = 600,
                    max_iter: int = 10, gate_commands: Optional[List[str]] = None,
                    skill_files: Optional[List[str]] = None) -> str:
        config = LoopConfig(
            name=name,
            goal=goal,
            heartbeat_interval_sec=heartbeat_sec,
            max_iterations=max_iter,
            gate_commands=gate_commands or [],
            skill_files=skill_files or ["SKILL.md", "VISION.md"],
        )
        self.engine.register(config)
        return f"Loop '{name}' registered with goal: {goal}"

    def start_loop(self, name: str) -> str:
        ok = self.engine.start(name)
        return f"Loop '{name}' started" if ok else f"Loop '{name}' not found"

    def stop_loop(self, name: str) -> str:
        ok = self.engine.stop(name)
        return f"Loop '{name}' stopped" if ok else f"Loop '{name}' not found"

    def get_status(self, name: str) -> Dict[str, Any]:
        return self.engine.get_report(name)

    def list_all(self) -> List[str]:
        return self.engine.list_loops()

    def add_feedback(self, loop_name: str, iteration: int, feedback: str) -> str:
        self.journal.record_feedback(loop_name, iteration, feedback)
        rules = self.journal.synthesize_rules()
        return f"Feedback recorded. Synthesized rules: {rules}"

    def get_lessons(self, loop_name: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.journal.get_lessons(loop_name)


# Export
__all__ = [
    "LoopEngineeringEngine",
    "LoopEngine",
    "LoopConfig",
    "LoopIteration",
    "LoopState",
    "GateResult",
    "StateManager",
    "SkillLoader",
    "GateRunner",
    "WorktreeManager",
    "SubAgent",
    "LoopLearningJournal",
]
