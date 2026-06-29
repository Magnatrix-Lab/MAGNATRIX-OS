"""
flow_execution_engine_native.py
MAGNATRIX-OS — Flow Execution Engine

Inspired by langflow-ai/langflow workflow execution:
Execute node-based flows with topological ordering and error handling. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class ExecutionResult:
    node_id: str
    status: str
    output: Any
    duration_ms: float
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class FlowExecutionEngine:
    """Execute node-based flows with topological ordering."""

    def __init__(self, exec_dir: str = "./flow_executions"):
        self.exec_dir = Path(exec_dir)
        self.exec_dir.mkdir(exist_ok=True)
        self.results: Dict[str, List[ExecutionResult]] = {}
        self._load()

    def _load(self) -> None:
        file = self.exec_dir / "results.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for run_id, results in data.items():
                        self.results[run_id] = [ExecutionResult(**r) for r in results]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.exec_dir / "results.json", "w", encoding="utf-8") as f:
            json.dump({k: [asdict(r) for r in v] for k, v in self.results.items()}, f, indent=2)

    def _topological_sort(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, str]]) -> List[str]:
        """Topological sort of nodes based on edges."""
        adj = {n["node_id"]: [] for n in nodes}
        in_degree = {n["node_id"]: 0 for n in nodes}
        for edge in edges:
            adj[edge["source"]].append(edge["target"])
            in_degree[edge["target"]] += 1
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
                edges: List[Dict[str, str]], inputs: Optional[Dict[str, Any]] = None) -> List[ExecutionResult]:
        """Execute a flow with given nodes and edges."""
        import time
        order = self._topological_sort(nodes, edges)
        results = []
        node_map = {n["node_id"]: n for n in nodes}
        state = inputs or {}
        for node_id in order:
            node = node_map.get(node_id)
            if not node:
                continue
            start = time.time()
            try:
                # Simulate execution based on node type
                node_type = node.get("node_type", "unknown")
                if node_type == "input":
                    output = state.get(node_id, {})
                elif node_type == "prompt":
                    template = node.get("config", {}).get("template", "")
                    output = template.format(**state)
                elif node_type == "llm":
                    prompt = state.get("prompt", "")
                    output = f"LLM response to: {prompt[:50]}..."
                elif node_type == "output":
                    output = state.get(node_id, "")
                elif node_type == "memory":
                    output = state.get("history", [])
                elif node_type == "tool":
                    tool_name = node.get("config", {}).get("tool_name", "")
                    output = f"Tool {tool_name} executed"
                elif node_type == "condition":
                    condition = state.get("condition", True)
                    output = "true_branch" if condition else "false_branch"
                else:
                    output = f"Executed {node_type}"
                state[node_id] = output
                duration = (time.time() - start) * 1000
                result = ExecutionResult(
                    node_id=node_id, status="success", output=output, duration_ms=round(duration, 2),
                )
            except Exception as e:
                duration = (time.time() - start) * 1000
                result = ExecutionResult(
                    node_id=node_id, status="error", output=str(e), duration_ms=round(duration, 2),
                )
            results.append(result)
        self.results[run_id] = results
        self._save()
        return results

    def get_run(self, run_id: str) -> List[ExecutionResult]:
        return self.results.get(run_id, [])

    def get_stats(self) -> Dict[str, Any]:
        total = sum(len(v) for v in self.results.values())
        success = sum(1 for v in self.results.values() for r in v if r.status == "success")
        return {"total_executions": len(self.results), "total_node_runs": total, "success": success}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["FlowExecutionEngine", "ExecutionResult"]