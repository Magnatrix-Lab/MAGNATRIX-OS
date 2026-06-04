"""Semantic Parser - Natural language to structured meaning for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum, auto
import re

class ActionType(Enum):
    CREATE = auto(); READ = auto(); UPDATE = auto(); DELETE = auto()

@dataclass
class SemanticParser:
    patterns: Dict[ActionType, List[str]] = field(default_factory=dict)

    def __post_init__(self):
        if not self.patterns:
            self.patterns = {
                ActionType.CREATE: ["create", "add", "make", "new"],
                ActionType.READ: ["show", "get", "find", "list", "display"],
                ActionType.UPDATE: ["update", "change", "modify", "edit"],
                ActionType.DELETE: ["delete", "remove", "drop", "clear"]
            }

    def parse(self, text: str) -> Dict:
        text_lower = text.lower()
        for action, keywords in self.patterns.items():
            for kw in keywords:
                if kw in text_lower:
                    entity = self._extract_entity(text_lower)
                    return {"action": action.name, "entity": entity, "original": text}
        return {"action": "UNKNOWN", "entity": "", "original": text}

    def _extract_entity(self, text: str) -> str:
        words = text.split()
        for i, w in enumerate(words):
            if w in ["the", "a", "an"] and i + 1 < len(words):
                return words[i + 1]
        return ""

    def stats(self, text: str) -> dict:
        parsed = self.parse(text)
        return {"action": parsed["action"], "entity": parsed["entity"]}

def run():
    sp = SemanticParser()
    for text in ["Create a new user", "Show me the records", "Delete the file"]:
        print(f"'{text}': {sp.parse(text)}")
    print("Stats:", sp.stats("Create a new user"))

if __name__ == "__main__": run()
