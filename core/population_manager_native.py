
"""
population_manager_native.py
MAGNATRIX-OS — Population Manager

Population-based evolutionary management: diversity tracking,
convergence detection, extinction events, and niche creation.
Inspired by A-Evolve population dynamics.
Pure Python standard library.
"""

import random
import math
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from pathlib import Path
import json


@dataclass
class PopulationStats:
    size: int = 0
    generation: int = 0
    avg_fitness: float = 0.0
    max_fitness: float = 0.0
    min_fitness: float = 0.0
    std_fitness: float = 0.0
    diversity_score: float = 0.0
    convergence_ratio: float = 0.0
    elite_count: int = 0


class PopulationManager:
    """Manage evolutionary population dynamics."""

    def __init__(self, max_size: int = 20, min_diversity: float = 0.1):
        self.max_size = max_size
        self.min_diversity = min_diversity
        self.population: List = []
        self.generation = 0
        self.extinction_history: List[int] = []
        self.stats_history: List[PopulationStats] = []

    def add(self, genome) -> bool:
        if len(self.population) >= self.max_size:
            return False
        self.population.append(genome)
        return True

    def replace(self, old_genome, new_genome) -> bool:
        for i, g in enumerate(self.population):
            if getattr(g, "agent_id", id(g)) == getattr(old_genome, "agent_id", id(old_genome)):
                self.population[i] = new_genome
                return True
        return False

    def cull(self, fitness_threshold: Optional[float] = None) -> int:
        """Remove low-fitness individuals."""
        if fitness_threshold is not None:
            before = len(self.population)
            self.population = [g for g in self.population if getattr(g, "fitness", 0) >= fitness_threshold]
            return before - len(self.population)
        # Cull bottom 50%
        self.population.sort(key=lambda g: getattr(g, "fitness", 0), reverse=True)
        before = len(self.population)
        self.population = self.population[:max(2, len(self.population) // 2)]
        return before - len(self.population)

    def extinct_event(self, preserve_elite: int = 1) -> List:
        """Mass extinction: keep only elite, clear rest."""
        self.population.sort(key=lambda g: getattr(g, "fitness", 0), reverse=True)
        survivors = self.population[:preserve_elite]
        extinct = self.population[preserve_elite:]
        self.population = survivors
        self.extinction_history.append(len(extinct))
        return extinct

    def compute_diversity(self) -> float:
        """Measure genetic diversity using fingerprint Hamming distance."""
        if len(self.population) < 2:
            return 1.0
        fingerprints = []
        for g in self.population:
            fp = getattr(g, "fingerprint", lambda: str(id(g)))()
            fingerprints.append(fp)
        # Simple diversity: ratio of unique fingerprints
        unique = len(set(fingerprints))
        return unique / len(fingerprints)

    def compute_stats(self) -> PopulationStats:
        fitnesses = [getattr(g, "fitness", 0.0) for g in self.population]
        if not fitnesses:
            return PopulationStats()
        avg = sum(fitnesses) / len(fitnesses)
        max_f = max(fitnesses)
        min_f = min(fitnesses)
        variance = sum((f - avg) ** 2 for f in fitnesses) / len(fitnesses)
        std = math.sqrt(variance)
        diversity = self.compute_diversity()
        convergence = 1.0 - diversity
        elite_count = sum(1 for f in fitnesses if f > avg + std)
        stats = PopulationStats(
            size=len(self.population),
            generation=self.generation,
            avg_fitness=avg,
            max_fitness=max_f,
            min_fitness=min_f,
            std_fitness=std,
            diversity_score=diversity,
            convergence_ratio=convergence,
            elite_count=elite_count,
        )
        self.stats_history.append(stats)
        return stats

    def check_stagnation(self, window: int = 5, threshold: float = 0.001) -> bool:
        """Check if population has stagnated."""
        if len(self.stats_history) < window:
            return False
        recent = self.stats_history[-window:]
        max_f = [s.max_fitness for s in recent]
        return max(max_f) - min(max_f) < threshold

    def promote_niche(self, skill_focus: str, count: int = 2) -> List:
        """Promote individuals with specific skill focus."""
        niche = [g for g in self.population if skill_focus in getattr(g, "skills", {})]
        niche.sort(key=lambda g: getattr(g, "fitness", 0), reverse=True)
        return niche[:count]

    def save_checkpoint(self, path: str) -> None:
        data = {
            "generation": self.generation,
            "population_size": len(self.population),
            "extinction_history": self.extinction_history,
            "latest_stats": self.compute_stats().__dict__ if self.population else {},
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def to_dict(self) -> Dict:
        return {
            "size": len(self.population),
            "max_size": self.max_size,
            "generation": self.generation,
            "diversity": self.compute_diversity(),
            "stats": self.compute_stats().__dict__ if self.population else {},
            "extinctions": len(self.extinction_history),
        }


__all__ = ["PopulationManager", "PopulationStats"]
