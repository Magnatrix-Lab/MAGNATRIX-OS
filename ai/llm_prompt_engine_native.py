"""Prompt Engine — Template management, variable substitution, prompt versioning, and optimization.

Modul ini menyediakan:
- PromptTemplate untuk template dengan variable substitution
- PromptRegistry untuk versioned prompt storage
- PromptOptimizer untuk prompt optimization via A/B testing
- PromptChain untuk chain multiple prompts
- PromptEngine untuk centralized prompt management
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
    FEW_SHOT = "few_shot"
    CHAIN = "chain"


@dataclass
class PromptTemplate:
    """Template with variables and metadata."""
    template_id: str
    name: str
    prompt_type: PromptType
    template: str
    variables: List[str] = field(default_factory=list)
    description: str = ""
    version: int = 1
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    usage_count: int = 0
    avg_score: float = 0.0

    def __post_init__(self):
        if not self.variables:
            self.variables = self._extract_variables()

    def _extract_variables(self) -> List[str]:
        # Extract {variable} patterns
        return list(set(re.findall(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}', self.template)))

    def render(self, **kwargs) -> str:
        result = self.template
        for var in self.variables:
            val = kwargs.get(var, f"{{{var}}}")
            result = result.replace(f"{{{var}}}", str(val))
        self.usage_count += 1
        return result

    def render_safe(self, **kwargs) -> Tuple[str, List[str]]:
        """Render and return list of missing variables."""
        result = self.template
        missing = []
        for var in self.variables:
            if var in kwargs:
                result = result.replace(f"{{{var}}}", str(kwargs[var]))
            else:
                missing.append(var)
        self.usage_count += 1
        return result, missing

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "type": self.prompt_type.value,
            "version": self.version,
            "variables": self.variables,
            "usage_count": self.usage_count,
            "avg_score": self.avg_score,
        }


@dataclass
class PromptVersion:
    """Version record for a prompt."""
    version_id: str
    template_id: str
    template: str
    version: int
    changes: str = ""
    created_at: float = field(default_factory=time.time)
    score: float = 0.0


class PromptRegistry:
    """Store and manage prompt templates with versioning."""

    def __init__(self):
        self._templates: Dict[str, PromptTemplate] = {}
        self._versions: Dict[str, List[PromptVersion]] = {}
        self._by_name: Dict[str, str] = {}  # name -> template_id

    def register(self, template: PromptTemplate) -> None:
        self._templates[template.template_id] = template
        self._by_name[template.name] = template.template_id
        self._versions.setdefault(template.template_id, [])

    def get(self, template_id: str) -> Optional[PromptTemplate]:
        return self._templates.get(template_id)

    def get_by_name(self, name: str) -> Optional[PromptTemplate]:
        tid = self._by_name.get(name)
        return self._templates.get(tid) if tid else None

    def create_version(self, template_id: str, new_template: str, changes: str = "") -> Optional[PromptTemplate]:
        old = self._templates.get(template_id)
        if not old:
            return None
        # Save old version
        self._versions[template_id].append(PromptVersion(
            version_id=str(uuid.uuid4())[:12],
            template_id=template_id,
            template=old.template,
            version=old.version,
            changes=changes,
            score=old.avg_score,
        ))
        # Update template
        old.template = new_template
        old.version += 1
        old.variables = old._extract_variables()
        return old

    def get_versions(self, template_id: str) -> List[PromptVersion]:
        return self._versions.get(template_id, [])

    def rollback(self, template_id: str, version: int) -> Optional[PromptTemplate]:
        versions = self._versions.get(template_id, [])
        for v in versions:
            if v.version == version:
                template = self._templates.get(template_id)
                if template:
                    template.template = v.template
                    template.version = version
                    template.variables = template._extract_variables()
                    return template
        return None

    def list_all(self) -> List[PromptTemplate]:
        return list(self._templates.values())

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._templates)
        total_usage = sum(t.usage_count for t in self._templates.values())
        return {
            "templates": total,
            "versions": sum(len(v) for v in self._versions.values()),
            "total_usage": total_usage,
            "avg_score": sum(t.avg_score for t in self._templates.values()) / max(total, 1),
        }


class PromptOptimizer:
    """Optimize prompts via A/B testing and scoring."""

    def __init__(self):
        self._experiments: Dict[str, List[Dict[str, Any]]] = {}

    def run_experiment(self, template_id: str, variants: List[str], evaluator: Callable[[str], float]) -> Dict[str, Any]:
        """Test prompt variants and pick best."""
        scores = []
        for variant in variants:
            score = evaluator(variant)
            scores.append({"variant": variant[:100], "score": score})
        best = max(scores, key=lambda x: x["score"])
        self._experiments[template_id] = scores
        return {
            "template_id": template_id,
            "variants_tested": len(variants),
            "best_score": best["score"],
            "best_variant": best["variant"],
            "all_scores": scores,
        }

    def optimize(self, template: PromptTemplate, optimizer_fn: Optional[Callable[[str], str]] = None) -> str:
        optimizer_fn = optimizer_fn or self._default_optimizer
        return optimizer_fn(template.template)

    def _default_optimizer(self, template: str) -> str:
        # Simple: add more specific instructions
        return template + "\n\nBe specific and concise in your response."

    def get_experiments(self, template_id: str) -> List[Dict[str, Any]]:
        return self._experiments.get(template_id, [])


class PromptChain:
    """Chain multiple prompts together."""

    def __init__(self, chain_id: str, name: str):
        self.chain_id = chain_id
        self.name = name
        self._steps: List[Tuple[str, Dict[str, str]]] = []  # (template_id, variable_mapping)
        self._results: List[Dict[str, Any]] = []

    def add_step(self, template_id: str, var_mapping: Optional[Dict[str, str]] = None) -> PromptChain:
        self._steps.append((template_id, var_mapping or {}))
        return self

    def execute(self, registry: PromptRegistry, initial_vars: Dict[str, Any]) -> List[Dict[str, Any]]:
        context = dict(initial_vars)
        results = []
        for template_id, mapping in self._steps:
            template = registry.get(template_id)
            if not template:
                results.append({"error": f"Template not found: {template_id}"})
                continue
            # Map context variables to template variables
            render_vars = {}
            for template_var, context_key in mapping.items():
                render_vars[template_var] = context.get(context_key, "")
            # Also include any matching context keys directly
            for var in template.variables:
                if var not in render_vars and var in context:
                    render_vars[var] = context[var]
            output, missing = template.render_safe(**render_vars)
            result = {
                "template_id": template_id,
                "output": output,
                "missing": missing,
            }
            results.append(result)
            # Store output in context for next steps
            context[f"output_{template_id}"] = output
        self._results = results
        return results

    def get_results(self) -> List[Dict[str, Any]]:
        return self._results

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "name": self.name,
            "steps": len(self._steps),
            "results": len(self._results),
        }


class PromptEngine:
    """Centralized prompt management."""

    def __init__(self):
        self.registry = PromptRegistry()
        self.optimizer = PromptOptimizer()
        self._chains: Dict[str, PromptChain] = {}

    def create_template(self, name: str, template: str, prompt_type: PromptType = PromptType.USER,
                        description: str = "") -> PromptTemplate:
        pt = PromptTemplate(
            template_id=str(uuid.uuid4())[:12],
            name=name,
            prompt_type=prompt_type,
            template=template,
            description=description,
        )
        self.registry.register(pt)
        return pt

    def create_chain(self, name: str) -> PromptChain:
        chain = PromptChain(str(uuid.uuid4())[:12], name)
        self._chains[chain.chain_id] = chain
        return chain

    def render(self, template_id: str, **kwargs) -> str:
        template = self.registry.get(template_id)
        if not template:
            return f"[Template not found: {template_id}]"
        return template.render(**kwargs)

    def get_template(self, name: str) -> Optional[PromptTemplate]:
        return self.registry.get_by_name(name)

    def optimize_template(self, template_id: str) -> Optional[str]:
        template = self.registry.get(template_id)
        if not template:
            return None
        optimized = self.optimizer.optimize(template)
        self.registry.create_version(template_id, optimized, "Auto-optimized")
        return optimized

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self.registry.get_stats(),
            "chains": len(self._chains),
        }

    def export_all(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "templates": [t.to_dict() for t in self.registry.list_all()],
                "chains": [c.to_dict() for c in self._chains.values()],
                "stats": self.get_stats(),
            }, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("PROMPT ENGINE DEMO")
    print("=" * 70)

    engine = PromptEngine()

    # 1. Create templates
    print("\n[1] Create Templates")
    t1 = engine.create_template("greeting", "Hello {name}! Welcome to {service}.", PromptType.USER)
    t2 = engine.create_template("qa", "Question: {question}\nContext: {context}\nAnswer:", PromptType.USER)
    t3 = engine.create_template("summarize", "Summarize the following text in {length} sentences:\n{text}", PromptType.USER)
    t4 = engine.create_template("system_prompt", "You are a helpful assistant. Respond in {language}.", PromptType.SYSTEM)
    print(f"  Created: {t1.template_id}, vars={t1.variables}")
    print(f"  Created: {t2.template_id}, vars={t2.variables}")
    print(f"  Created: {t3.template_id}, vars={t3.variables}")
    print(f"  Created: {t4.template_id}, vars={t4.variables}")

    # 2. Render
    print("\n[2] Render Templates")
    print(f"  Greeting: {engine.render(t1.template_id, name='Alice', service='MAGNATRIX')}")
    print(f"  QA: {engine.render(t2.template_id, question='What is AI?', context='AI is...')}")
    print(f"  Summarize: {engine.render(t3.template_id, text='Long text here...', length='3')}")
    print(f"  System: {engine.render(t4.template_id, language='Indonesian')}")

    # 3. Safe render with missing
    print("\n[3] Safe Render")
    output, missing = t1.render_safe(name="Bob")
    print(f"  Output: {output}")
    print(f"  Missing: {missing}")

    # 4. Versioning
    print("\n[4] Versioning")
    engine.registry.create_version(t1.template_id, "Hi {name}! Welcome to {service}. Enjoy your stay!", "More friendly")
    print(f"  Version: {t1.version}")
    print(f"  Template: {t1.template}")
    versions = engine.registry.get_versions(t1.template_id)
    print(f"  Versions: {len(versions)}")
    for v in versions:
        print(f"    v{v.version}: {v.template[:40]}...")

    # 5. Rollback
    print("\n[5] Rollback")
    engine.registry.rollback(t1.template_id, 1)
    print(f"  After rollback v1: {t1.template}")

    # 6. Prompt chain
    print("\n[6] Prompt Chain")
    chain = engine.create_chain("Research Pipeline")
    chain.add_step(t2.template_id, {"question": "topic", "context": "background"})
    chain.add_step(t3.template_id, {"text": f"output_{t2.template_id}", "length": "3"})
    results = chain.execute(engine.registry, {
        "topic": "What is quantum computing?",
        "background": "Quantum computing uses quantum mechanics...",
    })
    for i, r in enumerate(results):
        print(f"  Step {i}: {r['output'][:50]}...")

    # 7. Optimization
    print("\n[7] Prompt Optimization")
    optimized = engine.optimize_template(t2.template_id)
    print(f"  Optimized: {optimized[:80]}...")
    print(f"  Version now: {engine.registry.get(t2.template_id).version}")

    # 8. A/B test
    print("\n[8] A/B Test")
    variants = [
        "Answer: {question}",
        "Question: {question}\nPlease answer concisely:",
        "Q: {question}\nA:",
    ]
    def evaluator(t):
        return 1.0 if "concisely" in t else 0.5
    result = engine.optimizer.run_experiment(t2.template_id, variants, evaluator)
    print(f"  Best: {result['best_variant'][:50]}...")
    print(f"  Score: {result['best_score']}")

    # 9. Stats
    print(f"\n[9] Stats")
    print(f"  {engine.get_stats()}")

    # 10. Export
    print("\n[10] Export")
    engine.export_all("/tmp/prompts.json")
    print("  Exported to /tmp/prompts.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
