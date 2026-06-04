"""Scheduling Constraint - Job shop scheduling for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum, auto

@dataclass
class Job:
    job_id: str
    tasks: List[Tuple[str, float]]  # (machine, duration)

@dataclass
class SchedulingConstraint:
    jobs: List[Job] = field(default_factory=list)
    machines: List[str] = field(default_factory=list)

    def add_job(self, job: Job) -> None:
        self.jobs.append(job)
        for task in job.tasks:
            if task[0] not in self.machines:
                self.machines.append(task[0])

    def schedule(self) -> Dict[str, List[Tuple[str, float, float]]]:
        machine_schedule = {m: [] for m in self.machines}
        job_time = {}
        for job in self.jobs:
            current_time = 0
            for machine, duration in job.tasks:
                # Find earliest available time
                available = 0
                if machine_schedule[machine]:
                    available = max(end for _, _, end in machine_schedule[machine])
                start = max(current_time, available)
                machine_schedule[machine].append((job.job_id, start, start + duration))
                current_time = start + duration
            job_time[job.job_id] = current_time
        return machine_schedule

    def makespan(self) -> float:
        schedule = self.schedule()
        return max(end for tasks in schedule.values() for _, _, end in tasks) if any(schedule.values()) else 0

    def stats(self) -> dict:
        return {"jobs": len(self.jobs), "machines": len(self.machines), "makespan": round(self.makespan(), 2)}

def run():
    sc = SchedulingConstraint()
    sc.add_job(Job("J1", [("M1", 3), ("M2", 2)]))
    sc.add_job(Job("J2", [("M1", 2), ("M2", 4)]))
    print("Schedule:", sc.schedule())
    print("Stats:", sc.stats())

if __name__ == "__main__": run()
