"""Quantum Circuit - Circuit builder for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math
import cmath

class OpType(Enum):
    H = auto(); X = auto(); CNOT = auto(); MEASURE = auto()

@dataclass
class QuantumCircuit:
    num_qubits: int = 2
    operations: List[Tuple[OpType, List[int]]] = field(default_factory=list)

    def add_gate(self, op: OpType, targets: List[int]) -> None:
        self.operations.append((op, targets))

    def run(self, shots: int = 100) -> Dict[str, int]:
        state = [0.0]*(2**self.num_qubits)
        state[0] = 1.0
        for op, targets in self.operations:
            if op == OpType.H:
                t = targets[0]
                new = [0.0]*len(state)
                for i in range(len(state)):
                    j = i ^ (1 << t)
                    if (i >> t) & 1 == 0:
                        new[i] += (state[i] + state[j]) / math.sqrt(2)
                    else:
                        new[i] += (state[i] - state[j]) / math.sqrt(2)
                state = new
        results = {}
        for _ in range(shots):
            probs = [abs(s)**2 for s in state]
            r = __import__("random").random(); cum = 0
            for i, p in enumerate(probs):
                cum += p
                if r < cum:
                    key = format(i, f"0{self.num_qubits}b")
                    results[key] = results.get(key, 0) + 1
                    break
        return results

    def stats(self) -> dict:
        return {"qubits": self.num_qubits, "ops": len(self.operations)}

def run():
    qc = QuantumCircuit(2)
    qc.add_gate(OpType.H, [0])
    qc.add_gate(OpType.CNOT, [0, 1])
    print("Results:", qc.run(50))
    print("Stats:", qc.stats())

if __name__ == "__main__": run()
