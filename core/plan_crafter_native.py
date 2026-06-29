"""
plan_crafter_native.py
MAGNATRIX-OS — Plan Crafter

Inspired by engineering-discipline: Create executable plans with worker-validator execution. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class PlanStep:
    step_id: str
    description: str
    action: str
    validation: str
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, active, done, failed


@dataclass
class ExecutablePlan:
    plan_id: str
    task: str
    steps: List[PlanStep]
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class PlanCrafter:
    """Create executable plans with worker-validator execution."""

    def __init__(self, plans_dir: str = "./plans"):
        self.plans_dir = Path(plans_dir)
        self.plans_dir.mkdir(exist_ok=True)
        self.plans: Dict[str, ExecutablePlan] = {}
        self._load()

    def _load(self) -> None:
        file = self.plans_dir / "plans.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for pid, pd in data.items():
                        steps = [PlanStep(**s) for s in pd.get("steps", [])]
                        self.plans[pid] = ExecutablePlan(
                            plan_id=pid, task=pd["task"], steps=steps, created_at=pd.get("created_at", ""),
                        )
            except Exception:
                pass

    def _save(self) -> None:
        out = {}
        for pid, p in self.plans.items():
            d = asdict(p)
            d["steps"] = [asdict(s) for s in p.steps]
            out[pid] = d
        with open(self.plans_dir / "plans.json", "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)

    def craft(self, plan_id: str, task: str, requirements: List[str]) -> ExecutablePlan:
        """Create an executable plan from requirements."""
        steps = []
        for i, req in enumerate(requirements):
            sid = f"step_{i}"
            steps.append(PlanStep(
                step_id=sid, description=req,
                action=f"Implement: {req}",
                validation=f"Verify: {req} works as expected",
                dependencies=[f"step_{i-1}"] if i > 0 else [],
            ))
        # Add validation step
        steps.append(PlanStep(
            step_id="validate", description="Final validation",
            action="Run all tests and checks",
            validation="All tests pass, no regressions",
            dependencies=[f"step_{len(requirements)-1}"] if requirements else [],
        ))
        plan = ExecutablePlan(plan_id=plan_id, task=task, steps=steps)
        self.plans[plan_id] = plan
        self._save()
        return plan

    def get_plan(self, plan_id: str) -> Optional[ExecutablePlan]:
        return self.plans.get(plan_id)

    def update_step(self, plan_id: str, step_id: str, status: str) -> bool:
        plan = self.plans.get(plan_id)
        if not plan:
            return False
        for step in plan.steps:
            if step.step_id == step_id:
                step.status = status
                self._save()
                return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.plans)
        total_steps = sum(len(p.steps) for p in self.plans.values())
        done = sum(1 for p in self.plans.values() for s in p.steps if s.status == "done")
        return {"total_plans": total, "total_steps": total_steps, "completed_steps": done}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["PlanCrafter", "ExecutablePlan", "PlanStep"]