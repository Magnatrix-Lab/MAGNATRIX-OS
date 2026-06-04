"""Rolling Update — incremental instance replacement, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto
import time

class InstanceState(Enum):
    OLD = auto()
    UPDATING = auto()
    NEW = auto()
    FAILED = auto()

@dataclass
class Instance:
    instance_id: str
    version: str
    state: InstanceState
    healthy: bool = True

class RollingUpdater:
    def __init__(self, batch_size: int = 1, max_unavailable: int = 1):
        self.batch_size = batch_size
        self.max_unavailable = max_unavailable
        self.instances: List[Instance] = []
        self.target_version: str = ""
        self.update_history: List[Dict] = []

    def add_instance(self, instance_id: str, version: str):
        self.instances.append(Instance(instance_id, version, InstanceState.OLD))

    def start_update(self, target_version: str):
        self.target_version = target_version
        old_instances = [i for i in self.instances if i.state == InstanceState.OLD]
        for i in old_instances[:self.batch_size]:
            i.state = InstanceState.UPDATING

    def update_instance(self, instance_id: str, success: bool):
        inst = next((i for i in self.instances if i.instance_id == instance_id), None)
        if not inst:
            return
        if success:
            inst.version = self.target_version
            inst.state = InstanceState.NEW
            inst.healthy = True
        else:
            inst.state = InstanceState.FAILED
        self.update_history.append({"id": instance_id, "success": success, "time": time.time()})

    def continue_update(self):
        old = [i for i in self.instances if i.state == InstanceState.OLD]
        updating = [i for i in self.instances if i.state == InstanceState.UPDATING]
        failed = [i for i in self.instances if i.state == InstanceState.FAILED]
        if not old and not updating:
            return True
        available = sum(1 for i in self.instances if i.state in (InstanceState.OLD, InstanceState.NEW) and i.healthy)
        unavailable = len(self.instances) - available
        slots = self.max_unavailable - unavailable + len(failed)
        for i in old[:max(slots, self.batch_size)]:
            i.state = InstanceState.UPDATING
        return False

    def rollback(self):
        for i in self.instances:
            if i.state in (InstanceState.UPDATING, InstanceState.NEW):
                i.state = InstanceState.OLD
                i.version = "previous"

    def stats(self) -> Dict:
        states = {}
        for i in self.instances:
            states[i.state.name] = states.get(i.state.name, 0) + 1
        return {"instances": len(self.instances), "states": states, "target": self.target_version, "complete": not any(i.state in (InstanceState.OLD, InstanceState.UPDATING) for i in self.instances)}

def run():
    updater = RollingUpdater(batch_size=2, max_unavailable=1)
    for i in range(5):
        updater.add_instance(f"inst-{i}", "v1")
    updater.start_update("v2")
    for i in updater.instances:
        if i.state == InstanceState.UPDATING:
            updater.update_instance(i.instance_id, True)
    updater.continue_update()
    print(updater.stats())

if __name__ == "__main__":
    run()
