"""Agents Eval - Evaluation framework for ADK agents."""
from __future__ import annotations

import json
import time
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


@dataclass
class EvalDataset:
    dataset_id: str
    name: str
    description: str = ""
    entries: List[Dict] = field(default_factory=list)
    metric_type: str = "accuracy"

    def to_dict(self) -> Dict:
        return {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "description": self.description,
            "entries_count": len(self.entries),
            "metric_type": self.metric_type,
        }


@dataclass
class EvalTrace:
    trace_id: str
    agent_name: str
    dataset_id: str
    input_query: str = ""
    expected_output: str = ""
    actual_output: str = ""
    score: float = 0.0
    latency_ms: float = 0.0
    timestamp: float = 0.0
    rubric: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "trace_id": self.trace_id,
            "agent_name": self.agent_name,
            "dataset_id": self.dataset_id,
            "input_query": self.input_query,
            "expected_output": self.expected_output,
            "actual_output": self.actual_output,
            "score": self.score,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp,
            "rubric": self.rubric,
        }


@dataclass
class EvalRubric:
    rubric_id: str
    name: str
    criteria: Dict[str, float] = field(default_factory=dict)
    adaptive: bool = False

    def to_dict(self) -> Dict:
        return {
            "rubric_id": self.rubric_id,
            "name": self.name,
            "criteria": self.criteria,
            "adaptive": self.adaptive,
        }


class AgentsEval:
    """Evaluation framework with LLM-as-judge and adaptive rubrics."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "agents_eval"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.datasets: Dict[str, EvalDataset] = {}
        self.traces: Dict[str, EvalTrace] = {}
        self.rubrics: Dict[str, EvalRubric] = {}
        self._init_default_rubrics()
        self._load_state()

    def _init_default_rubrics(self) -> None:
        defaults = [
            EvalRubric("rubric_correctness", "Correctness", {"factual": 1.0, "relevant": 1.0}, False),
            EvalRubric("rubric_quality", "Response Quality", {"clarity": 1.0, "completeness": 1.0, "conciseness": 0.5}, False),
            EvalRubric("rubric_safety", "Safety", {"harmless": 1.0, "truthful": 1.0, "helpful": 0.8}, False),
            EvalRubric("rubric_tool_use", "Tool Use", {"correct_tool": 1.0, "valid_params": 1.0, "result_integration": 0.8}, True),
        ]
        for r in defaults:
            self.rubrics[r.rubric_id] = r

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for d in data.get("datasets", []):
                    entries = d.pop("entries", [])
                    ds = EvalDataset(**d)
                    ds.entries = entries
                    self.datasets[ds.dataset_id] = ds
                for t in data.get("traces", []):
                    self.traces[t["trace_id"]] = EvalTrace(**t)
                for r in data.get("rubrics", []):
                    self.rubrics[r["rubric_id"]] = EvalRubric(**r)
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {
            "datasets": [d.to_dict() for d in self.datasets.values()],
            "traces": [t.to_dict() for t in self.traces.values()],
            "rubrics": [r.to_dict() for r in self.rubrics.values()],
        }
        state_file.write_text(json.dumps(state, indent=2))

    def create_dataset(self, name: str, metric_type: str = "accuracy") -> EvalDataset:
        dataset_id = f"ds_{name}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:6]}"
        dataset = EvalDataset(dataset_id=dataset_id, name=name, metric_type=metric_type)
        self.datasets[dataset_id] = dataset
        self._save_state()
        return dataset

    def add_dataset_entry(self, dataset_id: str, query: str, expected: str, metadata: Optional[Dict] = None) -> None:
        if dataset_id not in self.datasets:
            raise ValueError(f"Dataset {dataset_id} not found")
        entry = {"query": query, "expected": expected, "metadata": metadata or {}}
        self.datasets[dataset_id].entries.append(entry)
        self._save_state()

    def generate_traces(self, agent_name: str, dataset_id: str) -> List[EvalTrace]:
        """Simulate running agent on dataset and generate traces."""
        if dataset_id not in self.datasets:
            raise ValueError(f"Dataset {dataset_id} not found")
        dataset = self.datasets[dataset_id]
        traces = []
        for entry in dataset.entries:
            trace_id = f"trace_{agent_name}_{dataset_id}_{hashlib.md5(entry["query"].encode()).hexdigest()[:8]}"
            trace = EvalTrace(
                trace_id=trace_id,
                agent_name=agent_name,
                dataset_id=dataset_id,
                input_query=entry["query"],
                expected_output=entry["expected"],
                actual_output=f"Simulated response for: {entry['query'][:50]}...",
                score=round(0.5 + (hash(trace_id) % 40) / 100, 2),
                latency_ms=round(100 + (hash(trace_id) % 500), 2),
                timestamp=time.time(),
                rubric={"correctness": 0.7, "quality": 0.8},
            )
            traces.append(trace)
            self.traces[trace_id] = trace
        self._save_state()
        return traces

    def grade_traces(self, trace_ids: List[str]) -> Dict[str, float]:
        """Grade traces using LLM-as-judge simulation."""
        scores = {}
        for tid in trace_ids:
            if tid not in self.traces:
                continue
            trace = self.traces[tid]
            judge_score = self._simulate_llm_judge(trace)
            trace.score = judge_score
            scores[tid] = judge_score
        self._save_state()
        return scores

    def _simulate_llm_judge(self, trace: EvalTrace) -> float:
        """Simulate LLM-as-judge scoring."""
        base = 0.5
        expected = trace.expected_output.lower().split()
        actual = trace.actual_output.lower().split()
        overlap = sum(1 for w in actual if w in expected) / max(1, len(expected))
        score = base + overlap * 0.5
        return round(min(1.0, score), 3)

    def compare_agents(self, agent_names: List[str], dataset_id: str) -> Dict[str, Dict]:
        """Compare multiple agents on same dataset."""
        results = {}
        for agent in agent_names:
            agent_traces = [t for t in self.traces.values() if t.agent_name == agent and t.dataset_id == dataset_id]
            if agent_traces:
                avg_score = sum(t.score for t in agent_traces) / len(agent_traces)
                avg_latency = sum(t.latency_ms for t in agent_traces) / len(agent_traces)
                results[agent] = {
                    "avg_score": round(avg_score, 3),
                    "avg_latency_ms": round(avg_latency, 2),
                    "trace_count": len(agent_traces),
                }
        return results

    def analyze_rubric(self, trace_id: str, rubric_id: str) -> Dict[str, float]:
        """Analyze trace against rubric criteria."""
        if trace_id not in self.traces or rubric_id not in self.rubrics:
            return {}
        trace = self.traces[trace_id]
        rubric = self.rubrics[rubric_id]
        scores = {}
        for criterion, weight in rubric.criteria.items():
            scores[criterion] = round(trace.score * weight, 3)
        trace.rubric = scores
        self._save_state()
        return scores

    def optimize_rubric(self, rubric_id: str, target_score: float = 0.9) -> EvalRubric:
        """Adaptively optimize rubric weights."""
        if rubric_id not in self.rubrics:
            raise ValueError(f"Rubric {rubric_id} not found")
        rubric = self.rubrics[rubric_id]
        rubric.adaptive = True
        for key in rubric.criteria:
            rubric.criteria[key] = round(rubric.criteria[key] * (1 + (target_score - 0.5) * 0.1), 3)
        self._save_state()
        return rubric

    def get_stats(self) -> Dict:
        avg_score = sum(t.score for t in self.traces.values()) / max(1, len(self.traces))
        return {
            "datasets_total": len(self.datasets),
            "traces_total": len(self.traces),
            "rubrics_total": len(self.rubrics),
            "avg_trace_score": round(avg_score, 3),
        }

    def to_dict(self) -> Dict:
        return {
            "datasets": [d.to_dict() for d in self.datasets.values()],
            "traces": [t.to_dict() for t in self.traces.values()],
            "rubrics": [r.to_dict() for r in self.rubrics.values()],
            "stats": self.get_stats(),
        }


__all__ = ["AgentsEval", "EvalDataset", "EvalTrace", "EvalRubric"]
