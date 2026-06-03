"""
llm_state_machine_native.py
MAGNATRIX-OS State Machine Engine
Native Python, stdlib only.
Provides finite state machine with transitions, guards, entry/exit actions, and nested states.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set


@dataclass
class Transition:
    source: str
    target: str
    event: str
    guard: Optional[Callable[[Any], bool]] = None
    action: Optional[Callable[[Any], None]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"source": self.source, "target": self.target, "event": self.event}


@dataclass
class State:
    name: str
    on_entry: Optional[Callable[[Any], None]] = None
    on_exit: Optional[Callable[[Any], None]] = None
    is_final: bool = False
    submachine: Optional[StateMachineEngine] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "is_final": self.is_final, "has_submachine": self.submachine is not None}


class StateMachineEngine:
    """Finite state machine with transitions and guards."""

    def __init__(self, name: str, initial_state: str) -> None:
        self.name = name
        self._states: Dict[str, State] = {}
        self._transitions: Dict[str, List[Transition]] = {}  # source -> transitions
        self._current_state = initial_state
        self._initial_state = initial_state
        self._history: List[Dict[str, Any]] = []
        self._context: Any = None

    def add_state(self, state: State) -> None:
        self._states[state.name] = state

    def add_transition(self, transition: Transition) -> None:
        self._transitions.setdefault(transition.source, []).append(transition)

    def transition(self, event: str, data: Any = None) -> bool:
        transitions = self._transitions.get(self._current_state, [])
        for t in transitions:
            if t.event == event:
                if t.guard and not t.guard(data):
                    continue
                # Exit current state
                current = self._states.get(self._current_state)
                if current and current.on_exit:
                    current.on_exit(data)
                # Execute action
                if t.action:
                    t.action(data)
                # Enter new state
                self._current_state = t.target
                self._history.append({"from": t.source, "to": t.target, "event": event})
                new_state = self._states.get(t.target)
                if new_state and new_state.on_entry:
                    new_state.on_entry(data)
                return True
        return False

    @property
    def current_state(self) -> str:
        return self._current_state

    def is_in(self, state: str) -> bool:
        return self._current_state == state

    def can_handle(self, event: str) -> bool:
        transitions = self._transitions.get(self._current_state, [])
        return any(t.event == event for t in transitions)

    def get_available_events(self) -> List[str]:
        transitions = self._transitions.get(self._current_state, [])
        return [t.event for t in transitions]

    def reset(self) -> None:
        self._current_state = self._initial_state
        self._history.clear()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "name": self.name, "current_state": self._current_state,
            "states": len(self._states), "transitions": sum(len(t) for t in self._transitions.values()),
            "history": len(self._history),
        }


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS State Machine Engine")
    print("=" * 60)

    # Build a conversation state machine
    sm = StateMachineEngine("conversation", "idle")

    sm.add_state(State("idle"))
    sm.add_state(State("listening"))
    sm.add_state(State("processing"))
    sm.add_state(State("responding"))
    sm.add_state(State("completed", is_final=True))

    sm.add_transition(Transition("idle", "listening", "start"))
    sm.add_transition(Transition("listening", "processing", "input_received"))
    sm.add_transition(Transition("processing", "responding", "output_ready"))
    sm.add_transition(Transition("responding", "listening", "response_sent"))
    sm.add_transition(Transition("listening", "completed", "end"))

    print(f"\n--- Initial state: {sm.current_state} ---")
    print(f"  Available events: {sm.get_available_events()}")

    print("\n--- Transitions ---")
    for event in ["start", "input_received", "output_ready", "response_sent", "input_received", "end"]:
        ok = sm.transition(event)
        print(f"  {event}: {'OK' if ok else 'FAIL'} -> state={sm.current_state}")

    print("\n--- Stats ---")
    print(sm.get_stats())

    print("\nState Machine test complete.")


if __name__ == "__main__":
    run()
