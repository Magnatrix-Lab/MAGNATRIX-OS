"""LLM Few-Shot Manager — Native Python (stdlib only)."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum, auto

class ExampleCategory(Enum):
    GENERAL = auto()
    TECHNICAL = auto()
    CREATIVE = auto()
    ANALYTICAL = auto()

@dataclass
class FewShotExample:
    id: str
    input_text: str
    output_text: str
    category: ExampleCategory = ExampleCategory.GENERAL
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class FewShotManager:
    def __init__(self, max_examples: int = 100) -> None:
        self.max_examples = max_examples
        self._examples: List[FewShotExample] = []
        self._index: Dict[str, int] = {}

    def add(self, example: FewShotExample) -> None:
        if example.id in self._index:
            self._examples[self._index[example.id]] = example
        else:
            if len(self._examples) >= self.max_examples:
                removed = self._examples.pop(0)
                del self._index[removed.id]
                self._rebuild_index()
            self._index[example.id] = len(self._examples)
            self._examples.append(example)

    def _rebuild_index(self) -> None:
        self._index = {ex.id: i for i, ex in enumerate(self._examples)}

    def get(self, example_id: str) -> Optional[FewShotExample]:
        idx = self._index.get(example_id)
        return self._examples[idx] if idx is not None else None

    def select(self, query: str, top_k: int = 3, scorer: Optional[Callable[[str, FewShotExample], float]] = None) -> List[FewShotExample]:
        if scorer is None:
            scorer = self._default_scorer
        scored = [(scorer(query, ex), ex) for ex in self._examples]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [ex for _, ex in scored[:top_k]]

    def _default_scorer(self, query: str, example: FewShotExample) -> float:
        q_words = set(query.lower().split())
        in_words = set(example.input_text.lower().split())
        if not q_words:
            return 0.0
        overlap = len(q_words & in_words)
        return overlap / len(q_words)

    def to_prompt(self, examples: List[FewShotExample]) -> str:
        parts = ["Examples:"]
        for ex in examples:
            parts.append(f"  Input: {ex.input_text}")
            parts.append(f"  Output: {ex.output_text}")
            parts.append("")
        return "\n".join(parts)

    def get_stats(self) -> Dict[str, Any]:
        return {"total": len(self._examples), "by_category": {cat.name: sum(1 for ex in self._examples if ex.category == cat) for cat in ExampleCategory}}

    def save(self, path: str) -> None:
        data = [{"id": ex.id, "input": ex.input_text, "output": ex.output_text, "category": ex.category.name, "score": ex.score, "metadata": ex.metadata} for ex in self._examples]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._examples = []
        self._index = {}
        for item in data:
            ex = FewShotExample(
                id=item["id"],
                input_text=item["input"],
                output_text=item["output"],
                category=ExampleCategory[item.get("category", "GENERAL")],
                score=item.get("score", 0.0),
                metadata=item.get("metadata", {})
            )
            self.add(ex)

def run() -> None:
    print("Few-Shot Manager test")
    mgr = FewShotManager(max_examples=50)
    mgr.add(FewShotExample("e1", "Translate hello to French", "Bonjour", ExampleCategory.GENERAL, 0.9))
    mgr.add(FewShotExample("e2", "Explain quantum computing", "Quantum computing uses qubits...", ExampleCategory.TECHNICAL, 0.85))
    mgr.add(FewShotExample("e3", "Write a haiku", "Ancient silent pond...", ExampleCategory.CREATIVE, 0.8))
    selected = mgr.select("Translate a greeting", top_k=2)
    print("  Selected: " + str([ex.id for ex in selected]))
    print("  Stats: " + str(mgr.get_stats()))
    print("Few-Shot Manager test complete.")

if __name__ == "__main__":
    run()
