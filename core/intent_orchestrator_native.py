#!/usr/bin/env python3
"""
Intent Orchestrator — MAGNATRIX-OS Intent-Based Module Orchestration
=====================================================================
Declare desired state (e.g., "search + summarize + store"), auto-select
modules, chain them, execute. Pure rule + pattern matching. No AI libs.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


@dataclass
class Intent:
    """A parsed user intent with goals and constraints."""
    raw_text: str = ""
    action: str = ""
    targets: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5  # 1-10, lower = higher
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    """A plan of module calls to fulfill an intent."""
    intent: Intent
    steps: List[Dict[str, Any]] = field(default_factory=list)
    estimated_cost: float = 0.0
    estimated_time_ms: float = 0.0
    fallback_steps: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ExecutionResult:
    """Result of executing an intent plan."""
    success: bool = False
    output: Any = None
    steps_executed: int = 0
    steps_failed: int = 0
    duration_ms: float = 0.0
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class IntentParser:
    """
    Parse natural language-like intent declarations into structured Intents.
    
    Uses keyword extraction + pattern matching. No NLP libraries.
    """

    ACTION_PATTERNS = {
        "search": [r"search\s+for", r"find\s+", r"look\s+up", r"query", r"cari", r"temukan"],
        "summarize": [r"summarize", r"summary", r"ringkasan", r"sum\s+up"],
        "store": [r"store", r"save", r"persist", r"simpan", r"save\s+to"],
        "analyze": [r"analyze", r"analysis", r"analisis", r"evaluate"],
        "transform": [r"transform", r"convert", r"ubah", r"format"],
        "notify": [r"notify", r"alert", r"send", r"notif", r"inform"],
        "backup": [r"backup", r"snapshot", r"cadangkan"],
        "deploy": [r"deploy", r"release", r"publish"],
        "train": [r"train", r"fit", r"learn", r"latih"],
        "predict": [r"predict", r"forecast", r"prediksi"],
        "monitor": [r"monitor", r"watch", r"track", r"pantau"],
        "heal": [r"heal", r"fix", r"repair", r"recover", r"perbaiki"],
    }

    TARGET_PATTERNS = {
        "data": [r"data", r"dataset", r"file", r"record"],
        "model": [r"model", r"ai", r"llm", r"neural"],
        "system": [r"system", r"os", r"infrastructure"],
        "user": [r"user", r"account", r"profile"],
        "log": [r"log", r"event", r"audit"],
        "config": [r"config", r"setting", r"preference"],
        "security": [r"security", r"auth", r"permission"],
    }

    CONSTRAINT_PATTERNS = {
        "fast": [r"fast", r"quick", r"quickly", r"cepat", r"instant"],
        "secure": [r"secure", r"safe", r"encrypted", r"aman"],
        "local": [r"local", r"offline", r"self-hosted"],
        "cloud": [r"cloud", r"remote", r"online"],
        "batch": [r"batch", r"bulk", r"all at once"],
        "realtime": [r"real.?time", r"live", r"streaming"],
    }

    def parse(self, text: str) -> Intent:
        """Parse intent text into structured Intent."""
        text_lower = text.lower()
        intent = Intent(raw_text=text)

        # Detect action
        for action, patterns in self.ACTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    intent.action = action
                    break
            if intent.action:
                break

        # Detect targets
        for target, patterns in self.TARGET_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    if target not in intent.targets:
                        intent.targets.append(target)
                    break

        # Detect constraints
        for constraint, patterns in self.CONSTRAINT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    intent.constraints[constraint] = True
                    break

        # Extract priority keywords
        if re.search(r"urgent|critical|asap|emergency", text_lower):
            intent.priority = 1
        elif re.search(r"important|high priority", text_lower):
            intent.priority = 2
        elif re.search(r"low priority|whenever|later", text_lower):
            intent.priority = 8

        # Extract quoted strings as specific targets
        quoted = re.findall(r'"([^"]+)"', text)
        if quoted:
            intent.metadata["quoted"] = quoted

        # Extract numbers
        numbers = re.findall(r'\d+', text)
        if numbers:
            intent.metadata["numbers"] = [int(n) for n in numbers]

        return intent

    def parse_structured(self, data: Dict[str, Any]) -> Intent:
        """Parse from structured data (e.g., JSON)."""
        return Intent(
            raw_text=data.get("text", ""),
            action=data.get("action", ""),
            targets=data.get("targets", []),
            constraints=data.get("constraints", {}),
            priority=data.get("priority", 5),
            metadata=data.get("metadata", {})
        )


class ModuleSelector:
    """
    Select modules based on intent and capabilities.
    
    Maps intent actions to modules that provide those capabilities.
    """

    CAPABILITY_MAP = {
        "search": ["search", "rag", "data_lake", "query_engine"],
        "summarize": ["nlq", "doc_intel", "analytics", "text_processor"],
        "store": ["database", "data_lake", "cache", "state_persistence"],
        "analyze": ["analytics", "code", "security", "data_quality"],
        "transform": ["etl", "data_lake", "compression", "encryption"],
        "notify": ["logging", "event_streaming", "alert", "notification"],
        "backup": ["backup", "snapshot", "replication"],
        "deploy": ["cicd", "auto_deployment", "bluegreen", "canary"],
        "train": ["ai_training", "local_llm", "model_serving"],
        "predict": ["analytics", "ai_model_registry", "edge_inference"],
        "monitor": ["monitoring", "slo", "log_analysis", "intrusion_detection"],
        "heal": ["self_healing", "backup", "state_persistence"],
    }

    def __init__(self, module_registry: Optional[Any] = None):
        self._registry = module_registry
        self._module_capabilities: Dict[str, List[str]] = {}

    def register_module_capabilities(self, module_name: str, capabilities: List[str]) -> None:
        self._module_capabilities[module_name] = capabilities

    def select(self, intent: Intent) -> List[str]:
        """Select modules that can fulfill the intent."""
        candidates = []
        action_modules = self.CAPABILITY_MAP.get(intent.action, [])

        for mod_name in action_modules:
            if self._module_available(mod_name):
                candidates.append(mod_name)

        # Also check targets for additional modules
        for target in intent.targets:
            target_modules = self.CAPABILITY_MAP.get(target, [])
            for mod_name in target_modules:
                if mod_name not in candidates and self._module_available(mod_name):
                    candidates.append(mod_name)

        # Sort by priority and constraints
        if "fast" in intent.constraints:
            candidates = self._sort_by_speed(candidates)
        if "secure" in intent.constraints:
            candidates = self._sort_by_security(candidates)

        return candidates

    def _module_available(self, name: str) -> bool:
        if self._registry and hasattr(self._registry, "get_module"):
            try:
                return self._registry.get_module(name) is not None
            except Exception:
                pass
        return name in self._module_capabilities

    def _sort_by_speed(self, candidates: List[str]) -> List[str]:
        fast_modules = {"cache", "search", "local_llm"}
        return sorted(candidates, key=lambda c: 0 if c in fast_modules else 1)

    def _sort_by_security(self, candidates: List[str]) -> List[str]:
        secure_modules = {"encryption", "secret", "quantum_safe", "auth", "security"}
        return sorted(candidates, key=lambda c: 0 if c in secure_modules else 1)


class PlanGenerator:
    """
    Generate execution plans from intents and selected modules.
    
    Creates step-by-step plans with fallback chains.
    """

    def __init__(self, selector: ModuleSelector):
        self._selector = selector
        self._step_templates: Dict[str, Dict[str, Any]] = {
            "search": {"action": "query", "params": {}},
            "summarize": {"action": "process", "params": {"mode": "summarize"}},
            "store": {"action": "persist", "params": {}},
            "analyze": {"action": "analyze", "params": {}},
            "transform": {"action": "transform", "params": {}},
            "notify": {"action": "notify", "params": {}},
            "backup": {"action": "backup", "params": {}},
            "deploy": {"action": "deploy", "params": {}},
            "train": {"action": "train", "params": {}},
            "predict": {"action": "predict", "params": {}},
            "monitor": {"action": "monitor", "params": {}},
            "heal": {"action": "heal", "params": {}},
        }

    def generate(self, intent: Intent) -> ExecutionPlan:
        """Generate an execution plan for the intent."""
        modules = self._selector.select(intent)
        plan = ExecutionPlan(intent=intent)

        if not modules:
            plan.steps.append({
                "module": "unknown",
                "action": "noop",
                "params": {},
                "fallback": None
            })
            return plan

        # Build steps based on action type
        if intent.action == "search":
            plan = self._plan_search(intent, modules)
        elif intent.action == "summarize":
            plan = self._plan_summarize(intent, modules)
        elif intent.action == "store":
            plan = self._plan_store(intent, modules)
        elif intent.action == "analyze":
            plan = self._plan_analyze(intent, modules)
        elif intent.action == "transform":
            plan = self._plan_transform(intent, modules)
        elif intent.action == "backup":
            plan = self._plan_backup(intent, modules)
        elif intent.action == "heal":
            plan = self._plan_heal(intent, modules)
        else:
            # Generic plan: call first available module
            for mod in modules[:3]:
                template = self._step_templates.get(intent.action, {"action": "execute", "params": {}})
                plan.steps.append({
                    "module": mod,
                    "action": template["action"],
                    "params": {**template["params"], **intent.metadata},
                    "fallback": None
                })

        # Add fallback steps for critical steps
        for step in plan.steps:
            if step["module"] in modules[1:]:
                step["fallback"] = modules[modules.index(step["module"]) + 1] if modules.index(step["module"]) + 1 < len(modules) else None

        plan.estimated_time_ms = len(plan.steps) * 100.0
        plan.estimated_cost = len(plan.steps) * 1.0
        return plan

    def _plan_search(self, intent: Intent, modules: List[str]) -> ExecutionPlan:
        plan = ExecutionPlan(intent=intent)
        search_mod = next((m for m in modules if "search" in m or "rag" in m), modules[0] if modules else "unknown")
        plan.steps.append({"module": search_mod, "action": "query", "params": {"query": intent.raw_text}, "fallback": None})
        return plan

    def _plan_summarize(self, intent: Intent, modules: List[str]) -> ExecutionPlan:
        plan = ExecutionPlan(intent=intent)
        # First search, then summarize
        search_mod = next((m for m in modules if "search" in m or "rag" in m or "data" in m), modules[0] if modules else "unknown")
        summary_mod = next((m for m in modules if "nlq" in m or "doc" in m or "analytics" in m), modules[0] if modules else "unknown")
        plan.steps.append({"module": search_mod, "action": "fetch", "params": {}, "fallback": None})
        plan.steps.append({"module": summary_mod, "action": "summarize", "params": {}, "fallback": None})
        return plan

    def _plan_store(self, intent: Intent, modules: List[str]) -> ExecutionPlan:
        plan = ExecutionPlan(intent=intent)
        store_mod = next((m for m in modules if "database" in m or "data_lake" in m or "cache" in m), modules[0] if modules else "unknown")
        plan.steps.append({"module": store_mod, "action": "persist", "params": {"data": intent.metadata.get("quoted", [])}, "fallback": None})
        return plan

    def _plan_analyze(self, intent: Intent, modules: List[str]) -> ExecutionPlan:
        plan = ExecutionPlan(intent=intent)
        analyze_mod = next((m for m in modules if "analytics" in m or "code" in m or "security" in m), modules[0] if modules else "unknown")
        plan.steps.append({"module": analyze_mod, "action": "analyze", "params": {"target": intent.targets}, "fallback": None})
        return plan

    def _plan_transform(self, intent: Intent, modules: List[str]) -> ExecutionPlan:
        plan = ExecutionPlan(intent=intent)
        transform_mod = next((m for m in modules if "etl" in m or "compression" in m or "encryption" in m), modules[0] if modules else "unknown")
        plan.steps.append({"module": transform_mod, "action": "transform", "params": {"target": intent.targets}, "fallback": None})
        return plan

    def _plan_backup(self, intent: Intent, modules: List[str]) -> ExecutionPlan:
        plan = ExecutionPlan(intent=intent)
        backup_mod = next((m for m in modules if "backup" in m or "snapshot" in m), modules[0] if modules else "unknown")
        plan.steps.append({"module": backup_mod, "action": "backup", "params": {"target": intent.targets}, "fallback": None})
        return plan

    def _plan_heal(self, intent: Intent, modules: List[str]) -> ExecutionPlan:
        plan = ExecutionPlan(intent=intent)
        heal_mod = next((m for m in modules if "heal" in m or "self" in m or "backup" in m), modules[0] if modules else "unknown")
        plan.steps.append({"module": heal_mod, "action": "heal", "params": {"target": intent.targets}, "fallback": None})
        return plan


class PlanExecutor:
    """
    Execute generated plans by calling modules via the message router.
    """

    def __init__(self, message_router: Optional[Any] = None):
        self._router = message_router
        self._execution_history: List[ExecutionResult] = []
        self._lock = threading.Lock()

    def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        """Execute an execution plan."""
        start = time.time()
        result = ExecutionResult()

        for step in plan.steps:
            step_result = self._execute_step(step)
            if step_result:
                result.steps_executed += 1
                result.output = step_result
            else:
                result.steps_failed += 1
                result.errors.append(f"Step failed: {step['module']}.{step['action']}")
                # Try fallback
                if step.get("fallback"):
                    fallback_step = {**step, "module": step["fallback"], "fallback": None}
                    fallback_result = self._execute_step(fallback_step)
                    if fallback_result:
                        result.steps_executed += 1
                        result.output = fallback_result
                    else:
                        result.steps_failed += 1

        result.duration_ms = (time.time() - start) * 1000
        result.success = result.steps_executed > 0 and result.steps_failed == 0

        with self._lock:
            self._execution_history.append(result)

        return result

    def _execute_step(self, step: Dict[str, Any]) -> Any:
        """Execute a single step."""
        if self._router and hasattr(self._router, "send"):
            try:
                message = {
                    "action": step["action"],
                    "params": step.get("params", {})
                }
                return self._router.send(step["module"], message)
            except Exception as e:
                return None
        # Fallback: simulate execution
        return {"simulated": True, "module": step["module"], "action": step["action"]}

    def get_history(self, limit: int = 100) -> List[ExecutionResult]:
        with self._lock:
            return self._execution_history[-limit:]


class IntentOrchestrator:
    """
    Top-level intent orchestrator for MAGNATRIX-OS.
    
    Parses intents, selects modules, generates plans, and executes them.
    """

    CAPABILITIES = ["orchestration", "intent", "planning", "chaining"]

    def __init__(self, repo_root: str = "."):
        self.repo_root = repo_root
        self._parser = IntentParser()
        self._selector = ModuleSelector()
        self._planner = PlanGenerator(self._selector)
        self._executor = PlanExecutor()
        self._lock = threading.Lock()
        self._stats = {"intents_parsed": 0, "plans_generated": 0, "plans_executed": 0, "successes": 0}

    def parse(self, text: str) -> Intent:
        """Parse a natural language intent."""
        intent = self._parser.parse(text)
        with self._lock:
            self._stats["intents_parsed"] += 1
        return intent

    def parse_structured(self, data: Dict[str, Any]) -> Intent:
        return self._parser.parse_structured(data)

    def plan(self, intent: Union[str, Intent]) -> ExecutionPlan:
        """Generate an execution plan for an intent."""
        if isinstance(intent, str):
            intent = self.parse(intent)
        plan = self._planner.generate(intent)
        with self._lock:
            self._stats["plans_generated"] += 1
        return plan

    def execute(self, intent: Union[str, Intent, ExecutionPlan]) -> ExecutionResult:
        """Execute an intent or plan."""
        if isinstance(intent, str):
            intent = self.parse(intent)
        if isinstance(intent, Intent):
            plan = self.plan(intent)
        else:
            plan = intent
        result = self._executor.execute(plan)
        with self._lock:
            self._stats["plans_executed"] += 1
            if result.success:
                self._stats["successes"] += 1
        return result

    def register_module(self, name: str, capabilities: List[str]) -> None:
        """Register a module's capabilities for intent routing."""
        self._selector.register_module_capabilities(name, capabilities)

    def set_router(self, router: Any) -> None:
        """Set the message router for plan execution."""
        self._executor = PlanExecutor(router)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._stats)

    def get_history(self, limit: int = 100) -> List[ExecutionResult]:
        return self._executor.get_history(limit)

    def handle_message(self, message: Dict[str, Any]) -> Any:
        action = message.get("action", "")
        if action == "parse":
            return self.parse(message["text"]).__dict__
        elif action == "plan":
            plan = self.plan(message.get("text", ""))
            return {"steps": plan.steps, "estimated_time": plan.estimated_time_ms}
        elif action == "execute":
            result = self.execute(message.get("text", ""))
            return {"success": result.success, "output": result.output, "duration_ms": result.duration_ms}
        elif action == "stats":
            return self.get_stats()
        return None

    def on_event(self, event) -> None:
        pass
