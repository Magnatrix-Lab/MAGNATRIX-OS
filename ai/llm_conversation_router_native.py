"""
llm_conversation_router_native.py
MAGNATRIX-OS Conversation Router Engine
Native Python, stdlib only.
Provides conversation routing with topic switching, handoff detection, and branch management.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class ConversationBranch:
    branch_id: str
    parent_id: Optional[str]
    topic: str
    messages: List[str] = field(default_factory=list)

class ConversationRouterEngine:
    def __init__(self) -> None:
        self._branches: Dict[str, ConversationBranch] = {}
        self._current_branch: Optional[str] = None
        self._topics: List[str] = []

    def create_branch(self, branch_id: str, topic: str, parent_id: Optional[str] = None) -> ConversationBranch:
        branch = ConversationBranch(branch_id, parent_id, topic)
        self._branches[branch_id] = branch
        self._current_branch = branch_id
        self._topics.append(topic)
        return branch

    def add_message(self, message: str, branch_id: Optional[str] = None) -> None:
        bid = branch_id or self._current_branch
        if bid and bid in self._branches:
            self._branches[bid].messages.append(message)

    def switch_branch(self, branch_id: str) -> bool:
        if branch_id in self._branches:
            self._current_branch = branch_id
            return True
        return False

    def detect_topic_switch(self, current_topic: str, new_message: str) -> bool:
        # Simple heuristic: check if message contains words from current topic
        topic_words = set(current_topic.lower().split())
        message_words = set(new_message.lower().split())
        overlap = len(topic_words & message_words)
        return overlap == 0 and len(topic_words) > 0

    def get_branch_history(self, branch_id: str) -> List[str]:
        branch = self._branches.get(branch_id)
        return branch.messages if branch else []

    def get_stats(self) -> Dict[str, Any]:
        return {"branches": len(self._branches), "topics": len(set(self._topics)), "current": self._current_branch}

def run() -> None:
    print("=" * 60); print("MAGNATRIX-OS Conversation Router"); print("=" * 60)
    e = ConversationRouterEngine()
    e.create_branch("b1", "python programming")
    e.add_message("How do I use decorators?")
    e.add_message("What about list comprehensions?")
    print(f"  Detect switch: {e.detect_topic_switch('python programming', 'The weather is nice today')}")
    e.create_branch("b2", "weather", parent_id="b1")
    e.add_message("It is sunny today", branch_id="b2")
    print(f"  Stats: {e.get_stats()}")
    print(f"  b1 history: {e.get_branch_history('b1')}")
    print("\nConversation Router test complete.")
if __name__ == "__main__": run()
