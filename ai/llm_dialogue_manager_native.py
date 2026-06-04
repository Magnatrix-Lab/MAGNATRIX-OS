"""Dialogue Manager - Conversation state tracking for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto

class DialogueState(Enum):
    GREETING = auto(); INQUIRY = auto(); RESPONSE = auto(); CLOSING = auto()

@dataclass
class DialogueManager:
    state: DialogueState = DialogueState.GREETING
    history: List[Tuple[str, str]] = field(default_factory=list)
    context: Dict[str, str] = field(default_factory=dict)
    
    def user_input(self, text: str) -> str:
        self.history.append(("user", text))
        if self.state == DialogueState.GREETING:
            self.state = DialogueState.INQUIRY
            return "Hello! How can I help you?"
        elif self.state == DialogueState.INQUIRY:
            self.context["last_query"] = text
            self.state = DialogueState.RESPONSE
            return f"I understand you said: {text}. Let me think..."
        elif self.state == DialogueState.RESPONSE:
            self.state = DialogueState.CLOSING
            return "Is there anything else?"
        else:
            return "Goodbye!"
    
    def stats(self) -> dict:
        return {"state": self.state.name, "turns": len(self.history), "context": len(self.context)}

def run():
    dm = DialogueManager()
    for inp in ["hello", "I need help", "thanks", "bye"]:
        print(f"User: {inp} -> Bot: {dm.user_input(inp)}")
    print("Stats:", dm.stats())

if __name__ == "__main__": run()
