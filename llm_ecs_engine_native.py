"""ECS Engine — entity, component, system, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any, Set
from enum import Enum, auto
import uuid

class ECSEngine:
    def __init__(self):
        self.entities: Set[str] = set()
        self.components: Dict[str, Dict[str, Any]] = {}  # component_type -> entity_id -> data
        self.systems: List[Callable] = []
        self.next_id = 0

    def create_entity(self) -> str:
        eid = str(self.next_id)
        self.next_id += 1
        self.entities.add(eid)
        return eid

    def destroy_entity(self, entity_id: str):
        self.entities.discard(entity_id)
        for comp_dict in self.components.values():
            comp_dict.pop(entity_id, None)

    def add_component(self, entity_id: str, component_type: str, data: Any):
        if component_type not in self.components:
            self.components[component_type] = {}
        self.components[component_type][entity_id] = data

    def get_component(self, entity_id: str, component_type: str) -> Any:
        return self.components.get(component_type, {}).get(entity_id)

    def has_component(self, entity_id: str, component_type: str) -> bool:
        return entity_id in self.components.get(component_type, {})

    def query(self, component_types: List[str]) -> List[str]:
        result = []
        for eid in self.entities:
            if all(self.has_component(eid, ct) for ct in component_types):
                result.append(eid)
        return result

    def add_system(self, system: Callable):
        self.systems.append(system)

    def update(self, dt: float):
        for system in self.systems:
            system(self, dt)

    def stats(self) -> Dict:
        return {"entities": len(self.entities), "component_types": len(self.components), "systems": len(self.systems)}

def run():
    ecs = ECSEngine()
    e1 = ecs.create_entity()
    e2 = ecs.create_entity()
    ecs.add_component(e1, "position", {"x": 0, "y": 0})
    ecs.add_component(e1, "velocity", {"vx": 1, "vy": 0})
    ecs.add_component(e2, "position", {"x": 5, "y": 5})
    def movement_system(ecs, dt):
        for eid in ecs.query(["position", "velocity"]):
            pos = ecs.get_component(eid, "position")
            vel = ecs.get_component(eid, "velocity")
            pos["x"] += vel["vx"] * dt
            pos["y"] += vel["vy"] * dt
    ecs.add_system(movement_system)
    ecs.update(1.0)
    print(ecs.get_component(e1, "position"))
    print(ecs.stats())

if __name__ == "__main__":
    run()
