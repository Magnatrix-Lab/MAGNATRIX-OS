"""Qubit Simulator — quantum state vectors, gates, measurement, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import random, math, cmath

class GateType(Enum):
    H = auto(); X = auto(); Y = auto(); Z = auto(); CNOT = auto(); SWAP = auto()

@dataclass
class Qubit:
    alpha: complex = complex(1, 0)
    beta: complex = complex(0, 0)
    def normalize(self):
        n = math.sqrt(abs(self.alpha)**2 + abs(self.beta)**2)
        if n > 0:
            self.alpha /= n; self.beta /= n

@dataclass
class QuantumCircuit:
    qubits: List[Qubit] = field(default_factory=list)
    gates: List[Tuple[GateType, List[int]]] = field(default_factory=list)

    def add_qubit(self, q: Qubit):
        self.qubits.append(q)

    def apply(self, gate: GateType, targets: List[int]):
        self.gates.append((gate, targets))
        if gate == GateType.H and len(targets) == 1:
            q = self.qubits[targets[0]]
            a, b = q.alpha, q.beta
            q.alpha = (a + b) / math.sqrt(2)
            q.beta = (a - b) / math.sqrt(2)
            q.normalize()
        elif gate == GateType.X and len(targets) == 1:
            q = self.qubits[targets[0]]
            q.alpha, q.beta = q.beta, q.alpha
        elif gate == GateType.Z and len(targets) == 1:
            q = self.qubits[targets[0]]
            q.beta = -q.beta
        elif gate == GateType.CNOT and len(targets) == 2:
            control, target = targets[0], targets[1]
            if abs(self.qubits[control].beta) > 0.5:
                self.qubits[target].alpha, self.qubits[target].beta = self.qubits[target].beta, self.qubits[target].alpha

    def measure(self, idx: int) -> int:
        q = self.qubits[idx]
        p0 = abs(q.alpha)**2
        return 0 if random.random() < p0 else 1

    def stats(self) -> Dict:
        return {"qubits": len(self.qubits), "gates": len(self.gates)}

def run():
    qc = QuantumCircuit()
    qc.add_qubit(Qubit(complex(1,0), complex(0,0)))
    qc.apply(GateType.H, [0])
    print("Measure:", qc.measure(0))
    print(qc.stats())

if __name__ == "__main__":
    run()
