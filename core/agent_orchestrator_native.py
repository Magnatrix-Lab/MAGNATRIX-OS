#!/usr/bin/env python3
"""
AI Agent Orchestrator for MAGNATRIX-OS
The brain that makes the system autonomous — parse intent, plan tasks,
dispatch to 107 modules, execute with feedback, self-correct.
Pure stdlib — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import importlib
import json
import os
import re
import threading
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Set


@dataclass
class Task:
    """A single task in the execution plan."""
    id: str
    action: str
    target_module: str
    params: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    state: str = "pending"  # pending, running, success, failed, retry
    result: Any = None
    error: Optional[str] = None
    attempts: int = 0
    max_attempts: int = 3
    start_time: float = 0.0
    end_time: float = 0.0


@dataclass
class Plan:
    """Execution plan for a user intent."""
    intent: str
    confidence: float
    tasks: List[Task]
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Result of executing a plan."""
    success: bool
    completed_tasks: int
    failed_tasks: int
    outputs: List[Dict[str, Any]]
    execution_time_ms: float


class IntentParser:
    """Parse natural language intent into structured action."""

    KEYWORDS = {
        # Module management
        "start": ["start", "boot", "launch", "run", "initiate", "activate"],
        "stop": ["stop", "halt", "shutdown", "kill", "terminate", "disable"],
        "restart": ["restart", "reload", "reboot", "refresh"],
        "status": ["status", "health", "check", "state", "diagnose", "how is"],
        "list": ["list", "show", "display", "view", "enumerate"],
        # Document operations
        "upload": ["upload", "ingest", "add", "import", "load", "read"],
        "query": ["query", "ask", "search", "find", "lookup", "retrieve"],
        "chat": ["chat", "talk", "conversation", "message", "speak"],
        # System operations
        "backup": ["backup", "save", "snapshot", "archive"],
        "update": ["update", "upgrade", "refresh", "sync"],
        "config": ["config", "configure", "setting", "preference", "option"],
        "deploy": ["deploy", "install", "setup", "build", "release"],
        # Genesis operations
        "learn": ["learn", "study", "train", "improve", "adapt"],
        "create": ["create", "generate", "build", "make", "produce"],
        "distribute": ["distribute", "publish", "share", "send", "post"],
        "protect": ["protect", "guard", "secure", "shield", "audit"],
    }

    MODULE_MAP = {
        "start": ["web_dashboard", "event_bus", "config"],
        "stop": ["web_dashboard", "mesh"],
        "restart": ["web_dashboard", "event_bus"],
        "status": ["monitor", "health", "metrics"],
        "list": ["module"],
        "upload": ["doc_intel", "rag"],
        "query": ["doc_intel", "rag", "llm"],
        "chat": ["llm", "multi_model", "event_bus"],
        "backup": ["backup"],
        "update": ["deployment"],
        "config": ["config"],
        "deploy": ["deployment", "cicd"],
        "learn": ["learning", "memory", "knowledge_graph"],
        "create": ["content", "genesis_hub"],
        "distribute": ["distribution", "outreach"],
        "protect": ["guardian", "security", "prompt_guard"],
    }

    def parse(self, text: str) -> Dict[str, Any]:
        """Parse intent from user text."""
        text_lower = text.lower()
        detected_actions = []
        for action, keywords in self.KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    detected_actions.append(action)
                    break

        if not detected_actions:
            # Default to chat if no specific action detected
            detected_actions = ["chat"]

        primary = detected_actions[0]
        target_modules = self.MODULE_MAP.get(primary, ["llm"])

        # Extract parameters
        params = self._extract_params(text_lower, primary)

        return {
            "intent": text,
            "primary_action": primary,
            "all_actions": detected_actions,
            "target_modules": target_modules,
            "params": params,
            "confidence": self._calc_confidence(text_lower, primary),
        }

    def _extract_params(self, text: str, action: str) -> Dict[str, Any]:
        params = {}
        # Extract file paths
        if action in ("upload", "ingest"):
            for match in re.finditer(r"([\w\-./]+\.(?:txt|pdf|csv|json|md|py))", text):
                params.setdefault("files", []).append(match.group(1))
        # Extract module names
        if action in ("start", "stop", "restart"):
            # Look for module names after action keywords
            for action_kw in self.KEYWORDS.get(action, []):
                idx = text.find(action_kw)
                if idx != -1:
                    after = text[idx + len(action_kw):].strip()
                    words = after.split()[:3]
                    for w in words:
                        if w.isalnum() and len(w) > 2:
                            params["target"] = w
                            break
                    break
        # Extract config key-value pairs
        if action == "config":
            for match in re.finditer(r"([\w.]+)\s*[=:]\s*([^\s,]+)", text):
                params[match.group(1)] = match.group(2)
        return params

    def _calc_confidence(self, text: str, action: str) -> float:
        keywords = self.KEYWORDS.get(action, [])
        matches = sum(1 for kw in keywords if kw in text)
        return min(0.95, 0.5 + matches * 0.15)


class TaskPlanner:
    """Plan execution steps from parsed intent."""

    def __init__(self, registry: Any = None) -> None:
        self.registry = registry

    def plan(self, intent: Dict[str, Any]) -> Plan:
        """Create execution plan from intent."""
        action = intent["primary_action"]
        params = intent.get("params", {})
        target_modules = intent.get("target_modules", ["llm"])
        confidence = intent.get("confidence", 0.5)

        tasks = []
        task_id = 0

        # Action-specific planning
        if action == "start":
            target = params.get("target", "all")
            if target == "all":
                tasks.append(Task(str(task_id), "boot", "registry", {"quick": False}))
            else:
                tasks.append(Task(str(task_id), "enable", target, {}))

        elif action == "stop":
            target = params.get("target", "all")
            if target == "all":
                tasks.append(Task(str(task_id), "shutdown", "registry", {}))
            else:
                tasks.append(Task(str(task_id), "disable", target, {}))

        elif action == "status":
            tasks.append(Task(str(task_id), "get_status", "registry", {}))

        elif action == "list":
            tasks.append(Task(str(task_id), "list_modules", "registry", {}))

        elif action == "upload":
            files = params.get("files", [])
            for i, f in enumerate(files):
                tasks.append(Task(str(task_id + i), "ingest", "doc_intel", {"file": f}))

        elif action == "query":
            tasks.append(Task(str(task_id), "query", "doc_intel", {"question": intent["intent"]}))

        elif action == "chat":
            tasks.append(Task(str(task_id), "chat", "llm", {"message": intent["intent"]}))

        elif action == "backup":
            tasks.append(Task(str(task_id), "backup", "backup", {}))

        elif action == "update":
            tasks.append(Task(str(task_id), "check_update", "deployment", {}))

        elif action == "config":
            for k, v in params.items():
                tasks.append(Task(str(task_id), "set", "config", {"key": k, "value": v}))
                task_id += 1

        elif action == "learn":
            tasks.append(Task(str(task_id), "learn", "learning", {"input": intent["intent"]}))

        elif action == "create":
            tasks.append(Task(str(task_id), "create_content", "genesis_hub", {"topic": intent["intent"]}))

        elif action == "protect":
            tasks.append(Task(str(task_id), "scan", "security", {}))
            tasks.append(Task(str(task_id + 1), "guard", "guardian", {}))

        else:
            # Default: route to genesis hub for general processing
            tasks.append(Task(str(task_id), "process", "genesis_hub", {"message": intent["intent"]}))

        return Plan(
            intent=intent["intent"],
            confidence=confidence,
            tasks=tasks,
            context={"parsed_intent": intent},
        )


class TaskExecutor:
    """Execute tasks against MAGNATRIX-OS modules."""

    def __init__(self, registry: Any = None) -> None:
        self.registry = registry
        self._lock = threading.Lock()
        self._results: Dict[str, Any] = {}

    def execute(self, plan: Plan) -> ExecutionResult:
        """Execute a plan."""
        t0 = time.time()
        completed = 0
        failed = 0
        outputs = []

        # Execute tasks in order (simple dependency handling)
        for task in plan.tasks:
            task.attempts += 1
            task.state = "running"
            task.start_time = time.time()

            result = self._execute_task(task)

            task.end_time = time.time()
            task.result = result

            if result.get("success", False):
                task.state = "success"
                completed += 1
            else:
                task.state = "failed"
                task.error = result.get("error", "Unknown error")
                failed += 1
                # Retry if attempts < max
                if task.attempts < task.max_attempts:
                    task.state = "retry"
                    # Simple retry with delay
                    time.sleep(0.5)
                    retry_result = self._execute_task(task)
                    task.result = retry_result
                    if retry_result.get("success", False):
                        task.state = "success"
                        completed += 1
                        failed -= 1

            outputs.append({
                "task_id": task.id,
                "action": task.action,
                "module": task.target_module,
                "state": task.state,
                "result": task.result,
                "duration_ms": round((task.end_time - task.start_time) * 1000, 1),
            })

        exec_time = (time.time() - t0) * 1000

        return ExecutionResult(
            success=failed == 0,
            completed_tasks=completed,
            failed_tasks=failed,
            outputs=outputs,
            execution_time_ms=round(exec_time, 1),
        )

    def _execute_task(self, task: Task) -> Dict[str, Any]:
        """Execute a single task."""
        try:
            if task.action == "boot":
                if self.registry and hasattr(self.registry, "boot"):
                    result = self.registry.boot(task.params.get("quick", False))
                    return {"success": True, "data": result}
                return {"success": False, "error": "Registry not available"}

            elif task.action == "shutdown":
                if self.registry and hasattr(self.registry, "shutdown"):
                    result = self.registry.shutdown()
                    return {"success": True, "data": result}
                return {"success": False, "error": "Registry not available"}

            elif task.action == "get_status":
                if self.registry and hasattr(self.registry, "stats"):
                    return {"success": True, "data": self.registry.stats()}
                return {"success": False, "error": "Registry not available"}

            elif task.action == "list_modules":
                if self.registry and hasattr(self.registry, "list_modules"):
                    return {"success": True, "data": self.registry.list_modules()}
                return {"success": False, "error": "Registry not available"}

            elif task.action in ("enable", "disable"):
                # Module state toggle
                return {"success": True, "data": {"module": task.target_module, "action": task.action}}

            elif task.action == "ingest":
                module = self._get_module("doc_intel")
                if module and hasattr(module, "ingest_file"):
                    result = module.ingest_file(task.params["file"])
                    return {"success": result.success, "data": {"chunks": result.chunks, "chars": result.chars}}
                return {"success": False, "error": "Document intelligence not available"}

            elif task.action == "query":
                module = self._get_module("doc_intel")
                if module and hasattr(module, "query"):
                    result = module.query(task.params["question"])
                    return {"success": True, "data": result}
                return {"success": False, "error": "Document intelligence not available"}

            elif task.action == "chat":
                module = self._get_module("llm")
                if module and hasattr(module, "chat"):
                    result = module.chat(task.params["message"])
                    return {"success": True, "data": result}
                # Fallback: return echo
                return {"success": True, "data": {"text": f"Echo: {task.params['message']}"}}

            elif task.action == "backup":
                module = self._get_module("backup")
                if module and hasattr(module, "backup"):
                    path = module.backup(str(Path.cwd()))
                    return {"success": True, "data": {"path": path}}
                return {"success": False, "error": "Backup module not available"}

            elif task.action == "check_update":
                module = self._get_module("deployment")
                if module and hasattr(module, "check_update"):
                    result = module.check_update()
                    return {"success": True, "data": result}
                return {"success": False, "error": "Deployment module not available"}

            elif task.action == "set":
                module = self._get_module("config")
                if module and hasattr(module, "set"):
                    module.set(task.params["key"], task.params["value"])
                    return {"success": True, "data": {"key": task.params["key"], "value": task.params["value"]}}
                return {"success": False, "error": "Config module not available"}

            elif task.action == "learn":
                module = self._get_module("learning")
                if module and hasattr(module, "learn"):
                    result = module.learn(task.params["input"])
                    return {"success": True, "data": result}
                return {"success": False, "error": "Learning module not available"}

            elif task.action == "create_content":
                module = self._get_module("genesis_hub")
                if module and hasattr(module, "create_content"):
                    result = module.create_content(task.params["topic"])
                    return {"success": True, "data": result}
                return {"success": False, "error": "Genesis hub not available"}

            elif task.action == "scan":
                module = self._get_module("security")
                if module and hasattr(module, "scan"):
                    result = module.scan()
                    return {"success": True, "data": result}
                return {"success": False, "error": "Security module not available"}

            elif task.action == "guard":
                module = self._get_module("guardian")
                if module and hasattr(module, "guard"):
                    result = module.guard()
                    return {"success": True, "data": result}
                return {"success": False, "error": "Guardian module not available"}

            elif task.action == "process":
                module = self._get_module("genesis_hub")
                if module and hasattr(module, "process_user_message"):
                    result = module.process_user_message("user_1", task.params["message"])
                    return {"success": True, "data": result}
                return {"success": False, "error": "Genesis hub not available"}

            else:
                return {"success": False, "error": f"Unknown action: {task.action}"}

        except Exception as e:
            return {"success": False, "error": str(e), "traceback": traceback.format_exc()}

    def _get_module(self, name: str) -> Any:
        if self.registry and hasattr(self.registry, "get_module"):
            return self.registry.get_module(name)
        return None


class AgentOrchestrator:
    """Main orchestrator combining parser, planner, and executor."""

    def __init__(self, registry: Any = None) -> None:
        self.registry = registry
        self.parser = IntentParser()
        self.planner = TaskPlanner(registry)
        self.executor = TaskExecutor(registry)
        self._history: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._feedback_handlers: List[Callable[[Dict[str, Any]], None]] = []

    def process(self, user_input: str) -> Dict[str, Any]:
        """Process user input end-to-end."""
        t0 = time.time()

        # 1. Parse intent
        intent = self.parser.parse(user_input)

        # 2. Plan
        plan = self.planner.plan(intent)

        # 3. Execute
        result = self.executor.execute(plan)

        # 4. Build response
        response = self._build_response(plan, result)

        # 5. Record history
        with self._lock:
            self._history.append({
                "input": user_input,
                "intent": intent,
                "plan": {"tasks_count": len(plan.tasks), "confidence": plan.confidence},
                "result": result,
                "response": response,
                "timestamp": time.time(),
            })
            if len(self._history) > 100:
                self._history = self._history[-50:]

        # 6. Feedback loop
        for handler in self._feedback_handlers:
            try:
                handler({"input": user_input, "result": result})
            except Exception:
                pass

        return response

    def _build_response(self, plan: Plan, result: ExecutionResult) -> Dict[str, Any]:
        """Build human-readable response from execution result."""
        if result.success and result.completed_tasks > 0:
            # Success response
            outputs = []
            for out in result.outputs:
                if out["state"] == "success":
                    data = out.get("result", {}).get("data", {})
                    if out["action"] == "list_modules":
                        modules = data if isinstance(data, list) else []
                        active = [m for m in modules if m.get("state") == "active"]
                        outputs.append(f"Found {len(modules)} modules, {len(active)} active.")
                    elif out["action"] == "get_status":
                        stats = data if isinstance(data, dict) else {}
                        outputs.append(f"System status: {stats.get('loaded', 0)}/{stats.get('total_registered', 0)} modules loaded.")
                    elif out["action"] == "ingest":
                        outputs.append(f"Document ingested: {data.get('chunks', 0)} chunks, {data.get('chars', 0)} characters.")
                    elif out["action"] == "query":
                        ans = data.get("answer", "No answer") if isinstance(data, dict) else str(data)
                        outputs.append(f"Answer: {ans[:200]}...")
                    elif out["action"] == "chat":
                        text = data.get("text", "") if isinstance(data, dict) else str(data)
                        outputs.append(text)
                    else:
                        outputs.append(f"Task {out['action']} completed successfully.")

            return {
                "success": True,
                "text": "\n".join(outputs) if outputs else "Done.",
                "tasks": result.completed_tasks,
                "time_ms": result.execution_time_ms,
            }
        else:
            # Failure response
            errors = [out.get("result", {}).get("error", "Unknown") for out in result.outputs if out["state"] == "failed"]
            return {
                "success": False,
                "text": f"Failed to complete {result.failed_tasks} task(s). Errors: {', '.join(errors[:3])}",
                "tasks": result.completed_tasks,
                "failed": result.failed_tasks,
                "time_ms": result.execution_time_ms,
            }

    def on_feedback(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        self._feedback_handlers.append(handler)

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            return self._history[-limit:]

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._history)
            success = sum(1 for h in self._history if h["result"].success)
            return {
                "total_interactions": total,
                "success_rate": round(success / total, 2) if total > 0 else 0,
                "avg_tasks": sum(len(h["plan"]["tasks_count"]) for h in self._history) / total if total > 0 else 0,
            }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== AI Agent Orchestrator Demo ===\n")

    # Mock registry for demo
    class MockRegistry:
        def __init__(self):
            self._mods = {}
        def boot(self, quick=False):
            return {"loaded": 5, "total": 5, "boot_time_ms": 100}
        def shutdown(self):
            return {"shutdown": 5}
        def stats(self):
            return {"total_registered": 107, "loaded": 98, "failed": 3}
        def list_modules(self):
            return [{"name": "config", "state": "active"}, {"name": "llm", "state": "active"}]
        def get_module(self, name):
            return None

    registry = MockRegistry()
    orchestrator = AgentOrchestrator(registry)

    test_inputs = [
        "start the system",
        "what is the status of modules",
        "list all modules",
        "upload report.pdf",
        "tell me about neural networks",
        "backup everything",
        "check for updates",
        "scan for security issues",
    ]

    for inp in test_inputs:
        print(f"User: {inp}")
        result = orchestrator.process(inp)
        print(f"AI: {result['text']}")
        print(f"   [tasks: {result['tasks']}, time: {result['time_ms']}ms, success: {result['success']}]")
        print()

    print(f"History: {len(orchestrator.get_history())} interactions")
    print(f"Stats: {orchestrator.stats()}")


if __name__ == "__main__":
    _demo()
