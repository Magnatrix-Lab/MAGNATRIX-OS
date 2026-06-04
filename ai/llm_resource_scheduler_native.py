"""Resource Scheduler - Resource allocation for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto

class SchedulingPolicy(Enum):
    FIFO = auto(); PRIORITY = auto(); FAIR = auto()

@dataclass
class ResourceScheduler:
    policy: SchedulingPolicy = SchedulingPolicy.FIFO
    queue: List[Dict] = field(default_factory=list)
    resources: Dict[str, int] = field(default_factory=dict)

    def add_resource(self, resource_type: str, capacity: int) -> None:
        self.resources[resource_type] = capacity

    def submit_job(self, job_id: str, requirements: Dict[str, int], priority: int = 0) -> bool:
        job = {"id": job_id, "requirements": requirements, "priority": priority, "status": "queued"}
        self.queue.append(job)
        return True

    def schedule(self) -> List[str]:
        if self.policy == SchedulingPolicy.PRIORITY:
            self.queue.sort(key=lambda j: j["priority"], reverse=True)
        scheduled = []
        available = self.resources.copy()
        for job in self.queue[:]:
            if all(available.get(r, 0) >= req for r, req in job["requirements"].items()):
                for r, req in job["requirements"].items(): available[r] -= req
                job["status"] = "running"
                scheduled.append(job["id"])
                self.queue.remove(job)
        return scheduled

    def stats(self) -> dict:
        return {"queued": len(self.queue), "resources": self.resources, "policy": self.policy.name}

def run():
    rs = ResourceScheduler(SchedulingPolicy.PRIORITY)
    rs.add_resource("cpu", 4); rs.add_resource("memory", 8)
    rs.submit_job("job1", {"cpu": 2, "memory": 4}, 1)
    rs.submit_job("job2", {"cpu": 1, "memory": 2}, 3)
    print("Scheduled:", rs.schedule())
    print("Stats:", rs.stats())

if __name__ == "__main__": run()
