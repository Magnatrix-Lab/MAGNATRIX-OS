"""
llm_input_injection_native.py
MAGNATRIX-OS Input Injection Engine
Native Python, stdlib only.
Provides recurrent input injection, residual blending, state merging, and adaptive mixing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


class InputInjectionEngine:
    """Recurrent input injection with adaptive mixing."""

    def __init__(self, alpha: float = 0.5) -> None:
        self.alpha = alpha
        self._injectors: List[Callable] = []

    def add_injector(self, fn: Callable[[Any, Any], Any]) -> None:
        self._injectors.append(fn)

    def inject(self, hidden_state: Any, raw_input: Any, iteration: int = 0) -> Any:
        # Mix hidden state with raw input
        if isinstance(hidden_state, list) and isinstance(raw_input, list):
            blended = [self.alpha * h + (1 - self.alpha) * r for h, r in zip(hidden_state, raw_input)]
        else:
            blended = hidden_state

        for injector in self._injectors:
            blended = injector(blended, iteration)
        return blended

    def get_stats(self) -> Dict[str, Any]:
        return {"alpha": self.alpha, "injectors": len(self._injectors)}


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Input Injection Engine")
    print("=" * 60)
    engine = InputInjectionEngine(alpha=0.7)
    h = [1.0, 2.0, 3.0]
    inp = [0.5, 0.5, 0.5]
    result = engine.inject(h, inp, iteration=1)
    print(f"  Hidden: {h}")
    print(f"  Input: {inp}")
    print(f"  Blended: {result}")
    print("\nInput Injection test complete.")

if __name__ == "__main__":
    run()
