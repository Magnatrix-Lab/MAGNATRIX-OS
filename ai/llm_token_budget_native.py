"""
llm_token_budget_native.py
MAGNATRIX-OS Token Budget Engine
Native Python, stdlib only.
Provides token budget allocation, spending tracking, and overflow handling for multi-stage generation.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class BudgetAllocation:
    stage: str
    allocated: int
    spent: int = 0
    overflow: int = 0

class TokenBudgetEngine:
    def __init__(self, total_budget: int) -> None:
        self.total_budget = total_budget
        self._stages: Dict[str, BudgetAllocation] = {}
        self._remaining = total_budget

    def allocate(self, stage: str, amount: int) -> bool:
        if amount > self._remaining:
            return False
        self._stages[stage] = BudgetAllocation(stage, amount)
        self._remaining -= amount
        return True

    def spend(self, stage: str, amount: int) -> bool:
        alloc = self._stages.get(stage)
        if not alloc:
            return False
        available = alloc.allocated - alloc.spent
        if amount > available:
            alloc.overflow += amount - available
            alloc.spent = alloc.allocated
        else:
            alloc.spent += amount
        return True

    def get_remaining(self, stage: str) -> int:
        alloc = self._stages.get(stage)
        return (alloc.allocated - alloc.spent) if alloc else 0

    def reallocate(self, from_stage: str, to_stage: str, amount: int) -> bool:
        from_alloc = self._stages.get(from_stage)
        to_alloc = self._stages.get(to_stage)
        if not from_alloc or not to_alloc:
            return False
        available = from_alloc.allocated - from_alloc.spent
        if amount > available:
            return False
        from_alloc.allocated -= amount
        to_alloc.allocated += amount
        return True

    def get_stats(self) -> Dict[str, Any]:
        total_spent = sum(s.spent for s in self._stages.values())
        total_overflow = sum(s.overflow for s in self._stages.values())
        return {"total": self.total_budget, "remaining": self._remaining, "spent": total_spent, "overflow": total_overflow, "stages": len(self._stages)}

def run() -> None:
    print("=" * 60); print("MAGNATRIX-OS Token Budget"); print("=" * 60)
    e = TokenBudgetEngine(total_budget=1000)
    e.allocate("prompt", 200)
    e.allocate("generation", 700)
    e.allocate("safety", 100)
    e.spend("generation", 500)
    e.spend("generation", 300)  # overflow
    print(f"  Stats: {e.get_stats()}")
    print(f"  Remaining gen: {e.get_remaining('generation')}")
    print("\nToken Budget test complete.")
if __name__ == "__main__": run()
