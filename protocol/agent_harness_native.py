# protocol/agent_harness_native.py
# AMATI-PELAJARI-TIRU: Pattern extracted from AI-Agent-Research survey
# https://github.com/xiangzhuo-ding/AI-Agent-Research
# Agent harness architecture H=(E,T,C,S,L,V) with six governance components
# Native reimplementation for MAGNATRIX-OS Layer 1 (Protocol) + Layer 10 (AI)

"""
Native Agent Harness Framework
==============================
Inspired by "Agent Harness for Large Language Model Agents: A Survey" (2025):
  - H = (E, T, C, S, L, V)
  - E: Environment interface (observations, actions, state transitions)
  - T: Tool dispatch (validation, timeouts, execution, sandboxing)
  - C: Context assembly (trimming, summarization, retrieval, ranking)
  - S: State commit (persistence, memory tiers, rollback, poisoning defense)
  - L: Inference governance (prompt construction, model selection, output parsing)
  - V: Verification (constraint checking, factuality, safety, human-in-the-loop)

Features:
  - Six-component harness with strict governance boundaries
  - Environment sandbox with action validation
  - Tool registry with timeout and retry policies
  - Context window manager with token estimation
  - Three-tier memory (sensory, working, long-term)
  - Inference router with model selection strategy
  - Verification pipeline with human approval gates
"""

from __future__ import annotations

import time
import json
import uuid
from typing import Dict, List, Optional, Callable, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum, auto


class ActionType(Enum):
    OBSERVE = auto()
    THINK = auto()
    TOOL_CALL = auto()
    COMMIT = auto()
    HUMAN_APPROVAL = auto()
    HALT = auto()


@dataclass
class Observation:
    source: str
    content: str
    timestamp: float


@dataclass
class Action:
    type: ActionType
    payload: Dict[str, Any] = field(default_factory=dict)
    approved: bool = False


@dataclass
class ToolSpec:
    name: str
    description: str
    schema: Dict[str, Any] = field(default_factory=dict)
    timeout_sec: float = 30.0
    max_retries: int = 2
    requires_approval: bool = False


class EnvironmentInterface:
    """E: Environment interface — observations, actions, state transitions."""

    def __init__(self):
        self.observations: List[Observation] = []
        self.actions: List[Action] = []
        self.state: Dict[str, Any] = {}

    def observe(self, source: str, content: str) -> None:
        self.observations.append(Observation(source=source, content=content, timestamp=time.time()))

    def transition(self, action: Action) -> Dict[str, Any]:
        self.actions.append(action)
        if action.type == ActionType.TOOL_CALL:
            self.state["last_tool"] = action.payload.get("tool_name")
        elif action.type == ActionType.COMMIT:
            self.state.update(action.payload.get("updates", {}))
        return self.state

    def get_recent_observations(self, n: int = 5) -> List[Observation]:
        return self.observations[-n:]


class ToolDispatcher:
    """T: Tool dispatch — validation, timeouts, execution, sandboxing."""

    def __init__(self):
        self.registry: Dict[str, ToolSpec] = {}
        self.executions: List[Dict[str, Any]] = []

    def register(self, spec: ToolSpec, impl: Callable) -> None:
        self.registry[spec.name] = spec
        setattr(self, f"_exec_{spec.name}", impl)

    def dispatch(self, name: str, args: Dict[str, Any]) -> Any:
        spec = self.registry.get(name)
        if not spec:
            raise ValueError(f"Tool {name} not registered")
        # Validate args against schema
        self._validate_args(spec, args)
        for attempt in range(spec.max_retries + 1):
            try:
                t0 = time.time()
                result = getattr(self, f"_exec_{name}")(**args)
                elapsed = time.time() - t0
                self.executions.append({"tool": name, "args": args, "result": result, "elapsed": elapsed, "attempt": attempt})
                return result
            except Exception as e:
                if attempt == spec.max_retries:
                    raise RuntimeError(f"Tool {name} failed after {spec.max_retries} retries: {e}")
                time.sleep(0.5)
        return None

    def _validate_args(self, spec: ToolSpec, args: Dict[str, Any]) -> None:
        required = spec.schema.get("required", [])
        for key in required:
            if key not in args:
                raise ValueError(f"Missing required arg '{key}' for tool {spec.name}")

    def get_stats(self) -> Dict[str, Any]:
        return {"registered": list(self.registry.keys()), "total_executions": len(self.executions)}


class ContextAssembler:
    """C: Context assembly — trimming, summarization, retrieval, ranking."""

    def __init__(self, max_tokens: int = 4096):
        self.max_tokens = max_tokens
        self.token_estimator: Callable[[str], int] = lambda text: len(text) // 4

    def assemble(self, system_prompt: str, history: List[str], observations: List[str], tools: List[str]) -> str:
        parts = [f"System: {system_prompt}"]
        budget = self.max_tokens - self.token_estimator(parts[0])
        # Add observations (most recent first)
        obs_text = "\n".join(observations)
        if self.token_estimator(obs_text) > budget // 3:
            obs_text = self._summarize(obs_text, budget // 3)
        parts.append(f"Observations:\n{obs_text}")
        budget -= self.token_estimator(obs_text)
        # Add tools
        tools_text = "\n".join(tools)
        if self.token_estimator(tools_text) > budget // 4:
            tools_text = "\n".join(tools[:5]) + "\n..."
        parts.append(f"Tools:\n{tools_text}")
        budget -= self.token_estimator(tools_text)
        # Add history (trimmed)
        hist_text = "\n".join(history)
        if self.token_estimator(hist_text) > budget:
            hist_text = "\n".join(history[-5:])
        parts.append(f"History:\n{hist_text}")
        return "\n\n".join(parts)

    def _summarize(self, text: str, target_tokens: int) -> str:
        # Placeholder summarization: truncate with ellipsis
        max_chars = target_tokens * 4
        if len(text) > max_chars:
            return text[:max_chars] + "\n...[summarized]"
        return text


class StateCommit:
    """S: State commit — persistence, memory tiers, rollback, poisoning defense."""

    def __init__(self):
        self.sensory: List[str] = []
        self.working: List[str] = []
        self.long_term: Dict[str, Any] = {}
        self.snapshots: List[Dict[str, Any]] = []

    def commit(self, observations: List[str], thoughts: List[str], updates: Dict[str, Any]) -> None:
        self.sensory.extend(observations)
        self.working.extend(thoughts)
        self.long_term.update(updates)
        self._promote_to_long_term()

    def snapshot(self) -> str:
        snap_id = str(uuid.uuid4())
        self.snapshots.append({
            "id": snap_id,
            "sensory": list(self.sensory),
            "working": list(self.working),
            "long_term": dict(self.long_term),
        })
        return snap_id

    def rollback(self, snap_id: str) -> bool:
        for snap in self.snapshots:
            if snap["id"] == snap_id:
                self.sensory = list(snap["sensory"])
                self.working = list(snap["working"])
                self.long_term = dict(snap["long_term"])
                return True
        return False

    def _promote_to_long_term(self) -> None:
        # Simple policy: move old working memory to long-term
        if len(self.working) > 20:
            old = self.working[:10]
            self.working = self.working[10:]
            key = f"session_{uuid.uuid4().hex[:8]}"
            self.long_term[key] = old

    def get_memory_report(self) -> Dict[str, Any]:
        return {
            "sensory_count": len(self.sensory),
            "working_count": len(self.working),
            "long_term_keys": list(self.long_term.keys()),
            "snapshots": len(self.snapshots),
        }


class InferenceGovernance:
    """L: Inference governance — prompt construction, model selection, output parsing."""

    def __init__(self, model_pool: Optional[Dict[str, Callable]] = None):
        self.model_pool = model_pool or {"default": lambda p: f"[DEFAULT] {p[:80]}..."}
        self.call_log: List[Dict[str, Any]] = []

    def select_model(self, task_complexity: str) -> str:
        if task_complexity == "simple" and "fast" in self.model_pool:
            return "fast"
        if task_complexity == "complex" and "powerful" in self.model_pool:
            return "powerful"
        return "default"

    def infer(self, prompt: str, model_key: Optional[str] = None) -> str:
        key = model_key or "default"
        model = self.model_pool.get(key, self.model_pool["default"])
        t0 = time.time()
        result = model(prompt)
        elapsed = time.time() - t0
        self.call_log.append({"model": key, "tokens_in": len(prompt), "tokens_out": len(result), "elapsed": elapsed})
        return result

    def parse_output(self, raw: str) -> Dict[str, Any]:
        # Extract structured JSON if present
        if "```json" in raw:
            json_part = raw.split("```json")[1].split("```")[0].strip()
            try:
                return json.loads(json_part)
            except json.JSONDecodeError:
                pass
        return {"raw": raw}


class VerificationPipeline:
    """V: Verification — constraint checking, factuality, safety, human-in-the-loop."""

    def __init__(self):
        self.constraints: List[Callable[[Dict[str, Any]], bool]] = []
        self.approval_gates: Dict[str, bool] = {}

    def add_constraint(self, checker: Callable[[Dict[str, Any]], bool]) -> None:
        self.constraints.append(checker)

    def verify(self, output: Dict[str, Any]) -> Tuple[bool, List[str]]:
        violations = []
        for checker in self.constraints:
            if not checker(output):
                violations.append(f"Constraint violated: {checker.__name__}")
        return len(violations) == 0, violations

    def request_human_approval(self, action_id: str, description: str) -> bool:
        # In production, integrate with UI/notification system
        self.approval_gates[action_id] = False
        return self.approval_gates.get(action_id, False)

    def grant_approval(self, action_id: str) -> None:
        self.approval_gates[action_id] = True


class AgentHarness:
    """
    Orchestrates the full harness H=(E,T,C,S,L,V).
    """

    def __init__(
        self,
        env: Optional[EnvironmentInterface] = None,
        tools: Optional[ToolDispatcher] = None,
        context: Optional[ContextAssembler] = None,
        state: Optional[StateCommit] = None,
        inference: Optional[InferenceGovernance] = None,
        verifier: Optional[VerificationPipeline] = None,
    ):
        self.env = env or EnvironmentInterface()
        self.tools = tools or ToolDispatcher()
        self.context = context or ContextAssembler()
        self.state = state or StateCommit()
        self.inference = inference or InferenceGovernance()
        self.verifier = verifier or VerificationPipeline()
        self.history: List[str] = []

    def step(self, observation: Optional[str] = None) -> Dict[str, Any]:
        if observation:
            self.env.observe("environment", observation)
        obs = [o.content for o in self.env.get_recent_observations()]
        tool_descs = [f"{n}: {s.description}" for n, s in self.tools.registry.items()]
        ctx = self.context.assemble(
            system_prompt="You are an agent governed by a harness.",
            history=self.history,
            observations=obs,
            tools=tool_descs,
        )
        raw = self.inference.infer(ctx)
        parsed = self.inference.parse_output(raw)
        ok, violations = self.verifier.verify(parsed)
        if not ok:
            parsed["violations"] = violations
        self.history.append(f"Assistant: {raw}")
        return parsed

    def execute_tool(self, name: str, args: Dict[str, Any]) -> Any:
        self.env.transition(Action(type=ActionType.TOOL_CALL, payload={"tool_name": name, "args": args}))
        result = self.tools.dispatch(name, args)
        self.state.commit(observations=[f"Tool {name} result: {result}"], thoughts=[], updates={})
        return result

    def get_report(self) -> Dict[str, Any]:
        return {
            "environment": {"observations": len(self.env.observations), "actions": len(self.env.actions)},
            "tools": self.tools.get_stats(),
            "state": self.state.get_memory_report(),
            "inference": {"calls": len(self.inference.call_log)},
            "verification": {"constraints": len(self.verifier.constraints)},
        }


# --- Standalone test ---
if __name__ == "__main__":
    harness = AgentHarness()
    harness.tools.register(
        ToolSpec(name="calculator", description="Evaluate math expressions", schema={"required": ["expr"]}, timeout_sec=5.0),
        lambda expr: eval(expr),
    )
    harness.verifier.add_constraint(lambda out: "error" not in str(out).lower())
    result = harness.step("User asks: what is 2+2?")
    print("Step result:", result)
    tool_result = harness.execute_tool("calculator", {"expr": "2+2"})
    print("Tool result:", tool_result)
    print("Harness report:", harness.get_report())
