"""
human_in_loop_controller_native.py
MAGNATRIX-OS — Human-in-the-Loop Controller

Inspired by AgentSkillOS: Human intervention at every step for controllable workflows. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class HumanDecision:
    decision_id: str
    step_id: str
    task_description: str
    proposed_action: str
    human_approved: Optional[bool] = None
    human_feedback: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class HumanInLoopController:
    """Human intervention at every step for controllable, auditable workflows."""

    def __init__(self, cache_dir: str = "./human_in_loop"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.decisions: Dict[str, HumanDecision] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "decisions.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for did, dd in data.items():
                        self.decisions[did] = HumanDecision(**dd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "decisions.json", "w", encoding="utf-8") as f:
            json.dump({did: asdict(d) for did, d in self.decisions.items()}, f, indent=2)

    def request_approval(self, decision_id: str, step_id: str, task_description: str,
                         proposed_action: str) -> HumanDecision:
        decision = HumanDecision(
            decision_id=decision_id, step_id=step_id, task_description=task_description,
            proposed_action=proposed_action, human_approved=None,
        )
        self.decisions[decision_id] = decision
        self._save()
        return decision

    def approve(self, decision_id: str, feedback: str = "") -> bool:
        decision = self.decisions.get(decision_id)
        if decision:
            decision.human_approved = True
            decision.human_feedback = feedback
            self._save()
            return True
        return False

    def reject(self, decision_id: str, feedback: str) -> bool:
        decision = self.decisions.get(decision_id)
        if decision:
            decision.human_approved = False
            decision.human_feedback = feedback
            self._save()
            return True
        return False

    def is_approved(self, decision_id: str) -> Optional[bool]:
        decision = self.decisions.get(decision_id)
        return decision.human_approved if decision else None

    def get_pending(self) -> List[HumanDecision]:
        return [d for d in self.decisions.values() if d.human_approved is None]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.decisions)
        approved = sum(1 for d in self.decisions.values() if d.human_approved is True)
        rejected = sum(1 for d in self.decisions.values() if d.human_approved is False)
        pending = sum(1 for d in self.decisions.values() if d.human_approved is None)
        return {"total": total, "approved": approved, "rejected": rejected, "pending": pending}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["HumanInLoopController", "HumanDecision"]