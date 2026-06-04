"""Infrastructure as Code — resource definition, dependency graph, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum, auto
import time

class ResourceType(Enum):
    COMPUTE = auto()
    STORAGE = auto()
    NETWORK = auto()
    DATABASE = auto()
    SECURITY = auto()

class ResourceState(Enum):
    PENDING = auto()
    CREATING = auto()
    READY = auto()
    FAILED = auto()
    DESTROYING = auto()

@dataclass
class Resource:
    resource_id: str
    resource_type: ResourceType
    config: Dict
    depends_on: List[str] = field(default_factory=list)
    state: ResourceState = ResourceState.PENDING

class IaCEngine:
    def __init__(self):
        self.resources: Dict[str, Resource] = {}
        self.state_history: List[Dict] = []

    def add_resource(self, resource: Resource):
        self.resources[resource.resource_id] = resource

    def get_dependency_order(self) -> List[str]:
        visited = set()
        order = []
        def visit(rid):
            if rid in visited:
                return
            visited.add(rid)
            r = self.resources.get(rid)
            if r:
                for dep in r.depends_on:
                    visit(dep)
            order.append(rid)
        for rid in self.resources:
            visit(rid)
        return order

    def provision(self, resource_id: str) -> bool:
        r = self.resources.get(resource_id)
        if not r:
            return False
        r.state = ResourceState.CREATING
        for dep in r.depends_on:
            if self.resources.get(dep, Resource("", ResourceType.COMPUTE, {})).state != ResourceState.READY:
                self.provision(dep)
        r.state = ResourceState.READY
        self.state_history.append({"id": resource_id, "state": "READY", "time": time.time()})
        return True

    def provision_all(self) -> List[str]:
        order = self.get_dependency_order()
        for rid in order:
            self.provision(rid)
        return order

    def destroy(self, resource_id: str):
        r = self.resources.get(resource_id)
        if r:
            r.state = ResourceState.DESTROYING
            r.state = ResourceState.PENDING

    def destroy_all(self):
        for rid in reversed(self.get_dependency_order()):
            self.destroy(rid)

    def stats(self) -> Dict:
        states = {}
        for r in self.resources.values():
            states[r.state.name] = states.get(r.state.name, 0) + 1
        return {"resources": len(self.resources), "states": states, "provisioned": sum(1 for r in self.resources.values() if r.state == ResourceState.READY)}

def run():
    iac = IaCEngine()
    iac.add_resource(Resource("vpc", ResourceType.NETWORK, {"cidr": "10.0.0.0/16"}))
    iac.add_resource(Resource("subnet", ResourceType.NETWORK, {"vpc": "vpc"}, ["vpc"]))
    iac.add_resource(Resource("vm", ResourceType.COMPUTE, {"subnet": "subnet"}, ["subnet"]))
    iac.provision_all()
    print(iac.stats())

if __name__ == "__main__":
    run()
