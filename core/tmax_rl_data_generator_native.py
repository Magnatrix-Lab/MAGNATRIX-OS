"""TMax RL Data Generator -- Generate terminal interaction data for RL training."""
from dataclasses import dataclass
from pathlib import Path
import json, random

@dataclass
class TerminalInteraction:
    interaction_id: str = ""
    task_id: str = ""
    prompt: str = ""
    commands: list[str] = None
    observations: list[str] = None
    reward: float = 0.0
    success: bool = False
    terminal_type: str = "bash"

    def __post_init__(self):
        if self.commands is None:
            self.commands = []
        if self.observations is None:
            self.observations = []

class TmaxRLDataGenerator:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._interactions: list[TerminalInteraction] = []
        self._task_templates: list[dict] = []
        self._persist_path = self.root / "tmax_rl_data.json"
        self._load()
        if not self._task_templates:
            self._seed_templates()

    def _seed_templates(self) -> None:
        self._task_templates = [
            {"task_id": "file_search", "prompt": "Find all Python files modified in the last 24 hours", "expected": "find . -name '*.py' -mtime -1"},
            {"task_id": "git_log", "prompt": "Show the last 5 commits with their diffs", "expected": "git log -p -5"},
            {"task_id": "disk_usage", "prompt": "Show disk usage for all directories in /var", "expected": "du -sh /var/*"},
            {"task_id": "process_kill", "prompt": "Kill all processes named 'python' that are consuming >50% CPU", "expected": "ps aux | grep python | awk '{print $2}' | xargs kill -9"},
            {"task_id": "env_check", "prompt": "Check if the environment variable OPENAI_API_KEY is set", "expected": "echo $OPENAI_API_KEY"},
            {"task_id": "port_scan", "prompt": "Check which process is using port 8080", "expected": "lsof -i :8080"},
            {"task_id": "package_search", "prompt": "Find installed packages matching 'requests'", "expected": "pip list | grep requests"},
            {"task_id": "log_tail", "prompt": "Tail the last 100 lines of /var/log/syslog", "expected": "tail -n 100 /var/log/syslog"},
        ]

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._interactions = [TerminalInteraction(**i) for i in data.get("interactions", [])]
            self._task_templates = data.get("templates", [])

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "interactions": [i.__dict__ for i in self._interactions],
            "templates": self._task_templates
        }, indent=2))

    def generate(self, task_id: str = "", count: int = 1) -> list[TerminalInteraction]:
        results = []
        templates = self._task_templates if not task_id else [t for t in self._task_templates if t["task_id"] == task_id]
        for _ in range(count):
            template = random.choice(templates) if templates else {"task_id": "unknown", "prompt": "", "expected": ""}
            interaction = TerminalInteraction(
                interaction_id="int_" + str(len(self._interactions)),
                task_id=template["task_id"],
                prompt=template["prompt"],
                commands=[template["expected"]],
                observations=["Command executed successfully. Output: ..."],
                reward=1.0 if random.random() > 0.3 else 0.5,
                success=random.random() > 0.2
            )
            self._interactions.append(interaction)
            results.append(interaction)
        self._save()
        return results

    def add_template(self, task_id: str, prompt: str, expected: str) -> None:
        self._task_templates.append({"task_id": task_id, "prompt": prompt, "expected": expected})
        self._save()

    def export_dataset(self, path: str) -> int:
        data = [i.__dict__ for i in self._interactions]
        Path(path).write_text(json.dumps(data, indent=2))
        return len(data)

    def to_dict(self) -> dict:
        return {"interaction_count": len(self._interactions), "templates": len(self._task_templates)}

    def get_stats(self) -> dict:
        by_task = {}
        success = 0
        for i in self._interactions:
            by_task[i.task_id] = by_task.get(i.task_id, 0) + 1
            if i.success:
                success += 1
        return {"interactions": len(self._interactions), "by_task": by_task, "success_rate": round(success / len(self._interactions), 2) if self._interactions else 0}

__all__ = ["TmaxRLDataGenerator", "TerminalInteraction"]
