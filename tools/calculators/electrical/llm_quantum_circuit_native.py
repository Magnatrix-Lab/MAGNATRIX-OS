"""Quantum Circuit Builder — gate sequences, depth, transpilation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

class GateType(Enum):
    H = auto(); X = auto(); Y = auto(); Z = auto(); CNOT = auto(); T = auto(); S = auto()

@dataclass
class Gate:
    gate: GateType
    targets: List[int]
    controls: List[int] = field(default_factory=list)

@dataclass
class QuantumCircuitBuilder:
    gates: List[Gate] = field(default_factory=list)
    num_qubits: int = 0

    def add_qubits(self, n: int):
        self.num_qubits = max(self.num_qubits, n)

    def append(self, gate: GateType, targets: List[int], controls: List[int] = None):
        self.gates.append(Gate(gate, targets, controls or []))

    def depth(self) -> int:
        if not self.gates:
            return 0
        layers = 0
        last_used = {}
        for g in self.gates:
            qubits = g.targets + g.controls
            earliest = max((last_used.get(q, -1) for q in qubits), default=-1)
            for q in qubits:
                last_used[q] = earliest + 1
            layers = max(layers, max(last_used.values()) + 1)
        return layers

    def gate_count(self) -> Dict[str, int]:
        counts = {}
        for g in self.gates:
            counts[g.gate.name] = counts.get(g.gate.name, 0) + 1
        return counts

    def stats(self) -> Dict:
        return {"qubits": self.num_qubits, "gates": len(self.gates), "depth": self.depth(), "counts": self.gate_count()}

def run():
    b = QuantumCircuitBuilder()
    b.add_qubits(2)
    b.append(GateType.H, [0])
    b.append(GateType.CNOT, [1], [0])
    print(b.stats())

if __name__ == "__main__":
    run()
