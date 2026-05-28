#!/usr/bin/env python3
"""
Quantum Algorithms -- MAGNATRIX-OS Phase 5
Path: ai/quantum_algo_native.py
License: AGPL-3.0
"""

from __future__ import annotations

import cmath
import math
import random
from typing import Dict, List, Optional


class StateVector:
    def __init__(self, n_qubits: int, amplitudes: Optional[List[complex]] = None):
        self.n = n_qubits
        self.N = 1 << n_qubits
        if amplitudes is None:
            self.amp = [0j] * self.N
            self.amp[0] = 1.0
        else:
            self.amp = list(amplitudes)
        self._normalize()

    def _normalize(self) -> None:
        norm = math.sqrt(sum(abs(a) ** 2 for a in self.amp))
        if norm > 0:
            self.amp = [a / norm for a in self.amp]

    def probs(self) -> List[float]:
        return [abs(a) ** 2 for a in self.amp]

    def apply_matrix(self, matrix: List[List[complex]], targets: List[int]) -> "StateVector":
        m = len(matrix)
        new_amp = self.amp[:]
        for i in range(self.N):
            sub_idx = 0
            for t, tgt in enumerate(targets):
                if (i >> tgt) & 1:
                    sub_idx |= (1 << t)
            for j in range(m):
                val = 0j
                for k in range(m):
                    src = i
                    for t, tgt in enumerate(targets):
                        src &= ~(1 << tgt)
                    for t, tgt in enumerate(targets):
                        if (k >> t) & 1:
                            src |= (1 << tgt)
                    val += matrix[j][k] * self.amp[src]
                dst = i
                for t, tgt in enumerate(targets):
                    dst &= ~(1 << tgt)
                for t, tgt in enumerate(targets):
                    if (j >> t) & 1:
                        dst |= (1 << tgt)
                new_amp[dst] = val
        return StateVector(self.n, new_amp)

    def measure(self) -> int:
        p = random.random()
        cum = 0.0
        for i, a in enumerate(self.amp):
            cum += abs(a) ** 2
            if p <= cum:
                return i
        return self.N - 1


H = [[1 / math.sqrt(2), 1 / math.sqrt(2)],
     [1 / math.sqrt(2), -1 / math.sqrt(2)]]

CNOT = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]]


class GroverSearch:
    def __init__(self, n_qubits: int):
        self.n = n_qubits
        self.N = 1 << n_qubits

    def oracle(self, state: StateVector, target_idx: int) -> StateVector:
        new_amp = state.amp[:]
        new_amp[target_idx] *= -1
        return StateVector(self.n, new_amp)

    def diffusion(self, state: StateVector) -> StateVector:
        s = StateVector(self.n)
        s.amp = state.amp[:]
        for q in range(self.n):
            s = s.apply_matrix(H, [q])
        new_amp = s.amp[:]
        new_amp[0] = 2 * new_amp[0] - sum(s.amp)
        for i in range(1, self.N):
            new_amp[i] = -s.amp[i]
        s = StateVector(self.n, new_amp)
        for q in range(self.n):
            s = s.apply_matrix(H, [q])
        return s

    def search(self, target_idx: int, iterations: Optional[int] = None) -> Dict:
        if iterations is None:
            iterations = int(math.pi / 4 * math.sqrt(self.N))
        state = StateVector(self.n)
        for q in range(self.n):
            state = state.apply_matrix(H, [q])
        for _ in range(iterations):
            state = self.oracle(state, target_idx)
            state = self.diffusion(state)
        probs = state.probs()
        return {
            "target": target_idx,
            "iterations": iterations,
            "probability": probs[target_idx],
            "classical_prob": 1.0 / self.N,
            "speedup": probs[target_idx] * self.N,
        }


class QAOA:
    def __init__(self, graph: Dict[int, List[int]]):
        self.graph = graph
        self.nodes = sorted(graph.keys())
        self.n = len(self.nodes)
        self.N = 1 << self.n
        self._idx = {node: i for i, node in enumerate(self.nodes)}

    def _cut_value(self, bitstring: int) -> int:
        val = 0
        for u in self.nodes:
            ui = self._idx[u]
            u_bit = (bitstring >> ui) & 1
            for v in self.graph.get(u, []):
                if v in self._idx:
                    vi = self._idx[v]
                    if vi > ui:
                        v_bit = (bitstring >> vi) & 1
                        if u_bit != v_bit:
                            val += 1
        return val

    def solve(self, shots: int = 1000) -> Dict:
        best_gamma, best_beta = 0.0, 0.0
        best_exp = -float("inf")
        for gamma in [i * math.pi / 10 for i in range(21)]:
            for beta in [i * math.pi / 10 for i in range(21)]:
                state = StateVector(self.n)
                for q in range(self.n):
                    state = state.apply_matrix(H, [q])
                new_amp = []
                for s in range(self.N):
                    new_amp.append(state.amp[s] * cmath.exp(-1j * gamma * self._cut_value(s)))
                state = StateVector(self.n, new_amp)
                rx = [[cmath.cos(beta / 2), -1j * cmath.sin(beta / 2)],
                      [-1j * cmath.sin(beta / 2), cmath.cos(beta / 2)]]
                for q in range(self.n):
                    state = state.apply_matrix(rx, [q])
                exp = sum(state.probs()[s] * self._cut_value(s) for s in range(self.N))
                if exp > best_exp:
                    best_exp = exp
                    best_gamma = gamma
                    best_beta = beta
        # Rebuild best
        state = StateVector(self.n)
        for q in range(self.n):
            state = state.apply_matrix(H, [q])
        new_amp = []
        for s in range(self.N):
            new_amp.append(state.amp[s] * cmath.exp(-1j * best_gamma * self._cut_value(s)))
        state = StateVector(self.n, new_amp)
        rx = [[cmath.cos(best_beta / 2), -1j * cmath.sin(best_beta / 2)],
              [-1j * cmath.sin(best_beta / 2), cmath.cos(best_beta / 2)]]
        for q in range(self.n):
            state = state.apply_matrix(rx, [q])
        probs = state.probs()
        best_s = max(range(self.N), key=lambda i: probs[i])
        return {
            "bitstring": format(best_s, "0" + str(self.n) + "b"),
            "cut_value": self._cut_value(best_s),
            "gamma": best_gamma,
            "beta": best_beta,
            "expectation": best_exp,
            "probability": probs[best_s],
        }


class VQE:
    def __init__(self):
        self.n = 2

    def _ansatz(self, theta: float, phi: float) -> StateVector:
        state = StateVector(self.n)
        ry = [[cmath.cos(theta / 2), -cmath.sin(theta / 2)],
              [cmath.sin(theta / 2), cmath.cos(theta / 2)]]
        state = state.apply_matrix(ry, [0])
        state = state.apply_matrix(CNOT, [0, 1])
        ry2 = [[cmath.cos(phi / 2), -cmath.sin(phi / 2)],
               [cmath.sin(phi / 2), cmath.cos(phi / 2)]]
        state = state.apply_matrix(ry2, [1])
        return state

    def _energy(self, state: StateVector, J: float = 1.0) -> float:
        probs = state.probs()
        energy = 0.0
        for s in range(4):
            b0 = (s >> 0) & 1
            b1 = (s >> 1) & 1
            zz = 1 if b0 == b1 else -1
            energy += probs[s] * J * zz
        return energy

    def solve(self, steps: int = 100) -> Dict:
        theta, phi = random.random() * math.pi, random.random() * math.pi
        lr = 0.1
        best_energy = float("inf")
        best = (theta, phi)
        for _ in range(steps):
            state = self._ansatz(theta, phi)
            E = self._energy(state)
            if E < best_energy:
                best_energy = E
                best = (theta, phi)
            eps = 0.01
            state_dth = self._ansatz(theta + eps, phi)
            state_dph = self._ansatz(theta, phi + eps)
            dE_dth = (self._energy(state_dth) - E) / eps
            dE_dph = (self._energy(state_dph) - E) / eps
            theta -= lr * dE_dth
            phi -= lr * dE_dph
        return {
            "energy": best_energy,
            "theta": best[0],
            "phi": best[1],
            "state": self._ansatz(*best).probs(),
        }


class QFT:
    def __init__(self, n_qubits: int):
        self.n = n_qubits
        self.N = 1 << n_qubits

    def _cphase(self, state: StateVector, control: int, target: int, k: int) -> StateVector:
        new_amp = state.amp[:]
        for i in range(self.N):
            if ((i >> control) & 1) and ((i >> target) & 1):
                new_amp[i] *= cmath.exp(2j * math.pi / (1 << k))
        return StateVector(self.n, new_amp)

    def transform(self, state: StateVector) -> StateVector:
        for q in range(self.n):
            state = state.apply_matrix(H, [q])
            for j in range(q + 1, self.n):
                state = self._cphase(state, j, q, j - q + 1)
        # Swap
        for i in range(self.n // 2):
            j = self.n - 1 - i
            if i != j:
                new_amp = state.amp[:]
                for s in range(self.N):
                    bi = (s >> i) & 1
                    bj = (s >> j) & 1
                    if bi != bj:
                        swapped = s ^ (1 << i) ^ (1 << j)
                        if s < swapped:
                            new_amp[s], new_amp[swapped] = new_amp[swapped], new_amp[s]
                state = StateVector(self.n, new_amp)
        return state

    def inverse(self, state: StateVector) -> StateVector:
        new_amp = [0j] * self.N
        for k in range(self.N):
            for j in range(self.N):
                new_amp[k] += state.amp[j] * cmath.exp(-2j * math.pi * j * k / self.N)
        return StateVector(self.n, [a / self.N for a in new_amp])


def _self_test():
    print("=" * 55)
    print("Quantum Algorithms -- Self Test")
    print("=" * 55)
    passed = 0
    total = 6

    print("[Test 1] State vector normalization")
    sv = StateVector(2)
    assert abs(sum(sv.probs()) - 1.0) < 1e-10
    passed += 1
    print("  PASS")

    print("[Test 2] Grover search (3 qubits)")
    grover = GroverSearch(3)
    result = grover.search(target_idx=5)
    print("  P(target=5) = " + str(round(result["probability"], 3)))
    print("  Speedup = " + str(round(result["speedup"], 1)) + "x")
    assert result["probability"] > result["classical_prob"] * 2
    passed += 1
    print("  PASS")

    print("[Test 3] QAOA max-cut")
    graph = {0: [1, 2], 1: [0, 2], 2: [0, 1]}
    qaoa = QAOA(graph)
    sol = qaoa.solve()
    print("  Bitstring: " + sol["bitstring"] + ", Cut: " + str(sol["cut_value"]))
    assert sol["cut_value"] >= 2
    passed += 1
    print("  PASS")

    print("[Test 4] VQE ground state")
    vqe = VQE()
    result = vqe.solve(steps=100)
    print("  Energy: " + str(round(result["energy"], 4)))
    assert result["energy"] < 0
    passed += 1
    print("  PASS")

    print("[Test 5] QFT")
    qft = QFT(2)
    state = StateVector(2)
    state.amp = [1.0, 0.0, 0.0, 0.0]
    transformed = qft.transform(state)
    probs = transformed.probs()
    assert all(abs(p - 0.25) < 0.01 for p in probs)
    passed += 1
    print("  PASS")

    print("[Test 6] QFT inverse")
    inv = qft.inverse(transformed)
    probs_inv = inv.probs()
    assert probs_inv[0] > 0.95
    passed += 1
    print("  PASS")

    print("")
    print("PASS: " + str(passed) + "/" + str(total))
    print("=" * 55)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
