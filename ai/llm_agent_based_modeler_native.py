#!/usr/bin/env python3
"""MAGNATRIX-OS :: Agent Based Modeler Native Module
Simulates multi-agent systems with emergent behavior from local interaction rules.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Tuple, Set


class AgentState(Enum):
    ACTIVE = auto()
    INACTIVE = auto()
    MOVING = auto()
    INTERACTING = auto()


@dataclass
class Agent:
    id: int
    x: float
    y: float
    state: AgentState = AgentState.ACTIVE
    energy: float = 100.0
    attributes: Dict[str, float] = field(default_factory=dict)

    def distance_to(self, other: "Agent") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def move_toward(self, target_x: float, target_y: float, speed: float) -> None:
        dx = target_x - self.x
        dy = target_y - self.y
        dist = math.hypot(dx, dy)
        if dist > 0 and dist > speed:
            self.x += (dx / dist) * speed
            self.y += (dy / dist) * speed
        else:
            self.x = target_x
            self.y = target_y

    def move_random(self, speed: float, rng: random.Random) -> None:
        angle = rng.uniform(0, 2 * math.pi)
        self.x += math.cos(angle) * speed
        self.y += math.sin(angle) * speed


@dataclass
class SimulationSnapshot:
    tick: int
    agent_count: int
    avg_energy: float
    cluster_count: int
    interactions: int

    def to_dict(self) -> Dict:
        return {
            "tick": self.tick,
            "agents": self.agent_count,
            "avg_energy": round(self.avg_energy, 2),
            "clusters": self.cluster_count,
            "interactions": self.interactions,
        }


class AgentBasedModeler:
    """Simulates emergent behavior from local agent interactions."""

    def __init__(self, width: float = 100.0, height: float = 100.0, seed: int = 42):
        self.width = width
        self.height = height
        self.rng = random.Random(seed)
        self.agents: List[Agent] = []
        self.interaction_radius = 5.0
        self.tick = 0
        self.history: List[SimulationSnapshot] = []

    def spawn_agent(self, x: float = None, y: float = None, energy: float = 100.0) -> Agent:
        x = x if x is not None else self.rng.uniform(0, self.width)
        y = y if y is not None else self.rng.uniform(0, self.height)
        agent = Agent(id=len(self.agents), x=x, y=y, energy=energy)
        self.agents.append(agent)
        return agent

    def find_neighbors(self, agent: Agent) -> List[Agent]:
        return [a for a in self.agents if a.id != agent.id and agent.distance_to(a) <= self.interaction_radius]

    def _count_clusters(self) -> int:
        if not self.agents:
            return 0
        visited: Set[int] = set()
        clusters = 0
        for a in self.agents:
            if a.id in visited:
                continue
            clusters += 1
            queue = [a]
            while queue:
                current = queue.pop(0)
                if current.id in visited:
                    continue
                visited.add(current.id)
                for n in self.find_neighbors(current):
                    if n.id not in visited:
                        queue.append(n)
        return clusters

    def step(self, movement_speed: float = 2.0, interaction_cost: float = 5.0) -> SimulationSnapshot:
        interactions = 0
        for agent in self.agents:
            if agent.state == AgentState.INACTIVE or agent.energy <= 0:
                continue
            neighbors = self.find_neighbors(agent)
            if neighbors:
                agent.state = AgentState.INTERACTING
                for n in neighbors:
                    if n.state != AgentState.INACTIVE and n.energy > 0:
                        interactions += 1
                        agent.energy -= interaction_cost * 0.5
                        n.energy -= interaction_cost * 0.5
            else:
                agent.state = AgentState.MOVING
                agent.move_random(movement_speed, self.rng)
                agent.energy -= movement_speed * 0.1
            agent.x = max(0, min(self.width, agent.x))
            agent.y = max(0, min(self.height, agent.y))
        self.tick += 1
        active = [a for a in self.agents if a.energy > 0]
        avg_energy = sum(a.energy for a in active) / len(active) if active else 0.0
        snapshot = SimulationSnapshot(
            tick=self.tick,
            agent_count=len(active),
            avg_energy=avg_energy,
            cluster_count=self._count_clusters(),
            interactions=interactions,
        )
        self.history.append(snapshot)
        return snapshot

    def run(self, steps: int = 50) -> List[SimulationSnapshot]:
        for _ in range(steps):
            self.step()
        return self.history

    def stats(self) -> Dict[str, float]:
        if not self.history:
            return {"agents": len(self.agents), "ticks": 0}
        return {
            "agents": len(self.agents),
            "ticks": self.tick,
            "final_clusters": self.history[-1].cluster_count,
            "final_energy": round(self.history[-1].avg_energy, 2),
        }


def run() -> None:
    model = AgentBasedModeler(width=100, height=100, seed=42)
    for _ in range(20):
        model.spawn_agent(energy=100.0)
    history = model.run(steps=30)
    print(f"Agent Based Modeler Demo:")
    print(f"  Final tick: {history[-1].tick}, Active agents: {history[-1].agent_count}")
    print(f"  Clusters: {history[-1].cluster_count}, Interactions: {history[-1].interactions}")
    print(f"  Stats: {model.stats()}")


if __name__ == "__main__":
    run()
