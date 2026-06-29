"""
flow_execution_engine_native.py
MAGNATRIX-OS — Flow Execution Engine

Inspired by Langflow (langflow-ai): Execute visual flows node-by-node with data passing.
Topological execution with caching and error handling. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class ExecutionStep:
    step_id: str
    node_id: str
    node_type: str
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, running, completed, failed
    duration_ms: float = 0.0
    error: str = ""


@dataclass
class ExecutionResult:
    run_id: str
    flow_id: str
    status: str
    steps: List[ExecutionStep] = field(default_factory=list)
    outputs: Dict[str, Any] = field(default_factory=dict)
    started_at: str = ""
    completed_at: str = ""

    def __post_init__(self):
        if not self.started_at:
            self.started_at = datetime.now().isoformat()


class FlowExecutionEngine:
    """Execute visual flows node-by-node with data passing and caching."""

    def __init__(self, cache_dir: str = "./flow_executions"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.results: Dict[str, ExecutionResult] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "results.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for rid, rd in data.items():
                        rd["steps"] = [ExecutionStep(**s) for s in rd.get("steps", [])]
                        self.results[rid] = ExecutionResult(**rd)
            except Exception:
                pass

    def _save(self) -> None:
        out = {}
        for rid, r in self.results.items():
            d = asdict(r)
            d["steps"] = [asdict(s) for s in r.steps]
            out[rid] = d
        with open(self.cache_dir / "results.json", "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)

    def _topological_sort(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[str]:
        """Sort nodes in topological order."""
        adj = {n["node_id"]: [] for n in nodes}
        in_degree = {n["node_id"]: 0 for n in nodes}
        for e in edges:
            adj[e["source"]].append(e["target"])
            in_degree[e["target"]] += 1
        queue = [n for n, d in in_degree.items() if d == 0]
        order = []
        while queue:
            node = queue.pop(0)
            order.append(node)
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        return order

    def execute(self, run_id: str, flow_id: str, nodes: List[Dict[str, Any]],
                edges: List[Dict[str, Any]], initial_inputs: Dict[str, Any]) -> ExecutionResult:
        """Execute a flow with the given nodes and edges."""
        result = ExecutionResult(run_id=run_id, flow_id=flow_id, status="running")
        node_outputs = {}
        node_map = {n["node_id"]: n for n in nodes}

        try:
            order = self._topological_sort(nodes, edges)
            for node_id in order:
                node = node_map[node_id]
                # Gather inputs from connected edges
                node_inputs = {}
                for e in edges:
                    if e["target"] == node_id and e["source"] in node_outputs:
                        node_inputs.update(node_outputs[e["source"]])
                # Merge with initial inputs if this is an input node
                if node.get("node_type") == "chat_input":
                    node_inputs.update(initial_inputs)

                step = ExecutionStep(
                    step_id=f"{run_id}_{node_id}", node_id=node_id,
                    node_type=node.get("node_type", "unknown"), input_data=node_inputs,
                )
                step.status = "running"

                # Simulate execution based on node type
                if node.get("node_type") == "llm":
                    step.output_data = {"response": f"LLM response to: {node_inputs.get('prompt', '')}"}
                elif node.get("node_type") == "memory":
                    step.output_data = {"context": f"Context: {node_inputs.get('input', '')}"}
                elif node.get("node_type") == "agent":
                    step.output_data = {"result": f"Agent result for: {node_inputs.get('task', '')}"}
                elif node.get("node_type") == "condition":
                    val = node_inputs.get("value", "")
                    cond = node.get("data", {}).get("condition", "")
                    step.output_data = {"true": val if str(val) == cond else "", "false": val if str(val) != cond else ""}
                elif node.get("node_type") == "text_splitter":
                    text = node_inputs.get("text", "")
                    chunk_size = node.get("data", {}).get("chunk_size", 1000)
                    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
                    step.output_data = {"chunks": chunks}
                else:
                    step.output_data = node_inputs

                step.status = "completed"
                node_outputs[node_id] = step.output_data
                result.steps.append(step)

            result.status = "completed"
            result.outputs = node_outputs
            result.completed_at = datetime.now().isoformat()
        except Exception as e:
            result.status = "failed"
            if result.steps:
                result.steps[-1].status = "failed"
                result.steps[-1].error = str(e)

        self.results[run_id] = result
        self._save()
        return result

    def get_result(self, run_id: str) -> Optional[ExecutionResult]:
        return self.results.get(run_id)

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.results)
        completed = sum(1 for r in self.results.values() if r.status == "completed")
        failed = sum(1 for r in self.results.values() if r.status == "failed")
        return {"total_runs": total, "completed": completed, "failed": failed}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["FlowExecutionEngine", "ExecutionResult", "ExecutionStep"]