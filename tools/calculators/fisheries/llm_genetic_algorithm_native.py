"""Genetic Algorithm — selection, crossover, mutation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Tuple, Optional
from enum import Enum, auto
import random
import math

@dataclass
class Individual:
    genes: List[float]
    fitness: float = 0.0

    def copy(self) -> "Individual":
        return Individual(list(self.genes), self.fitness)

class GeneticAlgorithm:
    def __init__(self, population_size: int = 50, mutation_rate: float = 0.1, crossover_rate: float = 0.8, elitism: int = 2):
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elitism = elitism
        self.population: List[Individual] = []
        self.generation: int = 0
        self.best_fitness_history: List[float] = []
        self.fitness_fn: Optional[Callable[[List[float]], float]] = None

    def initialize(self, gene_count: int, gene_range: Tuple[float, float] = (-1, 1)):
        lo, hi = gene_range
        self.population = [Individual([random.uniform(lo, hi) for _ in range(gene_count)]) for _ in range(self.population_size)]

    def evaluate(self, fitness_fn: Callable[[List[float]], float]):
        self.fitness_fn = fitness_fn
        for ind in self.population:
            ind.fitness = fitness_fn(ind.genes)

    def _select(self) -> Individual:
        # Tournament selection
        tournament = random.sample(self.population, min(3, len(self.population)))
        return max(tournament, key=lambda x: x.fitness).copy()

    def _crossover(self, a: Individual, b: Individual) -> Tuple[Individual, Individual]:
        if random.random() > self.crossover_rate:
            return a.copy(), b.copy()
        point = random.randint(1, len(a.genes) - 1)
        child1 = Individual(a.genes[:point] + b.genes[point:])
        child2 = Individual(b.genes[:point] + a.genes[point:])
        return child1, child2

    def _mutate(self, ind: Individual, gene_range: Tuple[float, float] = (-1, 1)):
        lo, hi = gene_range
        for i in range(len(ind.genes)):
            if random.random() < self.mutation_rate:
                ind.genes[i] += random.gauss(0, abs(hi - lo) * 0.1)
                ind.genes[i] = max(lo, min(hi, ind.genes[i]))

    def evolve(self, generations: int = 100, gene_range: Tuple[float, float] = (-1, 1)):
        for _ in range(generations):
            self.population.sort(key=lambda x: x.fitness, reverse=True)
            self.best_fitness_history.append(self.population[0].fitness)
            new_pop = [self.population[i].copy() for i in range(self.elitism)]
            while len(new_pop) < self.population_size:
                parent1 = self._select()
                parent2 = self._select()
                c1, c2 = self._crossover(parent1, parent2)
                self._mutate(c1, gene_range)
                self._mutate(c2, gene_range)
                c1.fitness = self.fitness_fn(c1.genes) if self.fitness_fn else 0
                c2.fitness = self.fitness_fn(c2.genes) if self.fitness_fn else 0
                new_pop.extend([c1, c2])
            self.population = new_pop[:self.population_size]
            self.generation += 1

    def get_best(self) -> Individual:
        return max(self.population, key=lambda x: x.fitness)

    def stats(self) -> Dict:
        return {"generation": self.generation, "population": len(self.population), "best_fitness": self.get_best().fitness, "avg_fitness": sum(i.fitness for i in self.population) / len(self.population)}

def run():
    ga = GeneticAlgorithm(population_size=30, mutation_rate=0.1)
    ga.initialize(5, (-5, 5))
    def fitness(genes):
        return -sum((x - 2) ** 2 for x in genes)
    ga.evaluate(fitness)
    ga.evolve(50)
    best = ga.get_best()
    print("Best:", best.genes, best.fitness)
    print(ga.stats())

if __name__ == "__main__":
    run()
