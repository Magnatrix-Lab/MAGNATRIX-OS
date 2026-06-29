"""TMax Evaluation Suite -- Daytona-style terminal agent evaluation."""
from dataclasses import dataclass
from pathlib import Path
import json, time

@dataclass
class EvalResult:
    eval_id: str = ""
    task_id: str = ""
    agent_id: str = ""
    score: float = 0.0
    max_score: float = 1.0
    passed: bool = False
    execution_time_ms: int = 0
    output_match: float = 0.0
    commands_used: int = 0
    evaluated_at: float = 0.0

class TmaxEvaluationSuite:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._results: list[EvalResult] = []
        self._test_cases: list[dict] = []
        self._persist_path = self.root / "tmax_eval.json"
        self._load()
        if not self._test_cases:
            self._seed_tests()

    def _seed_tests(self) -> None:
        self._test_cases = [
            {"task_id": "file_list", "expected_output": "main.py", "max_commands": 3, "score_weight": 1.0},
            {"task_id": "git_status", "expected_output": "clean", "max_commands": 2, "score_weight": 1.0},
            {"task_id": "env_var", "expected_output": "set", "max_commands": 1, "score_weight": 1.0},
            {"task_id": "directory_nav", "expected_output": "src", "max_commands": 3, "score_weight": 1.0},
            {"task_id": "grep_search", "expected_output": "match", "max_commands": 2, "score_weight": 1.0},
        ]

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._results = [EvalResult(**r) for r in data.get("results", [])]
            self._test_cases = data.get("test_cases", [])

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "results": [r.__dict__ for r in self._results],
            "test_cases": self._test_cases
        }, indent=2))

    def evaluate(self, eval_id: str, task_id: str, agent_id: str, agent_output: str, commands: list[str]) -> EvalResult:
        test = next((t for t in self._test_cases if t["task_id"] == task_id), None)
        max_score = test["score_weight"] if test else 1.0
        max_commands = test["max_commands"] if test else 5

        output_match = 0.0
        if test and test["expected_output"] in agent_output.lower():
            output_match = 1.0
        elif test:
            # Partial match
            for word in test["expected_output"].split():
                if word in agent_output.lower():
                    output_match += 0.3
            output_match = min(1.0, output_match)

        command_penalty = max(0, len(commands) - max_commands) * 0.1
        score = max(0, output_match - command_penalty)
        passed = score >= 0.7

        result = EvalResult(
            eval_id=eval_id, task_id=task_id, agent_id=agent_id,
            score=score, max_score=max_score, passed=passed,
            output_match=output_match, commands_used=len(commands),
            evaluated_at=time.time()
        )
        self._results.append(result)
        self._save()
        return result

    def add_test(self, task_id: str, expected_output: str, max_commands: int = 3, score_weight: float = 1.0) -> None:
        self._test_cases.append({"task_id": task_id, "expected_output": expected_output, "max_commands": max_commands, "score_weight": score_weight})
        self._save()

    def get_score(self, agent_id: str) -> dict:
        agent_results = [r for r in self._results if r.agent_id == agent_id]
        if not agent_results:
            return {"score": 0, "passed": 0, "total": 0}
        total = sum(r.score for r in agent_results)
        passed = sum(1 for r in agent_results if r.passed)
        return {"score": round(total / len(agent_results), 2), "passed": passed, "total": len(agent_results)}

    def leaderboard(self) -> list[dict]:
        agents = {}
        for r in self._results:
            if r.agent_id not in agents:
                agents[r.agent_id] = []
            agents[r.agent_id].append(r)
        scores = []
        for aid, results in agents.items():
            avg = sum(r.score for r in results) / len(results)
            passed = sum(1 for r in results if r.passed)
            scores.append({"agent_id": aid, "avg_score": round(avg, 2), "passed": passed, "total": len(results)})
        return sorted(scores, key=lambda x: x["avg_score"], reverse=True)

    def to_dict(self) -> dict:
        return {"result_count": len(self._results), "test_cases": len(self._test_cases)}

    def get_stats(self) -> dict:
        by_task = {}
        passed = 0
        for r in self._results:
            by_task[r.task_id] = by_task.get(r.task_id, 0) + 1
            if r.passed:
                passed += 1
        return {"results": len(self._results), "by_task": by_task, "pass_rate": round(passed / len(self._results), 2) if self._results else 0}

__all__ = ["TmaxEvaluationSuite", "EvalResult"]
