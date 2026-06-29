"""Squad Collaboration Log — Decision history, audit trail, timeline."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class CollaborationEvent:
    event_id: str = ""
    event_type: str = ""  # decision | task_start | task_complete | review | conflict | merge
    timestamp: float = 0.0
    agent_id: str = ""
    workspace_id: str = ""
    description: str = ""
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class SquadCollaborationLog:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._events: list[CollaborationEvent] = []
        self._persist_path = self.root / "squad_collaboration.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._events = [CollaborationEvent(**e) for e in data.get("events", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "events": [e.__dict__ for e in self._events]
        }, indent=2))

    def log(self, event_type: str, agent_id: str, workspace_id: str, description: str, metadata: dict = None) -> CollaborationEvent:
        import time
        event = CollaborationEvent(
            event_id=f"evt_{len(self._events)}",
            event_type=event_type, timestamp=time.time(),
            agent_id=agent_id, workspace_id=workspace_id,
            description=description, metadata=metadata or {}
        )
        self._events.append(event)
        self._save()
        return event

    def decision(self, agent_id: str, workspace_id: str, decision: str, context: dict) -> CollaborationEvent:
        return self.log("decision", agent_id, workspace_id, decision, context)

    def task_start(self, agent_id: str, workspace_id: str, task: str) -> CollaborationEvent:
        return self.log("task_start", agent_id, workspace_id, task)

    def task_complete(self, agent_id: str, workspace_id: str, task: str, result_summary: str) -> CollaborationEvent:
        return self.log("task_complete", agent_id, workspace_id, f"{task} -> {result_summary}")

    def review(self, reviewer_id: str, workspace_id: str, target_agent: str, verdict: str) -> CollaborationEvent:
        return self.log("review", reviewer_id, workspace_id, f"Reviewed {target_agent}: {verdict}")

    def get_timeline(self, workspace_id: str) -> list[CollaborationEvent]:
        return sorted([e for e in self._events if e.workspace_id == workspace_id], key=lambda x: x.timestamp)

    def get_by_agent(self, agent_id: str) -> list[CollaborationEvent]:
        return [e for e in self._events if e.agent_id == agent_id]

    def get_by_type(self, event_type: str) -> list[CollaborationEvent]:
        return [e for e in self._events if e.event_type == event_type]

    def to_dict(self) -> dict:
        return {"event_count": len(self._events)}

    def get_stats(self) -> dict:
        by_type = {}
        by_workspace = {}
        for e in self._events:
            by_type[e.event_type] = by_type.get(e.event_type, 0) + 1
            by_workspace[e.workspace_id] = by_workspace.get(e.workspace_id, 0) + 1
        return {"events": len(self._events), "by_type": by_type, "workspaces": len(by_workspace)}

__all__ = ["SquadCollaborationLog", "CollaborationEvent"]
