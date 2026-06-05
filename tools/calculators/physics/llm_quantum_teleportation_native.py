"""Quantum Teleportation — protocol simulation, state transfer, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math, random, cmath

@dataclass
class QuantumTeleportation:
    """Simulates the quantum teleportation protocol using classical communication."""
    source_state: Tuple[complex, complex] = (complex(1,0), complex(0,0))

    def entangle(self) -> Tuple[Tuple[complex, complex], Tuple[complex, complex]]:
        a = 1 / math.sqrt(2)
        return (complex(a, 0), complex(0, 0)), (complex(0, 0), complex(a, 0))

    def bell_measurement(self, psi: Tuple[complex, complex], phi: Tuple[complex, complex]) -> Tuple[int, int]:
        p00 = abs(psi[0] * phi[0] + psi[1] * phi[1])**2
        p01 = abs(psi[0] * phi[1] + psi[1] * phi[0])**2
        r = random.random()
        if r < p00:
            return 0, 0
        elif r < p00 + p01:
            return 0, 1
        elif r < p00 + p01 + 0.25:
            return 1, 0
        return 1, 1

    def apply_correction(self, state: Tuple[complex, complex], m1: int, m2: int) -> Tuple[complex, complex]:
        a, b = state
        if m2 == 1:
            a, b = b, a
        if m1 == 1:
            b = -b
        return a, b

    def fidelity(self, a: Tuple[complex, complex], b: Tuple[complex, complex]) -> float:
        return abs(a[0].conjugate() * b[0] + a[1].conjugate() * b[1])**2

    def stats(self) -> Dict:
        return {"source": str(self.source_state)}

def run():
    tp = QuantumTeleportation((complex(0.8, 0), complex(0.6, 0)))
    ent = tp.entangle()
    m = tp.bell_measurement(tp.source_state, ent[0])
    corrected = tp.apply_correction(ent[1], m[0], m[1])
    print("Fidelity:", tp.fidelity(tp.source_state, corrected))
    print(tp.stats())

if __name__ == "__main__":
    run()
