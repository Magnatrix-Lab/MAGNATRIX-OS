"""TMax Task Builder -- Construct terminal agent tasks with constraints and hints."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class TerminalTask:
    task_id: str = ""
    description: str = ""
    initial_state: dict = None
    goal: str = ""
    constraints: list[str] = None
    hints: list[str] = None
    expected_commands: list[str] = None
    difficulty: str = "easy"  # easy | medium | hard | expert
    tags: list[str] = None

    def __post_init__(self):
        if self.initial_state is None:
            self.initial_state = {}
        if self.constraints is None:
            self.constraints = []
        if self.hints is None:
            self.hints = []
        if self.expected_commands is None:
            self.expected_commands = []
        if self.tags is None:
            self.tags = []

class TmaxTaskBuilder:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._tasks: dict[str, TerminalTask] = {}
        self._persist_path = self.root / "tmax_tasks.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._tasks = {k: TerminalTask(**v) for k, v in data.get("tasks", {}).items()}

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "tasks": {k: v.__dict__ for k, v in self._tasks.items()}
        }, indent=2))

    def create(self, task_id: str, description: str, goal: str, difficulty: str = "easy") -> TerminalTask:
        task = TerminalTask(task_id=task_id, description=description, goal=goal, difficulty=difficulty)
        self._tasks[task_id] = task
        self._save()
        return task

    def add_constraint(self, task_id: str, constraint: str) -> bool:
        task = self._tasks.get(task_id)
        if task:
            task.constraints.append(constraint)
            self._save()
            return True
        return False

    def add_hint(self, task_id: str, hint: str) -> bool:
        task = self._tasks.get(task_id)
        if task:
            task.hints.append(hint)
            self._save()
            return True
        return False

    def set_initial_state(self, task_id: str, state: dict) -> bool:
        task = self._tasks.get(task_id)
        if task:
            task.initial_state = state
            self._save()
            return True
        return False

    def add_expected_command(self, task_id: str, command: str) -> bool:
        task = self._tasks.get(task_id)
        if task:
            task.expected_commands.append(command)
            self._save()
            return True
        return False

    def tag(self, task_id: str, tag: str) -> bool:
        task = self._tasks.get(task_id)
        if task and tag not in task.tags:
            task.tags.append(tag)
            self._save()
            return True
        return False

    def get(self, task_id: str) -> TerminalTask | None:
        return self._tasks.get(task_id)

    def list_by_difficulty(self, difficulty: str) -> list[TerminalTask]:
        return [t for t in self._tasks.values() if t.difficulty == difficulty]

    def list_by_tag(self, tag: str) -> list[TerminalTask]:
        return [t for t in self._tasks.values() if tag in t.tags]

    def export(self, path: str) -> int:
        data = {k: v.__dict__ for k, v in self._tasks.items()}
        Path(path).write_text(json.dumps(data, indent=2))
        return len(data)

    def to_dict(self) -> dict:
        return {"task_count": len(self._tasks)}

    def get_stats(self) -> dict:
        by_difficulty = {}
        by_tag = {}
        for t in self._tasks.values():
            by_difficulty[t.difficulty] = by_difficulty.get(t.difficulty, 0) + 1
            for tag in t.tags:
                by_tag[tag] = by_tag.get(tag, 0) + 1
        return {"tasks": len(self._tasks), "by_difficulty": by_difficulty, "by_tag": by_tag}

__all__ = ["TmaxTaskBuilder", "TerminalTask"]
