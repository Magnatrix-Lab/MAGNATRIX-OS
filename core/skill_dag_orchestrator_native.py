"""
skill_dag_orchestrator_native.py
MAGNATRIX-OS — Skill DAG Orchestrator

Inspired by AgentSkillOS: Compose skills into DAG workflows with dependency management. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class DAGNode:
    node_id: str
    skill_id: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, running, completed, failed
    duration_ms: float = 0.0


@dataclass
class SkillDAG:
    dag_id: str
    name: str
    nodes: Dict[str, DAGNode] = field(default_factory=dict)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class SkillDAGOrchestrator:
    """Compose skills into directed acyclic graph workflows."""

    def __init__(self, cache_dir: str = "./skill_dags"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.dags: Dict[str, SkillDAG] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "dags.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for dag_id, dd in data.items():
                        nodes = {nid: DAGNode(**nd) for nid, nd in dd.get("nodes", {}).items()}
                        self.dags[dag_id] = SkillDAG(
                            dag_id=dag_id, name=dd["name"], nodes=nodes, created_at=dd.get("created_at", ""),
                        )
            except Exception:
                pass

    def _save(self) -> None:
        out = {}
        for dag_id, dag in self.dags.items():
            d = asdict(dag)
            d["nodes"] = {nid: asdict(n) for nid, n in dag.nodes.items()}
            out[dag_id] = d
        with open(self.cache_dir / "dags.json", "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)

    def create_dag(self, dag_id: str, name: str) -> SkillDAG:
        dag = SkillDAG(dag_id=dag_id, name=name)
        self.dags[dag_id] = dag
        self._save()
        return dag

    def add_node(self, dag_id: str, node_id: str, skill_id: str, dependencies: Optional[List[str]] = None) -> bool:
        dag = self.dags.get(dag_id)
        if not dag:
            return False
        dag.nodes[node_id] = DAGNode(
            node_id=node_id, skill_id=skill_id, dependencies=dependencies or [],
        )
        self._save()
        return True

    def topological_sort(self, dag_id: str) -> List[str]:
        """Topological sort of DAG nodes for execution order."""
        dag = self.dags.get(dag_id)
        if not dag:
            return []
        in_degree = {nid: 0 for nid in dag.nodes}
        for node in dag.nodes.values():
            for dep in node.dependencies:
                if dep in in_degree:
                    in_degree[nid] = in_degree.get(nid, 0) + 1
        # Kahn's algorithm
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        result = []
        while queue:
            current = queue.pop(0)
            result.append(current)
            for nid, node in dag.nodes.items():
                if current in node.dependencies:
                    in_degree[nid] -= 1
                    if in_degree[nid] == 0:
                        queue.append(nid)
        return result

    def execute(self, dag_id: str) -> Dict[str, Any]:
        """Execute DAG in topological order."""
        dag = self.dags.get(dag_id)
        if not dag:
            return {"error": "DAG not found"}
        order = self.topological_sort(dag_id)
        for nid in order:
            node = dag.nodes[nid]
            node.status = "running"
            # Simulate execution
            import time
            start = time.time()
            node.outputs = {"result": f"Executed {node.skill_id}", "node_id": nid}
            node.duration_ms = round((time.time() - start) * 1000, 2)
            node.status = "completed"
        self._save()
        return {"dag_id": dag_id, "executed": len(order), "order": order}

    def get_dag(self, dag_id: str) -> Optional[SkillDAG]:
        return self.dags.get(dag_id)

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.dags)
        total_nodes = sum(len(d.nodes) for d in self.dags.values())
        return {"total_dags": total, "total_nodes": total_nodes}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["SkillDAGOrchestrator", "SkillDAG", "DAGNode"]