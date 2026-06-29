
"""
agent_evolution_engine_native.py
MAGNATRIX-OS — Agent Evolution Engine

Inspired by A-Evolve (A-EVO-Lab): "The PyTorch for Agentic AI".
Universal infrastructure for evolving any agent across any domain
using any evolution algorithm with zero human intervention.

Core API: Evolver(agent, benchmark).run(cycles)
Pure Python standard library.
"""

import os
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto


class EvolutionPhase(Enum):
    SEED = auto()
    MUTATE = auto()
    EVALUATE = auto()
    SELECT = auto()
    BREED = auto()
    CONVERGE = auto()


@dataclass
class AgentGenome:
    """Represents an agent's evolvable configuration."""
    agent_id: str
    system_prompt: str = ""
    skills: Dict[str, str] = field(default_factory=dict)
    memory_entries: List[Dict] = field(default_factory=list)
    hyperparams: Dict[str, Any] = field(default_factory=dict)
    fitness: float = 0.0
    generation: int = 0
    parent_ids: List[str] = field(default_factory=list)
    mutation_log: List[str] = field(default_factory=list)

    def fingerprint(self) -> str:
        content = json.dumps({
            "prompt": self.system_prompt,
            "skills": sorted(self.skills.items()),
            "hyperparams": self.hyperparams,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class EvolutionConfig:
    """Configuration for an evolution run."""
    cycles: int = 10
    population_size: int = 5
    mutation_rate: float = 0.3
    crossover_rate: float = 0.5
    elite_ratio: float = 0.2
    convergence_threshold: float = 0.01
    max_generations: int = 50
    seed_workspace: str = "./seed_workspace"
    output_workspace: str = "./evolved_workspace"
    git_tag_prefix: str = "evo"


class AgentEvolutionEngine:
    """Core evolver: Base Agent → SOTA Agent."""

    def __init__(self, config: Optional[EvolutionConfig] = None):
        self.config = config or EvolutionConfig()
        self.population: List[AgentGenome] = []
        self.history: List[Dict] = []
        self.phase = EvolutionPhase.SEED
        self._callbacks: Dict[EvolutionPhase, List[Callable]] = {
            p: [] for p in EvolutionPhase
        }

    def register_callback(self, phase: EvolutionPhase, fn: Callable) -> None:
        self._callbacks[phase].append(fn)

    def _emit(self, phase: EvolutionPhase, data: Dict) -> None:
        for fn in self._callbacks[phase]:
            try:
                fn(data)
            except Exception:
                pass

    def seed(self, base_agent: Dict[str, Any]) -> AgentGenome:
        """Create initial genome from a base agent workspace."""
        genome = AgentGenome(
            agent_id=f"gen0_seed_{int(time.time())}",
            system_prompt=base_agent.get("system_prompt", ""),
            skills=base_agent.get("skills", {}),
            memory_entries=base_agent.get("memory", []),
            hyperparams=base_agent.get("hyperparams", {}),
            generation=0,
        )
        self.population = [genome]
        self.phase = EvolutionPhase.SEED
        self._emit(EvolutionPhase.SEED, {"genome": asdict(genome)})
        return genome

    def evolve(self, benchmark_fn: Callable[[AgentGenome], float]) -> AgentGenome:
        """Run full evolution cycle."""
        cfg = self.config
        for cycle in range(cfg.cycles):
            self.phase = EvolutionPhase.MUTATE
            self._mutate_population()
            self._emit(EvolutionPhase.MUTATE, {"cycle": cycle, "population": len(self.population)})

            self.phase = EvolutionPhase.EVALUATE
            self._evaluate_population(benchmark_fn)
            self._emit(EvolutionPhase.EVALUATE, {"cycle": cycle, "fitnesses": [g.fitness for g in self.population]})

            self.phase = EvolutionPhase.SELECT
            self._select_elite()
            self._emit(EvolutionPhase.SELECT, {"cycle": cycle, "elite": len(self.population)})

            self.phase = EvolutionPhase.BREED
            self._breed_next_generation()
            self._emit(EvolutionPhase.BREED, {"cycle": cycle, "population": len(self.population)})

            # Check convergence
            if self._has_converged():
                self.phase = EvolutionPhase.CONVERGE
                self._emit(EvolutionPhase.CONVERGE, {"cycle": cycle, "reason": "converged"})
                break

        best = max(self.population, key=lambda g: g.fitness)
        self._tag_genome(best, f"{cfg.git_tag_prefix}-final")
        return best

    def _mutate_population(self) -> None:
        from .mutation_engine_native import MutationEngine
        mutator = MutationEngine()
        mutated = []
        for genome in self.population:
            if len(self.population) < self.config.population_size:
                for _ in range(2):
                    child = mutator.mutate(genome, rate=self.config.mutation_rate)
                    mutated.append(child)
        self.population.extend(mutated)

    def _evaluate_population(self, benchmark_fn: Callable[[AgentGenome], float]) -> None:
        for genome in self.population:
            genome.fitness = benchmark_fn(genome)

    def _select_elite(self) -> None:
        self.population.sort(key=lambda g: g.fitness, reverse=True)
        elite_count = max(1, int(len(self.population) * self.config.elite_ratio))
        self.population = self.population[:elite_count]

    def _breed_next_generation(self) -> None:
        while len(self.population) < self.config.population_size:
            parents = self.population[:2] if len(self.population) >= 2 else self.population * 2
            child = self._crossover(parents[0], parents[1])
            self.population.append(child)

    def _crossover(self, parent1: AgentGenome, parent2: AgentGenome) -> AgentGenome:
        child = AgentGenome(
            agent_id=f"gen{parent1.generation + 1}_cross_{int(time.time() * 1000) % 10000}",
            system_prompt=parent1.system_prompt if hash(parent1.agent_id) % 2 else parent2.system_prompt,
            skills={**parent1.skills, **parent2.skills},
            memory_entries=parent1.memory_entries + parent2.memory_entries,
            hyperparams=self._blend_hyperparams(parent1.hyperparams, parent2.hyperparams),
            generation=max(parent1.generation, parent2.generation) + 1,
            parent_ids=[parent1.agent_id, parent2.agent_id],
        )
        return child

    def _blend_hyperparams(self, h1: Dict, h2: Dict) -> Dict:
        blended = {}
        for k in set(h1) | set(h2):
            v1 = h1.get(k, 0)
            v2 = h2.get(k, 0)
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                blended[k] = (v1 + v2) / 2
            else:
                blended[k] = v1 if hash(k) % 2 else v2
        return blended

    def _has_converged(self) -> bool:
        if len(self.population) < 2:
            return False
        fitnesses = [g.fitness for g in self.population]
        spread = max(fitnesses) - min(fitnesses)
        return spread < self.config.convergence_threshold

    def _tag_genome(self, genome: AgentGenome, tag: str) -> None:
        genome.mutation_log.append(f"tagged:{tag}:{datetime.now().isoformat()}")

    def get_best(self) -> Optional[AgentGenome]:
        if not self.population:
            return None
        return max(self.population, key=lambda g: g.fitness)

    def to_dict(self) -> Dict:
        return {
            "phase": self.phase.name,
            "population_size": len(self.population),
            "best_fitness": max((g.fitness for g in self.population), default=0.0),
            "history": self.history,
            "config": asdict(self.config),
        }


__all__ = ["AgentEvolutionEngine", "AgentGenome", "EvolutionConfig", "EvolutionPhase"]
