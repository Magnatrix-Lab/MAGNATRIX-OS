"""Mutation Testing — code mutation, test validation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any
from enum import Enum, auto
import random
import ast
import copy

class MutantStatus(Enum):
    KILLED = auto()
    SURVIVED = auto()
    TIMEOUT = auto()

@dataclass
class Mutant:
    mutant_id: str
    original: str
    mutated: str
    mutation_type: str
    status: MutantStatus = MutantStatus.SURVIVED

class MutationTester:
    def __init__(self):
        self.mutants: List[Mutant] = []
        self.mutation_operators: Dict[str, Callable[[str], str]] = {}
        self._register_operators()

    def _register_operators(self):
        self.mutation_operators["arithmetic"] = lambda s: s.replace("+", "-", 1) if "+" in s else s
        self.mutation_operators["comparison"] = lambda s: s.replace(">", "<", 1) if ">" in s else s
        self.mutation_operators["boolean"] = lambda s: s.replace("and", "or", 1) if "and" in s else s
        self.mutation_operators["equality"] = lambda s: s.replace("==", "!=", 1) if "==" in s else s

    def generate_mutants(self, source_code: str) -> List[Mutant]:
        mutants = []
        for op_name, op_fn in self.mutation_operators.items():
            mutated = op_fn(source_code)
            if mutated != source_code:
                mutants.append(Mutant(str(len(mutants)), source_code, mutated, op_name))
        self.mutants.extend(mutants)
        return mutants

    def test_mutant(self, mutant: Mutant, test_suite: List[Callable]) -> MutantStatus:
        try:
            for test in test_suite:
                test()
            mutant.status = MutantStatus.SURVIVED
        except AssertionError:
            mutant.status = MutantStatus.KILLED
        except:
            mutant.status = MutantStatus.KILLED
        return mutant.status

    def run_all(self, test_suite: List[Callable]) -> Dict:
        for mutant in self.mutants:
            self.test_mutant(mutant, test_suite)
        killed = sum(1 for m in self.mutants if m.status == MutantStatus.KILLED)
        total = len(self.mutants)
        return {"mutants": total, "killed": killed, "survived": total - killed, "score": killed / total if total else 0}

    def stats(self) -> Dict:
        return {"total_mutants": len(self.mutants), "by_type": {m.mutation_type for m in self.mutants}}

def run():
    tester = MutationTester()
    code = "x + y"
    mutants = tester.generate_mutants(code)
    def test_add():
        assert eval("x + y", {"x": 1, "y": 2}) == 3
    for m in mutants:
        try:
            result = eval(m.mutated, {"x": 1, "y": 2})
            m.status = MutantStatus.SURVIVED if result == 3 else MutantStatus.KILLED
        except:
            m.status = MutantStatus.KILLED
    print(tester.stats())

if __name__ == "__main__":
    run()
