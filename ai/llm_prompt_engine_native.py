"""Prompt Engineering Suite — Templates, versioning, chain-of-thought, optimization.

Modul ini menyediakan:
- PromptTemplate dengan variable substitution dan validation
- PromptChain untuk multi-step reasoning
- PromptVersion untuk versioning dan rollback
- PromptOptimizer untuk auto-optimization metrics
- FewShotBuilder untuk few-shot example construction

Arsitektur: Template → Chain → Version → Optimize → Execute
"""

from __future__ import annotations

import json
import time
import uuid
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class PromptType(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    FEWSHOT = "fewshot"


class OptimizationTarget(Enum):
    ACCURACY = auto()
    TOKEN_EFFICIENCY = auto()
    LATENCY = auto()
    CLARITY = auto()


@dataclass
class PromptTemplate:
    """Template with variable slots."""
    template_id: str
    name: str
    template: str
    prompt_type: PromptType = PromptType.USER
    variables: List[str] = field(default_factory=list)
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.variables:
            self.variables = self._extract_vars(self.template)

    @staticmethod
    def _extract_vars(template: str) -> List[str]:
        return list(set(re.findall(r'\{(\w+)\}', template)))

    def render(self, **kwargs) -> str:
        result = self.template
        for var in self.variables:
            val = kwargs.get(var, f"{{{var}}}")
            result = result.replace(f"{{{var}}}", str(val))
        return result

    def validate(self, **kwargs) -> Tuple[bool, List[str]]:
        missing = [v for v in self.variables if v not in kwargs]
        return len(missing) == 0, missing


@dataclass
class PromptExample:
    """Single example for few-shot prompting."""
    input: str
    output: str
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PromptChain:
    """Chain of prompts for multi-step reasoning."""
    chain_id: str
    name: str
    steps: List[PromptTemplate] = field(default_factory=list)
    step_results: List[Any] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_step(self, template: PromptTemplate) -> PromptChain:
        self.steps.append(template)
        return self

    def execute(self, context: Dict[str, Any],
                executor: Optional[Callable[[str, Dict[str, Any]], str]] = None) -> List[str]:
        executor = executor or self._default_executor
        self.step_results = []
        current_ctx = dict(context)
        for i, step in enumerate(self.steps):
            ok, missing = step.validate(**current_ctx)
            if not ok:
                self.step_results.append(f"[ERROR] Missing vars: {missing}")
                continue
            prompt = step.render(**current_ctx)
            result = executor(prompt, current_ctx)
            self.step_results.append(result)
            current_ctx[f"step_{i}_result"] = result
        return self.step_results

    def _default_executor(self, prompt: str, ctx: Dict[str, Any]) -> str:
        return f"[SIMULATED] {prompt[:50]}..."


@dataclass
class PromptVersion:
    """Versioned prompt with metrics."""
    version_id: str
    template_id: str
    version: str  # semantic version
    template: str
    metrics: Dict[str, float] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    parent: Optional[str] = None


class PromptVersionManager:
    """Manage prompt versions and history."""

    def __init__(self):
        self._versions: Dict[str, List[PromptVersion]] = {}
        self._current: Dict[str, str] = {}  # template_id -> version_id

    def save(self, template_id: str, template: str, metrics: Optional[Dict[str, float]] = None) -> PromptVersion:
        versions = self._versions.setdefault(template_id, [])
        ver_num = f"1.{len(versions)}.0"
        pv = PromptVersion(
            version_id=str(uuid.uuid4())[:12],
            template_id=template_id,
            version=ver_num,
            template=template,
            metrics=metrics or {}
        )
        if versions:
            pv.parent = versions[-1].version_id
        versions.append(pv)
        self._current[template_id] = pv.version_id
        return pv

    def get(self, template_id: str, version_id: Optional[str] = None) -> Optional[PromptVersion]:
        versions = self._versions.get(template_id, [])
        if not version_id:
            vid = self._current.get(template_id)
            if vid:
                return next((v for v in versions if v.version_id == vid), None)
            return versions[-1] if versions else None
        return next((v for v in versions if v.version_id == version_id), None)

    def rollback(self, template_id: str) -> Optional[PromptVersion]:
        current = self.get(template_id)
        if current and current.parent:
            self._current[template_id] = current.parent
            return self.get(template_id, current.parent)
        return None

    def list_versions(self, template_id: str) -> List[PromptVersion]:
        return self._versions.get(template_id, [])

    def compare(self, template_id: str, v1: str, v2: str) -> Dict[str, Any]:
        a = self.get(template_id, v1)
        b = self.get(template_id, v2)
        if not a or not b:
            return {"error": "Version not found"}
        return {
            "v1": a.version,
            "v2": b.version,
            "template_diff": a.template != b.template,
            "metrics": {
                k: {"v1": a.metrics.get(k, 0), "v2": b.metrics.get(k, 0)}
                for k in set(a.metrics) | set(b.metrics)
            }
        }


class FewShotBuilder:
    """Build few-shot examples from data."""

    def __init__(self, max_examples: int = 5):
        self.max_examples = max_examples
        self._examples: List[PromptExample] = []

    def add(self, example: PromptExample) -> FewShotBuilder:
        self._examples.append(example)
        return self

    def build(self, template: str = "Input: {input}\nOutput: {output}") -> str:
        selected = self._examples[:self.max_examples]
        parts = []
        for ex in selected:
            parts.append(template.replace("{input}", ex.input).replace("{output}", ex.output))
        return "\n\n".join(parts)

    def build_with_reasoning(self, separator: str = "\n---\n") -> str:
        selected = self._examples[:self.max_examples]
        parts = []
        for ex in selected:
            part = f"Input: {ex.input}\nReasoning: {ex.reasoning}\nOutput: {ex.output}"
            parts.append(part)
        return separator.join(parts)

    def score_diversity(self) -> float:
        if len(self._examples) < 2:
            return 1.0
        # Simple diversity: average Jaccard distance of inputs
        inputs = [set(ex.input.split()) for ex in self._examples]
        total = 0
        count = 0
        for i in range(len(inputs)):
            for j in range(i + 1, len(inputs)):
                union = len(inputs[i] | inputs[j])
                inter = len(inputs[i] & inputs[j])
                total += 1 - (inter / union) if union > 0 else 0
                count += 1
        return total / count if count > 0 else 1.0


class PromptOptimizer:
    """Optimize prompts for target metrics."""

    def __init__(self, target: OptimizationTarget = OptimizationTarget.ACCURACY):
        self.target = target
        self._history: List[Dict[str, Any]] = []

    def optimize(self, template: PromptTemplate,
                 evaluator: Optional[Callable[[str], float]] = None,
                 iterations: int = 3) -> PromptTemplate:
        evaluator = evaluator or self._default_evaluator
        best = template
        best_score = evaluator(template.template)
        self._history.append({"template": template.template, "score": best_score, "iteration": 0})

        for i in range(1, iterations + 1):
            # Simple optimization strategies
            candidate = self._mutate(best)
            score = evaluator(candidate)
            self._history.append({"template": candidate, "score": score, "iteration": i})
            if score > best_score:
                best_score = score
                best = PromptTemplate(
                    template_id=template.template_id,
                    name=f"{template.name}-opt{i}",
                    template=candidate,
                    prompt_type=template.prompt_type,
                    metadata={**template.metadata, "optimized": True}
                )
        return best

    def _mutate(self, template: PromptTemplate) -> str:
        # Simplistic mutations
        t = template.template
        mutations = [
            lambda s: f"Be concise and accurate.\n\n{s}",
            lambda s: s.replace("Please ", "").replace("Could you ", ""),
            lambda s: f"{s}\n\nThink step by step.",
        ]
        import random
        m = random.choice(mutations)
        return m(t)

    def _default_evaluator(self, template: str) -> float:
        # Simulated scoring
        score = 0.7
        if "step by step" in template.lower():
            score += 0.1
        if len(template) < 200:
            score += 0.05
        return min(1.0, score)

    def get_history(self) -> List[Dict[str, Any]]:
        return self._history


class PromptLibrary:
    """Pre-built prompt templates library."""

    @staticmethod
    def chain_of_thought(question: str = "{question}") -> PromptTemplate:
        return PromptTemplate(
            template_id="cot-1",
            name="Chain of Thought",
            template=f"Answer the following question by thinking step by step:\n\n{question}\n\nLet's work through this:",
            prompt_type=PromptType.USER
        )

    @staticmethod
    def fewshot_classifier(examples: Optional[List[PromptExample]] = None) -> PromptTemplate:
        return PromptTemplate(
            template_id="fewshot-1",
            name="Few-Shot Classifier",
            template="{examples}\n\nInput: {input}\nOutput:",
            prompt_type=PromptType.FEWSHOT
        )

    @staticmethod
    def system_role(role: str = "helpful assistant") -> PromptTemplate:
        return PromptTemplate(
            template_id="sys-1",
            name="System Role",
            template=f"You are a {role}. Provide accurate, helpful responses.",
            prompt_type=PromptType.SYSTEM
        )

    @staticmethod
    def re_act(question: str = "{question}") -> PromptTemplate:
        return PromptTemplate(
            template_id="react-1",
            name="ReAct Pattern",
            template=f"Question: {question}\nThought: Let's analyze this step by step.\nAction: [search for information]\nObservation: [result]\nThought: Based on the observation...\nAnswer: ",
            prompt_type=PromptType.USER
        )


class PromptEngine:
    """Main engine combining all prompt components."""

    def __init__(self):
        self.templates: Dict[str, PromptTemplate] = {}
        self.chains: Dict[str, PromptChain] = {}
        self.versions = PromptVersionManager()
        self.library = PromptLibrary()

    def register(self, template: PromptTemplate) -> None:
        self.templates[template.template_id] = template

    def create_chain(self, name: str, steps: List[PromptTemplate]) -> PromptChain:
        chain = PromptChain(
            chain_id=str(uuid.uuid4())[:12],
            name=name,
            steps=steps
        )
        self.chains[chain.chain_id] = chain
        return chain

    def render(self, template_id: str, **kwargs) -> str:
        t = self.templates.get(template_id)
        if not t:
            raise ValueError(f"Template {template_id} not found")
        return t.render(**kwargs)

    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        return self.templates.get(template_id)

    def list_templates(self) -> List[PromptTemplate]:
        return list(self.templates.values())


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("PROMPT ENGINEERING SUITE DEMO")
    print("=" * 70)

    engine = PromptEngine()

    # 1. Template rendering
    print("\n[1] Template Rendering")
    t = PromptTemplate("t-1", "Greeting", "Hello {name}! Welcome to {place}.")
    engine.register(t)
    print(f"  Rendered: {engine.render('t-1', name='Alice', place='MAGNATRIX')}")

    # 2. Validation
    print("\n[2] Template Validation")
    ok, missing = t.validate(name="Alice")
    print(f"  With name: valid={ok}, missing={missing}")
    ok, missing = t.validate()
    print(f"  Without vars: valid={ok}, missing={missing}")

    # 3. Chain of Thought
    print("\n[3] Chain of Thought")
    cot = PromptLibrary.chain_of_thought()
    print(f"  Template: {cot.render(question='What is 2+2?')[:80]}...")

    # 4. ReAct pattern
    print("\n[4] ReAct Pattern")
    react = PromptLibrary.re_act()
    print(f"  Template: {react.render(question='How do I optimize Python code?')[:80]}...")

    # 5. Chain execution
    print("\n[5] Chain Execution")
    chain = engine.create_chain("Analysis Chain", [
        PromptTemplate("analyze", "Analyze", "Analyze the problem: {input}"),
        PromptTemplate("suggest", "Suggest", "Based on the analysis, suggest solutions."),
    ])
    results = chain.execute({"input": "Slow database queries"})
    for i, r in enumerate(results):
        print(f"  Step {i}: {r[:60]}...")

    # 6. Few-shot builder
    print("\n[6] Few-Shot Builder")
    builder = FewShotBuilder(max_examples=3)
    builder.add(PromptExample("What is the capital of France?", "Paris"))
    builder.add(PromptExample("What is the capital of Japan?", "Tokyo"))
    builder.add(PromptExample("What is the capital of Germany?", "Berlin"))
    prompt = builder.build()
    print(f"  Examples:\n{prompt}")
    print(f"  Diversity score: {builder.score_diversity():.2f}")

    # 7. Versioning
    print("\n[7] Prompt Versioning")
    vm = PromptVersionManager()
    v1 = vm.save("classifier", "Classify: {input} -> {label}", {"accuracy": 0.82})
    v2 = vm.save("classifier", "Classify this input: {input}\nLabel: {label}", {"accuracy": 0.89})
    print(f"  v1: {v1.version}, accuracy={v1.metrics['accuracy']}")
    print(f"  v2: {v2.version}, accuracy={v2.metrics['accuracy']}")
    comparison = vm.compare("classifier", v1.version_id, v2.version_id)
    print(f"  Comparison: {comparison}")

    # 8. Optimization
    print("\n[8] Prompt Optimization")
    opt = PromptOptimizer(OptimizationTarget.ACCURACY)
    original = PromptTemplate("opt-1", "Original", "Explain {topic} to me.")
    optimized = opt.optimize(original, iterations=3)
    print(f"  Original: {original.template}")
    print(f"  Optimized: {optimized.template}")
    print(f"  History: {len(opt.get_history())} iterations")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
