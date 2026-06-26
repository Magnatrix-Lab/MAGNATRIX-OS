#!/usr/bin/env python3
"""
Temporal Workflow Engine — MAGNATRIX-OS Durable Workflow Engine
================================================================
Saga pattern, retry with exponential backoff, compensation, timeouts,
persistent state. State machine + durable execution. Pure stdlib.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


class WorkflowStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    COMPENSATING = auto()
    COMPENSATED = auto()
    TIMEOUT = auto()
    CANCELLED = auto()


class StepStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    COMPENSATING = auto()
    COMPENSATED = auto()
    SKIPPED = auto()


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    name: str
    action: Callable[..., Any]
    compensation: Optional[Callable[..., Any]] = None
    retry_count: int = 3
    retry_delay_ms: float = 1000.0
    timeout_ms: float = 30000.0
    params: Dict[str, Any] = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    attempts: int = 0


@dataclass
class WorkflowState:
    """Durable state for a workflow instance."""
    workflow_id: str
    name: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    steps: List[WorkflowStep] = field(default_factory=list)
    current_step: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "status": self.status.name,
            "current_step": self.current_step,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "steps": [
                {
                    "name": s.name,
                    "status": s.status.name,
                    "result": s.result,
                    "error": s.error,
                    "attempts": s.attempts,
                }
                for s in self.steps
            ]
        }


class RetryPolicy:
    """Configurable retry policy with exponential backoff and jitter."""

    def __init__(self, max_attempts: int = 3, base_delay_ms: float = 1000.0,
                 max_delay_ms: float = 30000.0, backoff_multiplier: float = 2.0,
                 jitter: bool = True):
        self.max_attempts = max_attempts
        self.base_delay_ms = base_delay_ms
        self.max_delay_ms = max_delay_ms
        self.backoff_multiplier = backoff_multiplier
        self.jitter = jitter

    def calculate_delay(self, attempt: int) -> float:
        delay = self.base_delay_ms * (self.backoff_multiplier ** attempt)
        delay = min(delay, self.max_delay_ms)
        if self.jitter:
            import random
            delay = delay * (0.5 + random.random() * 0.5)
        return delay / 1000.0


class SagaOrchestrator:
    """
    Saga pattern orchestrator for long-running transactions.
    
    Executes steps sequentially. On failure, runs compensations in reverse.
    """

    def __init__(self, retry_policy: Optional[RetryPolicy] = None,
                 state_dir: Optional[str] = None):
        self.retry_policy = retry_policy or RetryPolicy()
        self.state_dir = state_dir
        self._lock = threading.Lock()
        self._active_workflows: Dict[str, WorkflowState] = {}
        self._history: List[WorkflowState] = []

    def execute(self, steps: List[WorkflowStep], name: str = "workflow",
                metadata: Optional[Dict[str, Any]] = None) -> WorkflowState:
        """Execute a saga workflow."""
        workflow_id = str(uuid.uuid4())[:8]
        state = WorkflowState(
            workflow_id=workflow_id,
            name=name,
            steps=steps,
            metadata=metadata or {}
        )

        with self._lock:
            self._active_workflows[workflow_id] = state

        self._persist_state(state)
        state.status = WorkflowStatus.RUNNING

        try:
            for i, step in enumerate(steps):
                state.current_step = i
                self._persist_state(state)

                success = self._execute_step(step, state)
                if not success:
                    state.status = WorkflowStatus.FAILED
                    self._compensate(state, i)
                    break
            else:
                state.status = WorkflowStatus.COMPLETED

        except Exception as e:
            state.status = WorkflowStatus.FAILED
            state.metadata["fatal_error"] = str(e)
            self._compensate(state, state.current_step)

        finally:
            state.completed_at = time.time()
            state.updated_at = time.time()
            with self._lock:
                self._active_workflows.pop(workflow_id, None)
                self._history.append(state)
            self._persist_state(state)

        return state

    def _execute_step(self, step: WorkflowStep, state: WorkflowState) -> bool:
        """Execute a single step with retry logic."""
        step.status = StepStatus.RUNNING
        step.start_time = time.time()

        for attempt in range(step.retry_count + 1):
            step.attempts = attempt + 1
            try:
                # Check timeout
                elapsed = (time.time() - step.start_time) * 1000
                if elapsed > step.timeout_ms:
                    step.status = StepStatus.FAILED
                    step.error = "Timeout"
                    return False

                step.result = step.action(**step.params)
                step.status = StepStatus.COMPLETED
                step.end_time = time.time()
                return True

            except Exception as e:
                step.error = str(e)
                if attempt < step.retry_count:
                    delay = self.retry_policy.calculate_delay(attempt)
                    time.sleep(delay)
                else:
                    step.status = StepStatus.FAILED
                    step.end_time = time.time()
                    return False

        return False

    def _compensate(self, state: WorkflowState, last_completed_idx: int) -> None:
        """Run compensations in reverse order."""
        state.status = WorkflowStatus.COMPENSATING
        self._persist_state(state)

        for i in range(last_completed_idx, -1, -1):
            step = state.steps[i]
            if step.status == StepStatus.COMPLETED and step.compensation:
                step.status = StepStatus.COMPENSATING
                try:
                    step.compensation(**step.params)
                    step.status = StepStatus.COMPENSATED
                except Exception as e:
                    step.error = f"Compensation failed: {e}"

        state.status = WorkflowStatus.COMPENSATED
        self._persist_state(state)

    def _persist_state(self, state: WorkflowState) -> None:
        """Persist workflow state to disk."""
        if self.state_dir:
            try:
                os.makedirs(self.state_dir, exist_ok=True)
                path = os.path.join(self.state_dir, f"{state.workflow_id}.json")
                with open(path, "w") as f:
                    json.dump(state.to_dict(), f, indent=2, default=str)
            except Exception:
                pass

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowState]:
        with self._lock:
            return self._active_workflows.get(workflow_id)

    def get_history(self, limit: int = 100) -> List[WorkflowState]:
        with self._lock:
            return self._history[-limit:]

    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow."""
        with self._lock:
            state = self._active_workflows.get(workflow_id)
            if state and state.status == WorkflowStatus.RUNNING:
                state.status = WorkflowStatus.CANCELLED
                return True
            return False


class TimeoutManager:
    """Manage timeouts for workflow steps and overall workflows."""

    def __init__(self):
        self._timers: Dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def set_timeout(self, workflow_id: str, timeout_ms: float,
                    callback: Callable) -> None:
        """Set a timeout for a workflow."""
        def _timeout():
            callback()
        timer = threading.Timer(timeout_ms / 1000.0, _timeout)
        with self._lock:
            self._timers[workflow_id] = timer
        timer.start()

    def cancel_timeout(self, workflow_id: str) -> None:
        """Cancel a pending timeout."""
        with self._lock:
            timer = self._timers.pop(workflow_id, None)
        if timer:
            timer.cancel()

    def clear_all(self) -> None:
        """Cancel all pending timeouts."""
        with self._lock:
            timers = list(self._timers.values())
            self._timers.clear()
        for timer in timers:
            timer.cancel()


class TemporalWorkflowEngine:
    """
    Top-level durable workflow engine for MAGNATRIX-OS.
    
    Provides saga orchestration, retry, compensation, timeouts, and
    persistent state management.
    """

    CAPABILITIES = ["workflow", "saga", "orchestration", "durability", "retry"]

    def __init__(self, repo_root: str = "."):
        self.repo_root = repo_root
        self.state_dir = os.path.join(repo_root, "data", "workflows")
        self._saga = SagaOrchestrator(retry_policy=RetryPolicy(), state_dir=self.state_dir)
        self._timeout_mgr = TimeoutManager()
        self._lock = threading.Lock()
        self._stats = {"workflows_created": 0, "completed": 0, "failed": 0, "compensated": 0}

    def create_workflow(self, name: str = "workflow") -> WorkflowState:
        """Create a new workflow instance."""
        workflow_id = str(uuid.uuid4())[:8]
        state = WorkflowState(workflow_id=workflow_id, name=name)
        with self._lock:
            self._stats["workflows_created"] += 1
        return state

    def execute(self, steps: List[WorkflowStep], name: str = "workflow",
                metadata: Optional[Dict[str, Any]] = None) -> WorkflowState:
        """Execute a workflow with saga pattern."""
        result = self._saga.execute(steps, name, metadata)
        with self._lock:
            if result.status == WorkflowStatus.COMPLETED:
                self._stats["completed"] += 1
            elif result.status == WorkflowStatus.FAILED:
                self._stats["failed"] += 1
            elif result.status == WorkflowStatus.COMPENSATED:
                self._stats["compensated"] += 1
        return result

    def execute_async(self, steps: List[WorkflowStep], name: str = "workflow",
                      metadata: Optional[Dict[str, Any]] = None) -> str:
        """Execute a workflow asynchronously. Returns workflow ID."""
        workflow_id = str(uuid.uuid4())[:8]

        def _run():
            self.execute(steps, name, metadata)

        threading.Thread(target=_run, daemon=True).start()
        return workflow_id

    def get_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow status."""
        state = self._saga.get_workflow(workflow_id)
        if state:
            return state.to_dict()
        # Try to load from disk
        path = os.path.join(self.state_dir, f"{workflow_id}.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return None

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get workflow execution history."""
        states = self._saga.get_history(limit)
        return [s.to_dict() for s in states]

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._stats)

    def handle_message(self, message: Dict[str, Any]) -> Any:
        action = message.get("action", "")
        if action == "status":
            return self.get_status(message.get("workflow_id", ""))
        elif action == "history":
            return self.get_history(message.get("limit", 100))
        elif action == "stats":
            return self.get_stats()
        return None

    def on_event(self, event) -> None:
        pass
