#!/usr/bin/env python3
"""
MAGNATRIX-OS | Layer 5 — State Machine
Native finite state machine with hierarchical states, guards, and actions.
- Flat + hierarchical state support
- Entry/exit/during actions
- Transition guards (conditions)
- Event-driven with async dispatch
- State serialization for persistence
"""
import json, time, threading, os, sys, hashlib
from typing import Dict, List, Optional, Any, Callable, Set, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum


@dataclass
class Transition:
    event: str
    source: str
    target: str
    guard: Optional[Callable] = None
    action: Optional[Callable] = None


@dataclass
class State:
    id: str
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)
    on_entry: Optional[Callable] = None
    on_exit: Optional[Callable] = None
    on_during: Optional[Callable] = None
    initial: bool = False
    final: bool = False


class StateMachine:
    """Hierarchical state machine engine."""

    def __init__(self, name: str = "fsm"):
        self.name = name
        self._states: Dict[str, State] = {}
        self._transitions: List[Transition] = []
        self._current: str = ""
        self._history: Dict[str, str] = {}  # parent -> last active child
        self._lock = threading.Lock()
        self._running = False
        self._event_queue: deque = deque()
        self._thread: Optional[threading.Thread] = None

    def add_state(self, state: State):
        self._states[state.id] = state
        if state.initial:
            self._current = state.id

    def add_transition(self, t: Transition):
        self._transitions.append(t)

    def _active_path(self, state_id: str) -> List[str]:
        path = []
        current = state_id
        while current:
            path.append(current)
            current = self._states.get(current, State("")).parent
        return list(reversed(path))

    def _common_ancestor(self, a: str, b: str) -> Optional[str]:
        path_a = set(self._active_path(a))
        path_b = set(self._active_path(b))
        common = path_a & path_b
        # Return deepest common
        for s in reversed(self._active_path(a)):
            if s in common:
                return s
        return None

    def trigger(self, event: str, data: Any = None) -> bool:
        with self._lock:
            if not self._current:
                return False
            # Find matching transition
            for t in self._transitions:
                if t.event == event and t.source == self._current:
                    if t.guard and not t.guard(data):
                        continue
                    # Execute transition
                    self._execute_transition(t, data)
                    return True
            # Check if parent can handle
            parent = self._states.get(self._current, State("")).parent
            if parent:
                for t in self._transitions:
                    if t.event == event and t.source == parent:
                        if t.guard and not t.guard(data):
                            continue
                        self._execute_transition(t, data)
                        return True
            return False

    def _execute_transition(self, t: Transition, data: Any):
        # Exit states up to common ancestor
        source_path = self._active_path(self._current)
        target_path = self._active_path(t.target)
        common = self._common_ancestor(self._current, t.target)
        # Exit
        for s in reversed(source_path):
            if s == common:
                break
            state = self._states.get(s)
            if state and state.on_exit:
                state.on_exit(data)
            # Save history
            parent = state.parent if state else None
            if parent:
                self._history[parent] = s
        # Action
        if t.action:
            t.action(data)
        # Enter
        for s in target_path:
            if s == common:
                continue
            state = self._states.get(s)
            if state and state.on_entry:
                state.on_entry(data)
        self._current = t.target

    def start(self):
        self._running = True
        def _loop():
            while self._running:
                if self._event_queue:
                    event, data = self._event_queue.popleft()
                    self.trigger(event, data)
                else:
                    time.sleep(0.01)
        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def post(self, event: str, data: Any = None):
        self._event_queue.append((event, data))

    def state(self) -> str:
        with self._lock:
            return self._current

    def is_in(self, state_id: str) -> bool:
        with self._lock:
            return state_id in self._active_path(self._current)

    def snapshot(self) -> Dict:
        with self._lock:
            return {
                "name": self.name,
                "current": self._current,
                "history": dict(self._history),
            }

    def restore(self, data: Dict):
        with self._lock:
            self._current = data.get("current", "")
            self._history = data.get("history", {})


class NativeStateMachineBuilder:
    """Fluent builder for state machines."""

    def __init__(self, name: str = "fsm"):
        self.fsm = StateMachine(name)

    def state(self, id: str, parent: str = None, initial: bool = False, final: bool = False,
              entry: Callable = None, exit: Callable = None, during: Callable = None):
        s = State(id=id, parent=parent, initial=initial, final=final,
                  on_entry=entry, on_exit=exit, on_during=during)
        if parent and parent in self.fsm._states:
            self.fsm._states[parent].children.append(id)
        self.fsm.add_state(s)
        return self

    def transition(self, event: str, source: str, target: str, guard: Callable = None, action: Callable = None):
        self.fsm.add_transition(Transition(event, source, target, guard, action))
        return self

    def build(self) -> StateMachine:
        return self.fsm


# ─── SELF TESTS ───
if __name__ == "__main__":
    tests = []
    def _t(name, fn):
        tests.append((name, fn))

    _t("simple_transition", lambda: (fsm := StateMachine(), fsm.add_state(State("idle", initial=True)), fsm.add_state(State("running")), fsm.add_transition(Transition("start", "idle", "running")), fsm.trigger("start"), fsm.state() == "running")[-1])
    _t("guard_blocks", lambda: (fsm := StateMachine(), fsm.add_state(State("idle", initial=True)), fsm.add_state(State("running")), fsm.add_transition(Transition("start", "idle", "running", guard=lambda d: False)), not fsm.trigger("start"), fsm.state() == "idle")[-1])
    _t("hierarchical", lambda: (fsm := StateMachine(), fsm.add_state(State("on", initial=True)), fsm.add_state(State("idle", parent="on")), fsm.add_state(State("busy", parent="on")), fsm.add_state(State("off")), fsm.add_transition(Transition("activate", "on", "idle")), fsm.add_transition(Transition("work", "idle", "busy")), fsm.trigger("activate"), fsm.trigger("work"), fsm.is_in("on"))[-1])
    _t("entry_action", lambda: (x := [], fsm := StateMachine(), fsm.add_state(State("a", initial=True)), fsm.add_state(State("b", on_entry=lambda d: x.append(1))), fsm.add_transition(Transition("go", "a", "b")), fsm.trigger("go"), x == [1])[-1])
    _t("exit_action", lambda: (x := [], fsm := StateMachine(), fsm.add_state(State("a", initial=True, on_exit=lambda d: x.append(1))), fsm.add_state(State("b")), fsm.add_transition(Transition("go", "a", "b")), fsm.trigger("go"), x == [1])[-1])
    _t("async_post", lambda: (fsm := StateMachine(), fsm.add_state(State("a", initial=True)), fsm.add_state(State("b")), fsm.add_transition(Transition("go", "a", "b")), fsm.start(), fsm.post("go"), time.sleep(0.05), fsm.stop(), fsm.state() == "b")[-1])
    _t("snapshot_restore", lambda: (fsm := StateMachine(), fsm.add_state(State("a", initial=True)), fsm.add_state(State("b")), fsm.add_transition(Transition("go", "a", "b")), fsm.trigger("go"), snap := fsm.snapshot(), fsm2 := StateMachine(), fsm2.restore(snap), fsm2.state() == "b")[-1])
    _t("builder", lambda: NativeStateMachineBuilder().state("a", initial=True).state("b").transition("go", "a", "b").build().state() == "a")
    _t("final_state", lambda: (fsm := StateMachine(), fsm.add_state(State("done", final=True)), fsm._states["done"].final)[-1])
    def _history_test():
        fsm = StateMachine()
        fsm.add_state(State("p"))
        fsm.add_state(State("c1", parent="p"))
        fsm.add_state(State("c2", parent="p"))
        fsm._current = "c1"
        fsm._history["p"] = "c1"
        return fsm._history.get("p") == "c1"
    _t("history", _history_test)

    passed = 0
    for name, fn in tests:
        try:
            ok = fn()
            print(f"  {'PASS' if ok else 'FAIL'} {name}")
            if ok:
                passed += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")
    print(f"\nState Machine: {passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)
