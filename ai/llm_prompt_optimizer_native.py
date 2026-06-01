#!/usr/bin/env python3
"""
ai/llm_prompt_optimizer_native.py
MAGNATRIX-OS — Prompt Optimization Engine for the LLM Arena
AMATI pattern: prompt engineering, CoT, few-shot, prompt compression, safety

Pure Python, stdlib only. Simulates prompt analysis, chain-of-thought injection,
few-shot selection, compression, and safety wrapping.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ───────────────────────────────────────────────────────────────
# 0. UTILITIES
# ───────────────────────────────────────────────────────────────

def _now() -> float:
    return time.time()


def _token_count(text: str) -> int:
    return len(text) // 4 + 1


# ───────────────────────────────────────────────────────────────
# 1. PROMPT ANALYZER
# ───────────────────────────────────────────────────────────────

class PromptAnalyzer:
    """Analyze prompt complexity, detect task type, identify missing context."""

    TASK_TYPES = {
        "reasoning": ["why", "how", "explain", "prove", "what if", "analyze", "compare"],
        "coding": ["code", "function", "script", "program", "debug", "write python", "write javascript"],
        "math": ["solve", "calculate", "compute", "equation", "integral", "derivative", "formula"],
        "writing": ["write", "essay", "email", "letter", "story", "blog", "article"],
        "translation": ["translate", "convert to", "in spanish", "in french", "in japanese"],
        "summarization": ["summarize", "tl;dr", "summary", "condense", "brief"],
        "creative": ["imagine", "create", "design", "generate", "brainstorm", "idea"],
    }

    COMPLEXITY_INDICATORS = ["step by step", "detailed", "comprehensive", "in depth", "thorough", "elaborate"]

    def analyze(self, prompt: str) -> Dict[str, Any]:
        text = prompt.lower()
        detected = []
        for task, keywords in self.TASK_TYPES.items():
            if any(kw in text for kw in keywords):
                detected.append(task)
        if not detected:
            detected = ["general"]

        complexity = 1
        for ind in self.COMPLEXITY_INDICATORS:
            if ind in text:
                complexity += 1
        complexity += len(prompt) // 200
        complexity = min(complexity, 10)

        missing = []
        if any(t in detected for t in ["coding", "math", "reasoning"]):
            if len(prompt) < 30:
                missing.append("more context or constraints")

        return {
            "task_types": detected,
            "complexity": complexity,
            "tokens": _token_count(prompt),
            "missing_context": missing,
            "suggestions": self._suggest(detected, complexity),
        }

    def _suggest(self, tasks: List[str], complexity: int) -> List[str]:
        suggestions = []
        if "reasoning" in tasks and complexity < 3:
            suggestions.append("Add 'think step by step' for better reasoning")
        if "coding" in tasks:
            suggestions.append("Specify language and input/output format")
        if "math" in tasks:
            suggestions.append("Clarify expected precision and format")
        return suggestions


# ───────────────────────────────────────────────────────────────
# 2. CHAIN OF THOUGHT INJECTOR
# ───────────────────────────────────────────────────────────────

class ChainOfThoughtInjector:
    """Auto-add CoT reasoning to prompts where beneficial."""

    COT_TRIGGERS = ["reasoning", "math", "coding", "analysis", "comparison"]
    COT_SUFFIXES = [
        "Let's think step by step.",
        "Break this down systematically.",
        "Show your reasoning clearly.",
        "Walk through your logic step by step.",
    ]

    def inject(self, prompt: str, task_types: List[str], complexity: int) -> str:
        if any(t in self.COT_TRIGGERS for t in task_types) and complexity >= 2:
            import random
            suffix = random.choice(self.COT_SUFFIXES)
            if not any(s.lower() in prompt.lower() for s in self.COT_SUFFIXES):
                return f"{prompt}\n\n{suffix}"
        return prompt


# ───────────────────────────────────────────────────────────────
# 3. FEW-SHOT TEMPLATE
# ───────────────────────────────────────────────────────────────

class FewShotTemplate:
    """Select and inject relevant few-shot examples from a curated library."""

    LIBRARY: Dict[str, List[Dict[str, str]]] = {
        "coding": [
            {"input": "Write a function to reverse a string.", "output": "def reverse(s): return s[::-1]"},
            {"input": "How to sort a list of dicts by key?", "output": "sorted(data, key=lambda x: x['name'])"},
        ],
        "math": [
            {"input": "Solve 2x + 5 = 13", "output": "x = 4"},
            {"input": "What is the derivative of x^2?", "output": "2x"},
        ],
        "writing": [
            {"input": "Write a professional email requesting a meeting.", "output": "Dear [Name], I hope this finds you well..."},
        ],
        "translation": [
            {"input": "Translate 'Hello' to Spanish", "output": "Hola"},
        ],
    }

    def select(self, task_type: str, n: int = 2) -> List[Dict[str, str]]:
        examples = self.LIBRARY.get(task_type, [])
        return examples[:n]

    def inject(self, prompt: str, task_type: str, n: int = 2) -> str:
        examples = self.select(task_type, n)
        if not examples:
            return prompt
        parts = ["Here are some examples:"]
        for ex in examples:
            parts.append(f"Q: {ex['input']}\nA: {ex['output']}")
        parts.append(f"Now your turn:\nQ: {prompt}")
        return "\n\n".join(parts)


# ───────────────────────────────────────────────────────────────
# 4. PROMPT COMPRESSOR
# ───────────────────────────────────────────────────────────────

class PromptCompressor:
    """Compress long prompts to fit context window while preserving meaning."""

    def compress(self, prompt: str, max_tokens: int = 1024) -> str:
        tokens = _token_count(prompt)
        if tokens <= max_tokens:
            return prompt
        char_limit = max_tokens * 4
        first_part = prompt[: int(len(prompt) * 0.3)]
        last_part = prompt[-int(len(prompt) * 0.3):]
        combined = f"{first_part}\n\n...[compressed: {tokens - max_tokens} tokens removed]...\n\n{last_part}"
        if len(combined) > char_limit:
            return prompt[:char_limit - 3] + "..."
        return combined

    def compress_smart(self, prompt: str, max_tokens: int = 1024) -> str:
        """Remove redundant whitespace and filler words."""
        lines = [line.strip() for line in prompt.split("\n") if line.strip()]
        compressed = "\n".join(lines)
        if _token_count(compressed) <= max_tokens:
            return compressed
        return self.compress(compressed, max_tokens)


# ───────────────────────────────────────────────────────────────
# 5. SAFETY WRAPPER
# ───────────────────────────────────────────────────────────────

class SafetyWrapper:
    """Jailbreak detection, prompt injection filtering, content policy checks."""

    JAILBREAK_PATTERNS = [
        "ignore previous instructions", "ignore all instructions", "you are now",
        "DAN mode", "developer mode", "no constraints", "bypass filter",
        "jailbreak", "ignore your training", "pretend to be",
    ]

    INJECTION_PATTERNS = [
        "<script>", "javascript:", "onerror=", "eval(", "document.cookie",
        "system prompt", "inner workings", "your instructions are",
    ]

    POLICY_VIOLATIONS = [
        "how to make a bomb", "how to hack", "steal data", "bypass security",
        "create malware", "social engineering", "phishing template",
    ]

    def check(self, prompt: str) -> Dict[str, Any]:
        text = prompt.lower()
        flags = []
        for pattern in self.JAILBREAK_PATTERNS:
            if pattern in text:
                flags.append(f"jailbreak: '{pattern}'")
        for pattern in self.INJECTION_PATTERNS:
            if pattern in text:
                flags.append(f"injection: '{pattern}'")
        for pattern in self.POLICY_VIOLATIONS:
            if pattern in text:
                flags.append(f"policy: '{pattern}'")

        return {
            "safe": len(flags) == 0,
            "flags": flags,
            "risk_score": len(flags) / 3.0,
            "sanitized": self.sanitize(prompt) if flags else prompt,
        }

    def sanitize(self, prompt: str) -> str:
        sanitized = prompt
        for pattern in self.JAILBREAK_PATTERNS + self.INJECTION_PATTERNS:
            sanitized = re.sub(re.escape(pattern), "[REDACTED]", sanitized, flags=re.IGNORECASE)
        return sanitized


# ───────────────────────────────────────────────────────────────
# 6. OPTIMIZER PIPELINE
# ───────────────────────────────────────────────────────────────

class OptimizerPipeline:
    """Main orchestrator: analyze -> inject CoT -> add few-shot -> compress -> wrap safety."""

    def __init__(self, max_tokens: int = 2048) -> None:
        self.analyzer = PromptAnalyzer()
        self.cot = ChainOfThoughtInjector()
        self.few_shot = FewShotTemplate()
        self.compressor = PromptCompressor()
        self.safety = SafetyWrapper()
        self.max_tokens = max_tokens

    def optimize(self, prompt: str, task_type: Optional[str] = None, use_few_shot: bool = True) -> Dict[str, Any]:
        analysis = self.analyzer.analyze(prompt)
        detected_tasks = analysis["task_types"]
        complexity = analysis["complexity"]

        optimized = self.cot.inject(prompt, detected_tasks, complexity)

        if use_few_shot and task_type and task_type in detected_tasks:
            optimized = self.few_shot.inject(optimized, task_type, n=2)
        elif use_few_shot and detected_tasks:
            optimized = self.few_shot.inject(optimized, detected_tasks[0], n=1)

        optimized = self.compressor.compress_smart(optimized, self.max_tokens)

        safety = self.safety.check(optimized)
        if not safety["safe"]:
            optimized = safety["sanitized"]

        return {
            "original": prompt,
            "optimized": optimized,
            "analysis": analysis,
            "safety": safety,
            "token_savings": _token_count(prompt) - _token_count(optimized),
        }

    def quick_optimize(self, prompt: str) -> str:
        return self.optimize(prompt, use_few_shot=False)["optimized"]


# ───────────────────────────────────────────────────────────────
# 7. DEMO
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Prompt Optimizer Demo")
    print("=" * 60)

    optimizer = OptimizerPipeline(max_tokens=1024)

    test_prompts = [
        "Why is the sky blue?",
        "Write a Python function to calculate factorial.",
        "Translate 'Good morning' to Japanese and explain the grammar.",
        "Summarize the theory of relativity in simple terms.",
    ]

    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n[{i}] Original: {prompt[:50]}...")
        result = optimizer.optimize(prompt, use_few_shot=True)
        print(f"    Task types: {result['analysis']['task_types']}")
        print(f"    Complexity: {result['analysis']['complexity']}/10")
        print(f"    Tokens saved: {result['token_savings']}")
        print(f"    Safe: {result['safety']['safe']}")
        print(f"    Optimized preview:\n    {result['optimized'][:120]}...")

    print("\n" + "=" * 60)
    print("Demo complete. Prompt Optimizer ready for LLM Arena.")
    print("=" * 60)
