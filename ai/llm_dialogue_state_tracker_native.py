"""Dialogue State Tracker - Multi-turn state tracking for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class DialogueStateTracker:
    turns: List[Dict] = field(default_factory=list)
    state: Dict[str, any] = field(default_factory=dict)

    def add_turn(self, user_utterance: str, system_response: str = "", slots: Dict = None) -> None:
        self.turns.append({"user": user_utterance, "system": system_response, "slots": slots or {}})
        if slots:
            for k, v in slots.items():
                if v is not None:
                    self.state[k] = v

    def get_missing_slots(self, required: List[str]) -> List[str]:
        return [s for s in required if s not in self.state or self.state[s] is None]

    def reset(self) -> None:
        self.turns = []
        self.state = {}

    def stats(self) -> dict:
        return {"turns": len(self.turns), "state": self.state, "missing": self.get_missing_slots([])}

def run():
    dst = DialogueStateTracker()
    dst.add_turn("I want a flight", "", {"destination": None, "date": None})
    dst.add_turn("to London", "", {"destination": "London"})
    dst.add_turn("on March 15", "", {"date": "March 15"})
    print("State:", dst.state)
    print("Stats:", dst.stats())

if __name__ == "__main__": run()
