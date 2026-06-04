"""Game State Machine — states, transitions, events, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any
from enum import Enum, auto
import time

class GameState(Enum):
    MENU = auto()
    PLAYING = auto()
    PAUSED = auto()
    GAME_OVER = auto()
    LOADING = auto()

@dataclass
class StateTransition:
    from_state: GameState
    to_state: GameState
    event: str
    condition: Optional[Callable] = None

class GameStateMachine:
    def __init__(self, initial_state: GameState = GameState.MENU):
        self.current_state = initial_state
        self.transitions: List[StateTransition] = []
        self.handlers: Dict[GameState, Dict[str, Callable]] = {}
        self.entry_handlers: Dict[GameState, Callable] = {}
        self.exit_handlers: Dict[GameState, Callable] = {}
        self.state_history: List[Tuple[GameState, float]] = []

    def add_transition(self, transition: StateTransition):
        self.transitions.append(transition)

    def on_entry(self, state: GameState, handler: Callable):
        self.entry_handlers[state] = handler

    def on_exit(self, state: GameState, handler: Callable):
        self.exit_handlers[state] = handler

    def handle_event(self, event: str, context: Dict = None) -> bool:
        for t in self.transitions:
            if t.from_state == self.current_state and t.event == event:
                if t.condition is None or t.condition(context):
                    if self.current_state in self.exit_handlers:
                        self.exit_handlers[self.current_state]()
                    self.current_state = t.to_state
                    self.state_history.append((self.current_state, time.time()))
                    if self.current_state in self.entry_handlers:
                        self.entry_handlers[self.current_state]()
                    return True
        return False

    def is_in(self, state: GameState) -> bool:
        return self.current_state == state

    def get_available_events(self) -> List[str]:
        return [t.event for t in self.transitions if t.from_state == self.current_state]

    def stats(self) -> Dict:
        return {"current": self.current_state.name, "transitions": len(self.transitions), "history": len(self.state_history)}

def run():
    fsm = GameStateMachine(GameState.MENU)
    fsm.add_transition(StateTransition(GameState.MENU, GameState.PLAYING, "start"))
    fsm.add_transition(StateTransition(GameState.PLAYING, GameState.PAUSED, "pause"))
    fsm.add_transition(StateTransition(GameState.PAUSED, GameState.PLAYING, "resume"))
    fsm.add_transition(StateTransition(GameState.PLAYING, GameState.GAME_OVER, "die"))
    fsm.add_transition(StateTransition(GameState.GAME_OVER, GameState.MENU, "restart"))
    fsm.handle_event("start")
    print(fsm.current_state.name)
    fsm.handle_event("pause")
    print(fsm.current_state.name)
    fsm.handle_event("resume")
    print(fsm.current_state.name)
    print(fsm.stats())

if __name__ == "__main__":
    run()
