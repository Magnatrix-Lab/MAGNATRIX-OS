"""Conversation State Machine — FSM for managing conversation flow, states, transitions, guards.

Modul ini menyediakan:
- ConversationState: individual state with entry/exit actions
- StateTransition: transition with guard conditions
- ConversationFSM: finite state machine engine
- StateMachineBuilder: declarative FSM construction
- ConversationManager: high-level conversation orchestration
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from enum import Enum, auto


class StateType(Enum):
    INITIAL = auto()
    NORMAL = auto()
    TERMINAL = auto()
    ERROR = auto()


@dataclass
class ConversationState:
    """A state in the conversation FSM."""
    state_id: str
    name: str
    state_type: StateType = StateType.NORMAL
    on_enter: Optional[Callable[[Dict[str, Any]], None]] = None
    on_exit: Optional[Callable[[Dict[str, Any]], None]] = None
    on_stay: Optional[Callable[[Dict[str, Any]], None]] = None
    timeout: Optional[float] = None  # seconds before auto-transition
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StateTransition:
    """Transition between states."""
    transition_id: str
    source: str
    target: str
    trigger: str
    guard: Optional[Callable[[Dict[str, Any]], bool]] = None
    action: Optional[Callable[[Dict[str, Any]], None]] = None
    priority: int = 0


@dataclass
class TransitionResult:
    """Result of a transition attempt."""
    success: bool
    from_state: str
    to_state: Optional[str] = None
    trigger: str = ""
    message: str = ""


class ConversationFSM:
    """Finite state machine for conversation flow."""

    def __init__(self, fsm_id: str = ""):
        self.fsm_id = fsm_id or str(uuid.uuid4())[:8]
        self._states: Dict[str, ConversationState] = {}
        self._transitions: List[StateTransition] = []
        self._adj: Dict[str, List[StateTransition]] = {}
        self._current: Optional[str] = None
        self._history: List[Tuple[str, str, float]] = []  # (from, to, timestamp)
        self._context: Dict[str, Any] = {}
        self._entry_time: float = 0.0

    def add_state(self, state: ConversationState) -> None:
        self._states[state.state_id] = state
        if state.state_type == StateType.INITIAL and not self._current:
            self._current = state.state_id

    def add_transition(self, transition: StateTransition) -> None:
        self._transitions.append(transition)
        self._adj.setdefault(transition.source, []).append(transition)
        # Sort by priority
        self._adj[transition.source].sort(key=lambda t: t.priority, reverse=True)

    def trigger(self, event: str, context: Optional[Dict[str, Any]] = None) -> TransitionResult:
        if context:
            self._context.update(context)
        if not self._current:
            return TransitionResult(False, "", trigger=event, message="No current state")
        # Find matching transition
        candidates = self._adj.get(self._current, [])
        for trans in candidates:
            if trans.trigger == event:
                if trans.guard is None or trans.guard(self._context):
                    return self._do_transition(trans)
        return TransitionResult(False, self._current, trigger=event, message="No valid transition")

    def _do_transition(self, trans: StateTransition) -> TransitionResult:
        old_state = self._states.get(self._current)
        new_state = self._states.get(trans.target)
        if not new_state:
            return TransitionResult(False, self._current, trigger=trans.trigger, message="Target state not found")
        # Exit old state
        if old_state and old_state.on_exit:
            old_state.on_exit(self._context)
        # Run transition action
        if trans.action:
            trans.action(self._context)
        # Enter new state
        self._current = trans.target
        self._entry_time = time.time()
        if new_state.on_enter:
            new_state.on_enter(self._context)
        self._history.append((trans.source, trans.target, time.time()))
        return TransitionResult(True, trans.source, trans.target, trans.trigger, "Transition successful")

    def get_current(self) -> Optional[ConversationState]:
        return self._states.get(self._current) if self._current else None

    def get_available_triggers(self) -> List[str]:
        if not self._current:
            return []
        return [t.trigger for t in self._adj.get(self._current, [])]

    def is_in_terminal(self) -> bool:
        state = self.get_current()
        return state is not None and state.state_type == StateType.TERMINAL

    def check_timeout(self) -> Optional[TransitionResult]:
        state = self.get_current()
        if not state or not state.timeout:
            return None
        if time.time() - self._entry_time >= state.timeout:
            # Look for timeout transition or default
            for t in self._adj.get(self._current, []):
                if t.trigger == "timeout":
                    return self._do_transition(t)
        return None

    def get_history(self) -> List[Tuple[str, str, float]]:
        return self._history

    def get_stats(self) -> Dict[str, Any]:
        return {
            "fsm_id": self.fsm_id,
            "current_state": self._current,
            "states": len(self._states),
            "transitions": len(self._transitions),
            "history_length": len(self._history),
            "terminal": self.is_in_terminal()
        }

    def reset(self) -> None:
        for state in self._states.values():
            if state.state_type == StateType.INITIAL:
                self._current = state.state_id
                self._entry_time = time.time()
                break
        self._history.clear()
        self._context.clear()

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "fsm_id": self.fsm_id,
                "current": self._current,
                "states": {k: {"name": v.name, "type": v.state_type.name} for k, v in self._states.items()},
                "transitions": [{"source": t.source, "target": t.target, "trigger": t.trigger, "priority": t.priority}
                                for t in self._transitions],
                "history": len(self._history)
            }, f, indent=2)


class StateMachineBuilder:
    """Declarative builder for conversation FSMs."""

    def __init__(self, fsm_id: str = ""):
        self.fsm = ConversationFSM(fsm_id)
        self._state_count = 0

    def state(self, name: str, state_type: StateType = StateType.NORMAL,
              on_enter: Optional[Callable] = None, on_exit: Optional[Callable] = None,
              timeout: Optional[float] = None) -> StateMachineBuilder:
        sid = f"s{self._state_count}"
        self._state_count += 1
        self.fsm.add_state(ConversationState(sid, name, state_type, on_enter, on_exit, timeout=timeout))
        return self

    def transition(self, from_state: str, to_state: str, trigger: str,
                   guard: Optional[Callable] = None, action: Optional[Callable] = None) -> StateMachineBuilder:
        # Find state IDs by name
        sid_map = {s.name: s.state_id for s in self.fsm._states.values()}
        tid = str(uuid.uuid4())[:8]
        self.fsm.add_transition(StateTransition(tid, sid_map[from_state], sid_map[to_state], trigger, guard, action))
        return self

    def build(self) -> ConversationFSM:
        return self.fsm


class ConversationManager:
    """High-level conversation orchestration using FSMs."""

    def __init__(self):
        self._fsms: Dict[str, ConversationFSM] = {}
        self._active: Optional[str] = None

    def create_conversation(self, conversation_id: str, fsm: ConversationFSM) -> None:
        self._fsms[conversation_id] = fsm
        if not self._active:
            self._active = conversation_id

    def send_event(self, conversation_id: str, event: str, context: Optional[Dict[str, Any]] = None) -> TransitionResult:
        fsm = self._fsms.get(conversation_id)
        if not fsm:
            return TransitionResult(False, "", trigger=event, message="Conversation not found")
        return fsm.trigger(event, context)

    def get_state(self, conversation_id: str) -> Optional[str]:
        fsm = self._fsms.get(conversation_id)
        if not fsm:
            return None
        state = fsm.get_current()
        return state.name if state else None

    def get_all_states(self) -> Dict[str, str]:
        return {cid: fsm.get_current().name if fsm.get_current() else "none"
                for cid, fsm in self._fsms.items()}

    def get_stats(self) -> Dict[str, Any]:
        return {
            "conversations": len(self._fsms),
            "active": self._active,
            "states": self.get_all_states()
        }


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("CONVERSATION STATE MACHINE DEMO")
    print("=" * 70)

    # 1. Build FSM for a support chatbot
    print("\n[1] Building Support Chatbot FSM")
    builder = StateMachineBuilder("support-bot")
    builder.state("greeting", StateType.INITIAL) \
           .state("collecting_info", StateType.NORMAL) \
           .state("diagnosing", StateType.NORMAL) \
           .state("resolving", StateType.NORMAL) \
           .state("confirming", StateType.NORMAL) \
           .state("closed", StateType.TERMINAL)

    builder.transition("greeting", "collecting_info", "user_greeting") \
           .transition("collecting_info", "diagnosing", "info_complete", lambda ctx: ctx.get("has_info", False)) \
           .transition("diagnosing", "resolving", "diagnosis_found") \
           .transition("resolving", "confirming", "solution_offered") \
           .transition("confirming", "closed", "user_confirmed") \
           .transition("confirming", "resolving", "user_rejected")

    fsm = builder.build()
    print(f"  States: {len(fsm._states)}, Transitions: {len(fsm._transitions)}")
    print(f"  Current: {fsm.get_current().name}")

    # 2. Run conversation
    print("\n[2] Running Conversation")
    result = fsm.trigger("user_greeting")
    print(f"  user_greeting -> {result.to_state}, success={result.success}")
    result = fsm.trigger("info_complete", {"has_info": True})
    print(f"  info_complete -> {result.to_state}, success={result.success}")
    result = fsm.trigger("diagnosis_found")
    print(f"  diagnosis_found -> {result.to_state}")
    result = fsm.trigger("solution_offered")
    print(f"  solution_offered -> {result.to_state}")
    result = fsm.trigger("user_confirmed")
    print(f"  user_confirmed -> {result.to_state}")
    print(f"  Terminal: {fsm.is_in_terminal()}")

    # 3. History
    print(f"\n[3] History")
    for i, (frm, to, ts) in enumerate(fsm.get_history()):
        print(f"  Step {i+1}: {fsm._states[frm].name} -> {fsm._states[to].name}")

    # 4. FSM with actions
    print("\n[4] FSM with Entry/Exit Actions")
    fsm2 = ConversationFSM("action-bot")
    log = []
    fsm2.add_state(ConversationState("idle", "Idle", StateType.INITIAL,
                                      on_enter=lambda ctx: log.append("enter idle")))
    fsm2.add_state(ConversationState("processing", "Processing",
                                      on_enter=lambda ctx: log.append("enter processing"),
                                      on_exit=lambda ctx: log.append("exit processing")))
    fsm2.add_state(ConversationState("done", "Done", StateType.TERMINAL))
    fsm2.add_transition(StateTransition("t1", "idle", "processing", "start"))
    fsm2.add_transition(StateTransition("t2", "processing", "done", "finish"))
    fsm2.trigger("start")
    fsm2.trigger("finish")
    print(f"  Log: {log}")

    # 5. Conversation Manager
    print("\n[5] Conversation Manager")
    mgr = ConversationManager()
    mgr.create_conversation("conv-1", fsm)
    print(f"  Stats: {mgr.get_stats()}")
    print(f"  State of conv-1: {mgr.get_state('conv-1')}")

    # 6. Guard conditions
    print("\n[6] Guard Conditions")
    fsm3 = ConversationFSM("guard-bot")
    fsm3.add_state(ConversationState("start", "Start", StateType.INITIAL))
    fsm3.add_state(ConversationState("premium", "Premium"))
    fsm3.add_state(ConversationState("basic", "Basic"))
    fsm3.add_transition(StateTransition("t1", "start", "premium", "upgrade",
                                         guard=lambda ctx: ctx.get("is_premium", False)))
    fsm3.add_transition(StateTransition("t2", "start", "basic", "continue"))
    fsm3.trigger("upgrade", {"is_premium": False})
    print(f"  Current (premium blocked): {fsm3.get_current().name}")
    fsm3.trigger("continue")
    print(f"  Current (continue): {fsm3.get_current().name}")

    # 7. Export
    print("\n[7] Export")
    fsm.export("/tmp/fsm.json")
    print(f"  Exported to /tmp/fsm.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
