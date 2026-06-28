#!/usr/bin/env python3
"""Quantum Simulator for MAGNATRIX-OS."""
from __future__ import annotations
import cmath, math, random
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

@dataclass
class Qubit:
    alpha: complex = 1+0j
    beta: complex = 0+0j
    def measure(self) -> int:
        p0 = abs(self.alpha)**2
        return 0 if random.random() < p0 else 1
    def apply(self, gate: 'QuantumGate') -> 'Qubit':
        a = gate.matrix[0][0]*self.alpha + gate.matrix[0][1]*self.beta
        b = gate.matrix[1][0]*self.alpha + gate.matrix[1][1]*self.beta
        norm = math.sqrt(abs(a)**2 + abs(b)**2)
        return Qubit(a/norm, b/norm)
    def to_dict(self): return {"alpha": str(self.alpha), "beta": str(self.beta)}

@dataclass
class QuantumGate:
    name: str
    matrix: List[List[complex]]
    def to_dict(self): return {"name": self.name, "matrix": [[str(c) for c in row] for row in self.matrix]}

class QuantumCircuit:
    def __init__(self, num_qubits: int = 2):
        self.num_qubits = num_qubits
        self.qubits = [Qubit() for _ in range(num_qubits)]
        self.gates: List[Tuple[int, QuantumGate]] = []
    def add_gate(self, qubit_idx: int, gate: QuantumGate):
        self.gates.append((qubit_idx, gate))
    def run(self) -> List[int]:
        for idx, gate in self.gates:
            self.qubits[idx] = self.qubits[idx].apply(gate)
        return [q.measure() for q in self.qubits]
    def to_dict(self):
        return {"num_qubits": self.num_qubits, "gates": [(i, g.to_dict()) for i,g in self.gates], "results": self.run()}

class QuantumSimulator:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.gates = {
            "H": QuantumGate("Hadamard", [[1/math.sqrt(2), 1/math.sqrt(2)], [1/math.sqrt(2), -1/math.sqrt(2)]]),
            "X": QuantumGate("Pauli-X", [[0,1],[1,0]]),
            "Y": QuantumGate("Pauli-Y", [[0,-1j],[1j,0]]),
            "Z": QuantumGate("Pauli-Z", [[1,0],[0,-1]]),
        }
    def create_circuit(self, num_qubits: int = 2) -> QuantumCircuit:
        return QuantumCircuit(num_qubits)
    def run_experiment(self, num_qubits: int = 2, shots: int = 100) -> Dict[str, Any]:
        circuit = self.create_circuit(num_qubits)
        circuit.add_gate(0, self.gates["H"])
        counts = {}
        for _ in range(shots):
            result = tuple(circuit.run())
            counts[result] = counts.get(result, 0) + 1
        return {"shots": shots, "counts": {str(k): v for k,v in counts.items()}}
    def to_dict(self):
        return {"gates": list(self.gates.keys())}
