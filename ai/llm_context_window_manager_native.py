"""LLM Context Window Manager — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

class ContextWindowManager:
    def __init__(self, max_tokens: int = 4096) -> None:
        self.max_tokens = max_tokens
        self._segments: List[str] = []
        self._priority: List[int] = []

    def add_segment(self, text: str, priority: int = 5) -> None:
        self._segments.append(text)
        self._priority.append(priority)

    def estimate_tokens(self, text: str) -> int:
        return len(text.split())

    def build_context(self) -> str:
        total = 0
        selected = []
        indexed = list(enumerate(self._segments))
        indexed.sort(key=lambda x: self._priority[x[0]], reverse=True)
        for idx, text in indexed:
            tokens = self.estimate_tokens(text)
            if total + tokens <= self.max_tokens:
                selected.append((idx, text))
                total += tokens
        selected.sort(key=lambda x: x[0])
        return "\n".join(text for _, text in selected)

    def get_stats(self) -> Dict[str, Any]:
        total = sum(self.estimate_tokens(s) for s in self._segments)
        return {"segments": len(self._segments), "total_tokens": total, "max_tokens": self.max_tokens, "overflow": total > self.max_tokens}

def run() -> None:
    print("Context Window Manager test")
    e = ContextWindowManager(max_tokens=20)
    e.add_segment("System prompt: Be helpful.", priority=10)
    e.add_segment("User: Hello", priority=8)
    e.add_segment("Assistant: Hi there", priority=7)
    e.add_segment("User: Tell me about quantum physics in detail.", priority=5)
    e.add_segment("Assistant: Quantum physics is the study...", priority=5)
    ctx = e.build_context()
    print("  Built context:")
    print(ctx)
    print("  Stats: " + str(e.get_stats()))
    print("Context Window Manager test complete.")

if __name__ == "__main__":
    run()
