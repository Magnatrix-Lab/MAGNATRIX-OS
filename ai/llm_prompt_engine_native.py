"""Prompt Template Engine — Advanced prompt engineering, versioning, optimization.

Modul ini menyediakan:
- TemplateRegistry dengan variable substitution dan conditional blocks
- Prompt versioning dengan history tracking
- Few-shot example manager dengan similarity selection
- Chain-of-thought template builder
- Prompt optimizer dengan auto-format detection
"""

from __future__ import annotations

import json
import time
import uuid
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class PromptFormat(Enum):
    RAW = auto()
    CHAT = auto()
    INSTRUCT = auto()
    FEW_SHOT = auto()
    CHAIN_OF_THOUGHT = auto()
    SYSTEM_USER = auto()


@dataclass
class PromptTemplate:
    """Template definisi dengan metadata."""
    template_id: str
    name: str
    template_str: str
    format: PromptFormat = PromptFormat.RAW
    variables: List[str] = field(default_factory=list)
    version: str = "1.0"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    usage_count: int = 0

    def __post_init__(self):
        if not self.variables:
            self.variables = self._extract_vars()

    def _extract_vars(self) -> List[str]:
        pattern = re.compile(r'\{\{(\w+)\}\}')
        return list(dict.fromkeys(pattern.findall(self.template_str)))

    def render(self, **kwargs: Any) -> str:
        result = self.template_str
        for var in self.variables:
            val = kwargs.get(var, f"{{{{{var}}}}}")
            result = result.replace(f"{{{{{var}}}}}", str(val))
        self.usage_count += 1
        return result


@dataclass
class PromptVersion:
    """Single version entry dalam history."""
    version: str
    template_str: str
    changed_at: float
    change_note: str = ""


@dataclass
class FewShotExample:
    """Single few-shot example pair."""
    example_id: str
    input_text: str
    output_text: str
    score: float = 1.0
    tags: List[str] = field(default_factory=list)


class TemplateRegistry:
    """Register dan manage prompt templates."""

    def __init__(self):
        self._templates: Dict[str, PromptTemplate] = {}
        self._history: Dict[str, List[PromptVersion]] = {}

    def register(self, template: PromptTemplate) -> PromptTemplate:
        self._templates[template.template_id] = template
        self._history.setdefault(template.template_id, [])
        self._history[template.template_id].append(PromptVersion(
            version=template.version,
            template_str=template.template_str,
            changed_at=template.created_at,
            change_note="Initial"
        ))
        return template

    def get(self, template_id: str) -> Optional[PromptTemplate]:
        return self._templates.get(template_id)

    def update(self, template_id: str, new_str: str, change_note: str = "") -> Optional[PromptTemplate]:
        t = self._templates.get(template_id)
        if not t:
            return None
        new_ver = str(float(t.version) + 0.1)
        t.template_str = new_str
        t.version = new_ver
        t.variables = t._extract_vars()
        self._history[template_id].append(PromptVersion(
            version=new_ver, template_str=new_str, changed_at=time.time(), change_note=change_note
        ))
        return t

    def rollback(self, template_id: str, version: str) -> Optional[PromptTemplate]:
        t = self._templates.get(template_id)
        if not t:
            return None
        for v in self._history.get(template_id, []):
            if v.version == version:
                t.template_str = v.template_str
                t.version = v.version
                t.variables = t._extract_vars()
                return t
        return None

    def list_all(self) -> List[PromptTemplate]:
        return list(self._templates.values())

    def search_by_tag(self, tag: str) -> List[PromptTemplate]:
        return [t for t in self._templates.values() if tag in t.tags]

    def export(self, path: str) -> None:
        data = {
            tid: {
                "template_id": t.template_id, "name": t.name, "template_str": t.template_str,
                "format": t.format.name, "variables": t.variables, "version": t.version,
                "tags": t.tags, "metadata": t.metadata, "usage_count": t.usage_count
            }
            for tid, t in self._templates.items()
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


class FewShotManager:
    """Manage few-shot examples dengan similarity-based selection."""

    def __init__(self, max_examples: int = 5):
        self.max_examples = max_examples
        self._examples: List[FewShotExample] = []

    def add(self, input_text: str, output_text: str, tags: Optional[List[str]] = None, score: float = 1.0) -> FewShotExample:
        ex = FewShotExample(
            example_id=str(uuid.uuid4())[:8],
            input_text=input_text,
            output_text=output_text,
            score=score,
            tags=tags or []
        )
        self._examples.append(ex)
        return ex

    def _similarity(self, a: str, b: str) -> float:
        # Simple Jaccard similarity on words
        sa, sb = set(a.lower().split()), set(b.lower().split())
        if not sa or not sb:
            return 0.0
        return len(sa & sb) / len(sa | sb)

    def select(self, query: str, n: Optional[int] = None, tag: Optional[str] = None) -> List[FewShotExample]:
        candidates = self._examples
        if tag:
            candidates = [e for e in candidates if tag in e.tags]
        scored = [(self._similarity(query, e.input_text) * e.score, e) for e in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)
        n = n or self.max_examples
        return [e for _, e in scored[:n]]

    def build_prompt(self, query: str, template: str = "Input: {input}\nOutput: {output}", n: Optional[int] = None) -> str:
        selected = self.select(query, n)
        parts = []
        for ex in selected:
            parts.append(template.replace("{input}", ex.input_text).replace("{output}", ex.output_text))
        return "\n\n".join(parts)

    def get_stats(self) -> Dict[str, Any]:
        return {"total_examples": len(self._examples), "tags": list(set(t for e in self._examples for t in e.tags))}


class ChainOfThoughtBuilder:
    """Build chain-of-thought prompts dengan reasoning steps."""

    def __init__(self):
        self._steps: List[str] = []
        self._separator: str = "\n\n"

    def add_step(self, instruction: str, reasoning_template: str = "Let's think step by step.") -> ChainOfThoughtBuilder:
        self._steps.append(f"{instruction}\n{reasoning_template}")
        return self

    def build(self, final_question: str) -> str:
        parts = self._steps + [f"Now, answer this:\n{final_question}"]
        return self._separator.join(parts)

    def build_with_examples(self, examples: List[Tuple[str, str, str]], final_question: str) -> str:
        """examples: (question, reasoning, answer)"""
        parts = []
        for q, r, a in examples:
            parts.append(f"Q: {q}\nReasoning: {r}\nA: {a}")
        parts.append(f"Q: {final_question}\nReasoning: Let's think step by step.")
        return self._separator.join(parts)


class PromptOptimizer:
    """Auto-detect format dan optimize prompt structure."""

    def detect_format(self, text: str) -> PromptFormat:
        if re.search(r'^(system|user|assistant):', text, re.MULTILINE | re.IGNORECASE):
            return PromptFormat.SYSTEM_USER
        if "Q:" in text and "A:" in text:
            return PromptFormat.FEW_SHOT
        if "Let's think step by step" in text or "Reasoning:" in text:
            return PromptFormat.CHAIN_OF_THOUGHT
        if text.startswith("### Instruction:") or text.startswith("<|im_start|>"):
            return PromptFormat.INSTRUCT
        return PromptFormat.RAW

    def optimize(self, text: str) -> str:
        fmt = self.detect_format(text)
        if fmt == PromptFormat.RAW:
            # Add structure if missing
            if len(text) > 200 and "\n" not in text[:200]:
                text = text.replace(". ", ".\n", 1)
        return text.strip()

    def estimate_tokens(self, text: str) -> int:
        # Simple estimation: ~4 chars per token for English
        return len(text) // 4 + 1


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("PROMPT TEMPLATE ENGINE DEMO")
    print("=" * 70)

    # 1. Template Registry
    print("\n[1] Template Registry")
    registry = TemplateRegistry()
    t1 = PromptTemplate(
        template_id="summarize-v1",
        name="Summarize Text",
        template_str="Summarize the following text in {{max_words}} words:\n\n{{text}}",
        format=PromptFormat.INSTRUCT,
        tags=["summarization", "nlp"]
    )
    registry.register(t1)
    print(f"  Registered: {t1.name} (vars: {t1.variables})")
    rendered = t1.render(max_words=50, text="The quick brown fox jumps over the lazy dog. This is a classic pangram.")
    print(f"  Rendered: {rendered[:80]}...")

    # Update dan rollback
    registry.update("summarize-v1", "Summarize:\n{{text}}\n(max {{max_words}} words)", "Simplified")
    print(f"  Updated to v{t1.version}")
    registry.rollback("summarize-v1", "1.0")
    print(f"  Rolled back to v{t1.version}")

    # 2. Few-Shot Manager
    print("\n[2] Few-Shot Manager")
    fsm = FewShotManager(max_examples=3)
    fsm.add("What is 2+2?", "4", tags=["math"])
    fsm.add("What is 5*3?", "15", tags=["math"])
    fsm.add("What is 10-7?", "3", tags=["math"])
    fsm.add("What is the capital of France?", "Paris", tags=["geography"])
    prompt = fsm.build_prompt("What is 8/2?", n=2)
    print(f"  Few-shot prompt:\n{prompt}")

    # 3. Chain of Thought
    print("\n[3] Chain of Thought Builder")
    cot = ChainOfThoughtBuilder()
    cot.add_step("First, identify the key numbers in the problem.")
    cot.add_step("Next, determine the operation needed.")
    cot.add_step("Finally, calculate the result.")
    full = cot.build("If a train travels 60 km/h for 2.5 hours, how far does it go?")
    print(f"  CoT prompt:\n{full}")

    # CoT with examples
    cot2 = ChainOfThoughtBuilder()
    cot_prompt = cot2.build_with_examples([
        ("2+3", "I need to add 2 and 3. 2+3=5", "5"),
        ("10-4", "I need to subtract 4 from 10. 10-4=6", "6"),
    ], "7*8")
    print(f"  CoT with examples:\n{cot_prompt}")

    # 4. Prompt Optimizer
    print("\n[4] Prompt Optimizer")
    opt = PromptOptimizer()
    texts = [
        "system: You are helpful\nuser: Hello",
        "Q: What is 2+2? A: 4\nQ: What is 3+3?",
        "Let's think step by step. What is the meaning of life?",
        "Just a plain raw text without any formatting applied here",
    ]
    for text in texts:
        fmt = opt.detect_format(text)
        print(f"  Detected: {fmt.name} for '{text[:40]}...'")

    # 5. Export
    print("\n[5] Export Registry")
    registry.register(PromptTemplate("qa-v1", "Q&A", "Q: {{question}}\nA: ", tags=["qa"]))
    registry.register(PromptTemplate("code-v1", "Code Gen", "Write {{language}} code for: {{task}}", tags=["code"]))
    registry.export("/tmp/prompt_registry.json")
    print(f"  Exported {len(registry.list_all())} templates to /tmp/prompt_registry.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
