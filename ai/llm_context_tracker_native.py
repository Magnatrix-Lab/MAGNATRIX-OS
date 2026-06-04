"""Context Tracker - Conversation context tracking for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
from collections import deque

@dataclass
class ContextTracker:
    max_history: int = 10
    history: deque = field(default_factory=lambda: deque(maxlen=10))
    entities: Dict[str, str] = field(default_factory=dict)
    
    def add_turn(self, speaker: str, text: str) -> None:
        self.history.append({"speaker": speaker, "text": text, "timestamp": time.time()})
        # Extract simple entities
        import re
        words = re.findall(r"[A-Z][a-zA-Z]+", text)
        for word in words:
            if word not in self.entities:
                self.entities[word] = speaker
    
    def get_last_n(self, n: int = 3) -> List[Dict]:
        return list(self.history)[-n:]
    
    def get_entities(self) -> Dict[str, str]:
        return self.entities
    
    def stats(self) -> dict:
        return {"turns": len(self.history), "entities": len(self.entities), "max_history": self.max_history}

def run():
    import time
    ct = ContextTracker(5)
    ct.add_turn("user", "I like New York")
    ct.add_turn("bot", "New York is great")
    ct.add_turn("user", "Tell me about Paris")
    print("Last 2 turns:", ct.get_last_n(2))
    print("Entities:", ct.get_entities())
    print("Stats:", ct.stats())

if __name__ == "__main__": run()
