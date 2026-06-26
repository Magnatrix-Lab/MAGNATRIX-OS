#!/usr/bin/env python3
"""Prompt Chaining Engine for MAGNATRIX-OS — Chain multiple prompts for complex reasoning."""
from __future__ import annotations
import json, re, time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

@dataclass
class PromptStep:
    id: str
    template: str
    output_key: str = ""
    condition: Optional[str] = None
    fallback: Optional[str] = None

class PromptChain:
    def __init__(self, name: str = "chain") -> None:
        self.name = name
        self._steps: List[PromptStep] = []
        self._outputs: Dict[str, Any] = {}
        self._llm_fn: Optional[Callable[[str], str]] = None

    def add_step(self, step: PromptStep) -> None:
        self._steps.append(step)

    def set_llm(self, fn: Callable[[str], str]) -> None:
        self._llm_fn = fn

    def execute(self, initial_input: str) -> Dict[str, Any]:
        self._outputs["input"] = initial_input
        context = initial_input
        for step in self._steps:
            template = step.template
            for key, val in self._outputs.items():
                template = template.replace(f"{{{key}}}", str(val))
            if self._llm_fn:
                result = self._llm_fn(template)
            else:
                result = f"[MOCK] {template[:50]}..."
            self._outputs[step.output_key or step.id] = result
            context = result
        return self._outputs

    def stats(self) -> Dict[str, Any]:
        return {"steps": len(self._steps), "outputs": len(self._outputs)}
