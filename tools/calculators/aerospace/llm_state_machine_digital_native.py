"""Digital State Machine — FSM, state transitions, Moore/Mealy, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum, auto

class FSMType(Enum):
    MOORE = auto()
    MEALY = auto()

class DigitalStateMachine:
    def __init__(self, fsm_type: FSMType = FSMType.MOORE):
        self.fsm_type = fsm_type
        self.states: Dict[str, Dict] = {}
        self.current_state: str = ""
        self.transitions: List[Dict] = []
        self.outputs: List[str] = []

    def add_state(self, state_id: str, output: str = "", transitions: Dict = None):
        self.states[state_id] = {"output": output, "transitions": transitions or {}}

    def set_initial(self, state_id: str):
        self.current_state = state_id

    def step(self, input_val: str) -> str:
        state = self.states.get(self.current_state)
        if not state:
            return ""
        next_state = state["transitions"].get(input_val, self.current_state)
        self.transitions.append({"from": self.current_state, "input": input_val, "to": next_state})
        self.current_state = next_state
        if self.fsm_type == FSMType.MOORE:
            output = self.states.get(next_state, {}).get("output", "")
        else:
            output = state["transitions"].get(f"{input_val}_out", "")
        self.outputs.append(output)
        return output

    def run(self, inputs: List[str]) -> List[str]:
        return [self.step(i) for i in inputs]

    def stats(self) -> Dict:
        return {"states": len(self.states), "current": self.current_state, "transitions": len(self.transitions)}

def run():
    fsm = DigitalStateMachine(FSMType.MOORE)
    fsm.add_state("S0", "00", {"0": "S0", "1": "S1"})
    fsm.add_state("S1", "01", {"0": "S0", "1": "S2"})
    fsm.add_state("S2", "10", {"0": "S1", "1": "S2"})
    fsm.set_initial("S0")
    print(fsm.run(["1", "1", "0", "1"]))
    print(fsm.stats())

if __name__ == "__main__":
    run()
