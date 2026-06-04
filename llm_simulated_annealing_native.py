"""Simulated Annealing — combinatorial optimization, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Any, Optional
from enum import Enum, auto
import random
import math

class SAState:
    def __init__(self, value: Any):
        self.value = value

class SimulatedAnnealing:
    def __init__(self, initial_temp: float = 100.0, cooling_rate: float = 0.95, min_temp: float = 0.01):
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate
        self.min_temp = min_temp
        self.temperature = initial_temp
        self.current: Optional[SAState] = None
        self.best: Optional[SAState] = None
        self.current_energy = 0.0
        self.best_energy = float('inf')
        self.iterations = 0

    def initialize(self, initial_state: Any, energy_fn: Callable[[Any], float]):
        self.current = SAState(initial_state)
        self.best = SAState(copy.deepcopy(initial_state) if hasattr(initial_state, '__deepcopy__') else initial_state)
        self.current_energy = energy_fn(initial_state)
        self.best_energy = self.current_energy

    def run(self, neighbor_fn: Callable[[Any], Any], energy_fn: Callable[[Any], float], max_iter: int = 1000) -> SAState:
        for _ in range(max_iter):
            if self.temperature < self.min_temp:
                break
            neighbor = SAState(neighbor_fn(self.current.value))
            neighbor_energy = energy_fn(neighbor.value)
            delta = neighbor_energy - self.current_energy
            if delta < 0 or random.random() < math.exp(-delta / self.temperature):
                self.current = neighbor
                self.current_energy = neighbor_energy
                if self.current_energy < self.best_energy:
                    self.best = SAState(copy.deepcopy(neighbor.value) if hasattr(neighbor.value, '__deepcopy__') else neighbor.value)
                    self.best_energy = self.current_energy
            self.temperature *= self.cooling_rate
            self.iterations += 1
        return self.best

    def stats(self) -> Dict:
        return {"temperature": self.temperature, "iterations": self.iterations, "best_energy": self.best_energy, "current_energy": self.current_energy}

def run():
    import copy
    def energy(state):
        return sum((x - 3) ** 2 for x in state)
    def neighbor(state):
        new = list(state)
        i = random.randint(0, len(new) - 1)
        new[i] += random.gauss(0, 0.5)
        return new
    sa = SimulatedAnnealing(initial_temp=100, cooling_rate=0.98)
    sa.initialize([0, 0, 0], energy)
    best = sa.run(neighbor, energy, max_iter=500)
    print("Best:", best.value, sa.best_energy)
    print(sa.stats())

if __name__ == "__main__":
    run()
