"""
milestone_planner_native.py
MAGNATRIX-OS — Milestone Planner

Inspired by engineering-discipline: Multi-day orchestrator with checkpoints for complex tasks. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class Milestone:
    milestone_id: str
    name: str
    description: str
    requirements: List[str]
    status: str = "pending"  # pending, active, done
    checkpoint: str = ""


@dataclass
class MilestonePlan:
    plan_id: str
    task: str
    milestones: List[Milestone]
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class MilestonePlanner:
    """Multi-day orchestrator with checkpoints for complex tasks."""

    def __init__(self, plans_dir: str = "./milestone_plans"):
        self.plans_dir = Path(plans_dir)
        self.plans_dir.mkdir(exist_ok=True)
        self.plans: Dict[str, MilestonePlan] = {}
        self._load()

    def _load(self) -> None:
        file = self.plans_dir / "plans.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for pid, pd in data.items():
                        ms = [Milestone(**m) for m in pd.get("milestones", [])]
                        self.plans[pid] = MilestonePlan(
                            plan_id=pid, task=pd["task"], milestones=ms, created_at=pd.get("created_at", ""),
                        )
            except Exception:
                pass

    def _save(self) -> None:
        out = {}
        for pid, p in self.plans.items():
            d = asdict(p)
            d["milestones"] = [asdict(m) for m in p.milestones]
            out[pid] = d
        with open(self.plans_dir / "plans.json", "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)

    def plan(self, plan_id: str, task: str, requirements: List[str]) -> MilestonePlan:
        """Break down a complex task into milestones."""
        milestones = []
        # Break into 3-5 milestones
        chunk_size = max(1, len(requirements) // 4)
        for i in range(0, len(requirements), chunk_size):
            chunk = requirements[i:i + chunk_size]
            mid = f"M{i // chunk_size + 1}"
            milestones.append(Milestone(
                milestone_id=mid, name=f"Phase {i // chunk_size + 1}",
                description="; ".join(chunk),
                requirements=chunk,
            ))
        # Add final milestone
        milestones.append(Milestone(
            milestone_id="M_final", name="Final Integration",
            description="Integration and validation of all phases",
            requirements=["Run all tests", "Perform final review"],
        ))
        plan = MilestonePlan(plan_id=plan_id, task=task, milestones=milestones)
        self.plans[plan_id] = plan
        self._save()
        return plan

    def checkpoint(self, plan_id: str, milestone_id: str) -> Dict[str, Any]:
        """Record a checkpoint for a milestone."""
        plan = self.plans.get(plan_id)
        if not plan:
            return {"error": "Plan not found"}
        for m in plan.milestones:
            if m.milestone_id == milestone_id:
                m.status = "done"
                m.checkpoint = datetime.now().isoformat()
                self._save()
                return {"milestone": milestone_id, "status": "done", "checkpoint": m.checkpoint}
        return {"error": "Milestone not found"}

    def get_plan(self, plan_id: str) -> Optional[MilestonePlan]:
        return self.plans.get(plan_id)

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.plans)
        total_ms = sum(len(p.milestones) for p in self.plans.values())
        done = sum(1 for p in self.plans.values() for m in p.milestones if m.status == "done")
        return {"total_plans": total, "total_milestones": total_ms, "completed": done}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["MilestonePlanner", "MilestonePlan", "Milestone"]