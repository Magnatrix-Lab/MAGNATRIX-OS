"""
collective-brain/world-model/simulation_env.py
===============================================
MAGNATRIX World Model / Simulation Environment
Layer 0: Reality Interface

Sandbox simulator untuk test agents tanpa real-world risk.
Simulated environment dengan reward functions, physics-lite, economic models.
"""

import asyncio, json, random, time, uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from collections import defaultdict

class EntityType(Enum):
    AGENT = "agent"; RESOURCE = "resource"; OBSTACLE = "obstacle"; GOAL = "goal"

@dataclass
class SimEntity:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    entity_type: EntityType = EntityType.AGENT
    position: List[float] = field(default_factory=lambda: [0.0, 0.0])
    velocity: List[float] = field(default_factory=lambda: [0.0, 0.0])
    state: Dict = field(default_factory=dict)
    reward_history: List[float] = field(default_factory=list)
    alive: bool = True

@dataclass
class SimAction:
    agent_id: str = ""
    action_type: str = ""   # move, collect, interact, attack, build
    parameters: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

class RewardFunction:
    """Configurable reward functions for training"""

    def __init__(self, config: Dict = None):
        self.config = config or {"survival": 1.0, "collection": 5.0, "goal": 100.0, "collision": -10.0}

    def compute(self, entity: SimEntity, action: SimAction, world_state: Dict) -> float:
        reward = 0.0

        if action.action_type == "move":
            # Reward for progress toward goal
            goal = world_state.get("goal_position", [10.0, 10.0])
            dist_before = self._distance(entity.position, goal)
            new_pos = [
                entity.position[0] + action.parameters.get("dx", 0),
                entity.position[1] + action.parameters.get("dy", 0)
            ]
            dist_after = self._distance(new_pos, goal)
            reward += (dist_before - dist_after) * 0.5

        elif action.action_type == "collect":
            resource_id = action.parameters.get("resource_id")
            resources = world_state.get("resources", {})
            if resource_id in resources and resources[resource_id].get("available", False):
                reward += self.config["collection"]
                resources[resource_id]["available"] = False

        elif action.action_type == "goal":
            reward += self.config["goal"]

        elif action.action_type == "collide":
            reward += self.config["collision"]
            entity.alive = False

        # Survival bonus
        if entity.alive:
            reward += self.config["survival"]

        entity.reward_history.append(reward)
        return reward

    def _distance(self, a: List[float], b: List[float]) -> float:
        return ((a[0]-b[0])**2 + (a[1]-b[1])**2) ** 0.5

class SimulationWorld:
    """Main simulation environment"""

    def __init__(self, width: float = 100.0, height: float = 100.0):
        self.width = width; self.height = height
        self.entities: Dict[str, SimEntity] = {}
        self.time_step: int = 0
        self.running: bool = False
        self.reward_fn = RewardFunction()
        self._episode_log: List[Dict] = []

    def spawn(self, entity: SimEntity) -> str:
        self.entities[entity.id] = entity
        return entity.id

    def reset(self):
        """Reset world state untuk new episode"""
        self.entities.clear()
        self.time_step = 0
        self._episode_log = []

    async def step(self, actions: List[SimAction]) -> Dict:
        """Execute one simulation step"""
        rewards = {}

        for action in actions:
            entity = self.entities.get(action.agent_id)
            if not entity or not entity.alive:
                continue

            reward = self.reward_fn.compute(entity, action, {
                "goal_position": [self.width*0.8, self.height*0.8],
                "resources": {eid: {"available": True} for eid, e in self.entities.items() if e.entity_type == EntityType.RESOURCE}
            })
            rewards[action.agent_id] = reward

            # Apply movement
            if action.action_type == "move":
                dx = action.parameters.get("dx", 0)
                dy = action.parameters.get("dy", 0)
                entity.position[0] = max(0, min(self.width, entity.position[0] + dx))
                entity.position[1] = max(0, min(self.height, entity.position[1] + dy))

            # Check goal reached
            goal_dist = ((entity.position[0] - self.width*0.8)**2 + (entity.position[1] - self.height*0.8)**2)**0.5
            if goal_dist < 5.0:
                rewards[action.agent_id] += 100.0

        self.time_step += 1

        state = {
            "time_step": self.time_step,
            "entities_alive": sum(1 for e in self.entities.values() if e.alive),
            "total_entities": len(self.entities),
            "rewards": rewards,
            "average_reward": sum(rewards.values()) / max(len(rewards), 1)
        }
        self._episode_log.append(state)
        return state

    def run_episode(self, agent_fn: Callable, max_steps: int = 100) -> Dict:
        """Run full episode dengan agent policy function"""
        self.reset()

        # Spawn agent and resources
        agent = SimEntity(entity_type=EntityType.AGENT, position=[5.0, 5.0])
        self.spawn(agent)

        for _ in range(10):
            res = SimEntity(entity_type=EntityType.RESOURCE,
                           position=[random.uniform(0, self.width), random.uniform(0, self.height)])
            self.spawn(res)

        total_reward = 0.0
        for step in range(max_steps):
            action = agent_fn(agent, self)
            if action:
                state = asyncio.get_event_loop().run_until_complete(self.step([action]))
                total_reward += state["average_reward"]
            if not agent.alive:
                break

        return {
            "total_reward": total_reward,
            "steps_survived": self.time_step,
            "max_reward": max((e.reward_history or [0]) for e in self.entities.values(), key=lambda x: max(x) if x else 0),
            "final_position": agent.position
        }

    def get_stats(self) -> Dict:
        return {
            "dimensions": f"{self.width}x{self.height}",
            "entities": len(self.entities),
            "time_steps": self.time_step,
            "episodes": len(self._episode_log)
        }


if __name__ == "__main__":
    async def demo():
        world = SimulationWorld(50, 50)

        # Simple random agent
        def random_agent(agent, world):
            return SimAction(
                agent_id=agent.id,
                action_type="move",
                parameters={"dx": random.uniform(-2, 2), "dy": random.uniform(-2, 2)}
            )

        result = world.run_episode(random_agent, max_steps=20)
        print(f"Episode result: {result}")
        print(f"World stats: {world.get_stats()}")

    asyncio.run(demo())
