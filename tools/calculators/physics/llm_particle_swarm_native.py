"""Particle Swarm Optimization — PSO, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Optional
from enum import Enum, auto
import random
import math

@dataclass
class Particle:
    position: List[float]
    velocity: List[float]
    best_position: List[float] = field(default_factory=list)
    best_fitness: float = float('-inf')
    fitness: float = 0.0

class ParticleSwarmOptimizer:
    def __init__(self, num_particles: int = 30, w: float = 0.7, c1: float = 1.5, c2: float = 1.5):
        self.num_particles = num_particles
        self.w = w
        self.c1 = c1
        self.c2 = c2
        self.particles: List[Particle] = []
        self.global_best_position: List[float] = []
        self.global_best_fitness: float = float('-inf')
        self.iterations = 0
        self.bounds: Optional[List[Tuple[float, float]]] = None

    def initialize(self, dim: int, bounds: List[Tuple[float, float]]):
        self.bounds = bounds
        self.particles = []
        for _ in range(self.num_particles):
            pos = [random.uniform(bounds[i][0], bounds[i][1]) for i in range(dim)]
            vel = [random.uniform(-1, 1) for _ in range(dim)]
            p = Particle(pos, vel, list(pos), float('-inf'))
            self.particles.append(p)
        self.global_best_position = [0.0] * dim

    def optimize(self, fitness_fn: Callable[[List[float]], float], iterations: int = 100):
        for _ in range(iterations):
            for p in self.particles:
                p.fitness = fitness_fn(p.position)
                if p.fitness > p.best_fitness:
                    p.best_fitness = p.fitness
                    p.best_position = list(p.position)
                if p.fitness > self.global_best_fitness:
                    self.global_best_fitness = p.fitness
                    self.global_best_position = list(p.position)
            for p in self.particles:
                for i in range(len(p.position)):
                    r1, r2 = random.random(), random.random()
                    p.velocity[i] = (self.w * p.velocity[i] +
                                     self.c1 * r1 * (p.best_position[i] - p.position[i]) +
                                     self.c2 * r2 * (self.global_best_position[i] - p.position[i]))
                    p.position[i] += p.velocity[i]
                    if self.bounds:
                        p.position[i] = max(self.bounds[i][0], min(self.bounds[i][1], p.position[i]))
            self.iterations += 1

    def stats(self) -> Dict:
        return {"iterations": self.iterations, "particles": len(self.particles), "best_fitness": self.global_best_fitness}

def run():
    pso = ParticleSwarmOptimizer(num_particles=20)
    pso.initialize(3, [(-5, 5), (-5, 5), (-5, 5)])
    def fitness(pos):
        return -sum((x - 2) ** 2 for x in pos)
    pso.optimize(fitness, 100)
    print("Best:", pso.global_best_position, pso.global_best_fitness)
    print(pso.stats())

if __name__ == "__main__":
    run()
