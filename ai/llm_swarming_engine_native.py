"""LLM Swarming Engine — Native Python (stdlib only)."""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto

class SwarmRole(Enum):
    LEADER = auto()
    FOLLOWER = auto()
    EXPLORER = auto()
    COORDINATOR = auto()

@dataclass
class SwarmAgent:
    id: str
    role: SwarmRole
    position: List[float] = field(default_factory=list)
    velocity: List[float] = field(default_factory=list)
    fitness: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class SwarmingEngine:
    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed)
        self._agents: List[SwarmAgent] = []
        self._best_position: Optional[List[float]] = None
        self._best_fitness: float = float('-inf')

    def add_agent(self, agent: SwarmAgent) -> None:
        self._agents.append(agent)

    def evaluate(self, fitness_fn: Callable[[List[float]], float]) -> None:
        for agent in self._agents:
            agent.fitness = fitness_fn(agent.position)
            if agent.fitness > self._best_fitness:
                self._best_fitness = agent.fitness
                self._best_position = list(agent.position)

    def update_positions(self, inertia: float = 0.7, cognitive: float = 1.5, social: float = 1.5) -> None:
        for agent in self._agents:
            for i in range(len(agent.position)):
                r1, r2 = self._rng.random(), self._rng.random()
                cognitive_component = cognitive * r1 * (self._best_position[i] - agent.position[i]) if self._best_position else 0
                social_component = social * r2 * (self._best_position[i] - agent.position[i]) if self._best_position else 0
                agent.velocity[i] = inertia * agent.velocity[i] + cognitive_component + social_component
                agent.position[i] += agent.velocity[i]

    def get_best(self) -> Optional[SwarmAgent]:
        if not self._agents:
            return None
        return max(self._agents, key=lambda a: a.fitness)

    def get_stats(self) -> Dict[str, Any]:
        return {"agents": len(self._agents), "best_fitness": self._best_fitness, "avg_fitness": sum(a.fitness for a in self._agents) / len(self._agents) if self._agents else 0.0}

def run() -> None:
    print("Swarming Engine test")
    e = SwarmingEngine(seed=42)
    for i in range(5):
        e.add_agent(SwarmAgent("s" + str(i), SwarmRole.FOLLOWER, [float(i), float(i)], [0.0, 0.0]))
    e.evaluate(lambda pos: -(pos[0] - 5) ** 2 - (pos[1] - 3) ** 2)
    best = e.get_best()
    print("  Best fitness: " + str(best.fitness if best else 0))
    e.update_positions()
    print("  Stats: " + str(e.get_stats()))
    print("Swarming Engine test complete.")

if __name__ == "__main__":
    run()
