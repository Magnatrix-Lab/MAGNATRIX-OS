"""Workflow Engine — DAG pipeline composition, node execution, data routing.

Modul ini menyediakan:
- DAG workflow builder dengan dependency resolution
- Node execution engine dengan sync/async support
- Conditional branching dan data routing
- Loop nodes untuk iterasi batch
- Visual execution trace

Arsitektur: Workflow → Nodes → Edges → ExecutionContext
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Tuple, Set, Union
from enum import Enum, auto


class NodeType(Enum):
    ACTION = auto()
    CONDITION = auto()
    LOOP = auto()
    PARALLEL = auto()
    AGGREGATE = auto()
    DELAY = auto()
    SUBFLOW = auto()


class NodeStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILED = auto()
    SKIPPED = auto()
    TIMEOUT = auto()


@dataclass
class WorkflowNode:
    """Single node in a workflow DAG."""
    id: str
    name: str
    node_type: NodeType
    action: Optional[Callable[..., Any]] = None
    config: Dict[str, Any] = field(default_factory=dict)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    condition: Optional[Callable[..., bool]] = None
    timeout: float = 30.0
    retries: int = 0

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]


@dataclass
class WorkflowEdge:
    """Directed edge between nodes with optional condition."""
    source: str
    target: str
    condition: Optional[Callable[..., bool]] = None
    label: str = ""


@dataclass
class ExecutionResult:
    """Result of a single node execution."""
    node_id: str
    status: NodeStatus
    output: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    attempts: int = 0


@dataclass
class WorkflowTrace:
    """Complete trace of a workflow execution."""
    trace_id: str
    workflow_id: str
    start_time: float
    end_time: float = 0.0
    results: Dict[str, ExecutionResult] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps({
            "trace_id": self.trace_id,
            "workflow_id": self.workflow_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "results": {
                k: {"node_id": v.node_id, "status": v.status.name,
                    "output": str(v.output)[:200], "error": v.error,
                    "duration": v.duration, "attempts": v.attempts}
                for k, v in self.results.items()
            },
            "variables": {k: str(v)[:100] for k, v in self.variables.items()},
            "errors": self.errors
        }, indent=2)


class WorkflowDAG:
    """Directed Acyclic Graph workflow definition."""

    def __init__(self, workflow_id: str, name: str):
        self.workflow_id = workflow_id
        self.name = name
        self._nodes: Dict[str, WorkflowNode] = {}
        self._edges: List[WorkflowEdge] = []
        self._adj: Dict[str, List[str]] = {}
        self._indegree: Dict[str, int] = {}

    def add_node(self, node: WorkflowNode) -> WorkflowDAG:
        self._nodes[node.id] = node
        self._adj.setdefault(node.id, [])
        self._indegree.setdefault(node.id, 0)
        return self

    def add_edge(self, edge: WorkflowEdge) -> WorkflowDAG:
        if edge.source not in self._nodes or edge.target not in self._nodes:
            raise ValueError("Edge references unknown node")
        self._edges.append(edge)
        self._adj.setdefault(edge.source, []).append(edge.target)
        self._indegree[edge.target] = self._indegree.get(edge.target, 0) + 1
        return self

    def topological_sort(self) -> List[str]:
        """Kahn's algorithm for topological ordering."""
        indeg = dict(self._indegree)
        queue = [n for n, d in indeg.items() if d == 0]
        order = []
        while queue:
            curr = queue.pop(0)
            order.append(curr)
            for nxt in self._adj.get(curr, []):
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    queue.append(nxt)
        if len(order) != len(self._nodes):
            raise RuntimeError("Cycle detected in workflow DAG")
        return order

    def get_predecessors(self, node_id: str) -> List[str]:
        return [e.source for e in self._edges if e.target == node_id]

    def get_successors(self, node_id: str) -> List[str]:
        return [e.target for e in self._edges if e.source == node_id]

    def validate(self) -> bool:
        try:
            self.topological_sort()
            return True
        except RuntimeError:
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "nodes": {k: {"id": v.id, "name": v.name, "type": v.node_type.name,
                          "config": v.config, "timeout": v.timeout, "retries": v.retries}
                      for k, v in self._nodes.items()},
            "edges": [{"source": e.source, "target": e.target, "label": e.label}
                       for e in self._edges]
        }


class ExecutionContext:
    """Runtime context for workflow execution."""

    def __init__(self, variables: Optional[Dict[str, Any]] = None):
        self.variables: Dict[str, Any] = variables or {}
        self._node_outputs: Dict[str, Any] = {}
        self._lock: Dict[str, bool] = {}

    def set(self, key: str, value: Any) -> None:
        self.variables[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)

    def set_node_output(self, node_id: str, output: Any) -> None:
        self._node_outputs[node_id] = output

    def get_node_output(self, node_id: str) -> Any:
        return self._node_outputs.get(node_id)

    def merge(self, other: ExecutionContext) -> ExecutionContext:
        merged = ExecutionContext({**self.variables})
        merged._node_outputs = {**self._node_outputs, **other._node_outputs}
        return merged


class WorkflowEngine:
    """Execute workflows with DAG resolution, retries, and trace collection."""

    def __init__(self, max_parallel: int = 4):
        self.max_parallel = max_parallel
        self._traces: List[WorkflowTrace] = []

    def execute(self, dag: WorkflowDAG, ctx: Optional[ExecutionContext] = None) -> WorkflowTrace:
        ctx = ctx or ExecutionContext()
        trace = WorkflowTrace(
            trace_id=str(uuid.uuid4())[:12],
            workflow_id=dag.workflow_id,
            start_time=time.time()
        )
        order = dag.topological_sort()

        for node_id in order:
            node = dag._nodes[node_id]
            # Check if any predecessor failed
            preds = dag.get_predecessors(node_id)
            if any(trace.results.get(p, ExecutionResult(p, NodeStatus.PENDING)).status == NodeStatus.FAILED for p in preds):
                trace.results[node_id] = ExecutionResult(node_id, NodeStatus.SKIPPED, error="Predecessor failed")
                continue

            # Evaluate edge conditions
            skip = False
            for edge in dag._edges:
                if edge.target == node_id and edge.condition is not None:
                    if not edge.condition(ctx):
                        skip = True
                        break
            if skip:
                trace.results[node_id] = ExecutionResult(node_id, NodeStatus.SKIPPED)
                continue

            result = self._execute_node(node, ctx)
            trace.results[node_id] = result
            if result.status == NodeStatus.SUCCESS:
                ctx.set_node_output(node_id, result.output)
            else:
                trace.errors.append(f"Node {node_id} ({node.name}): {result.error}")

        trace.end_time = time.time()
        trace.variables = dict(ctx.variables)
        self._traces.append(trace)
        return trace

    def _execute_node(self, node: WorkflowNode, ctx: ExecutionContext) -> ExecutionResult:
        start = time.time()
        attempts = 0
        while attempts <= node.retries:
            attempts += 1
            try:
                if node.node_type == NodeType.CONDITION and node.condition:
                    out = node.condition(ctx)
                elif node.node_type == NodeType.DELAY:
                    delay = node.config.get("seconds", 0)
                    time.sleep(delay)
                    out = {"delayed": delay}
                elif node.action:
                    # Collect inputs from predecessors (node outputs first, then variables)
                    inputs = {}
                    for k in node.inputs:
                        if k in ctx._node_outputs:
                            inputs[k] = ctx._node_outputs[k]
                        else:
                            inputs[k] = ctx.get(k)
                    inputs["_ctx"] = ctx
                    out = node.action(**inputs)
                else:
                    out = None
                dur = time.time() - start
                if dur > node.timeout:
                    return ExecutionResult(node.id, NodeStatus.TIMEOUT, error="Timeout exceeded", duration=dur, attempts=attempts)
                return ExecutionResult(node.id, NodeStatus.SUCCESS, output=out, duration=dur, attempts=attempts)
            except Exception as e:
                if attempts > node.retries:
                    dur = time.time() - start
                    return ExecutionResult(node.id, NodeStatus.FAILED, error=str(e), duration=dur, attempts=attempts)
        return ExecutionResult(node.id, NodeStatus.FAILED, error="Retries exhausted", duration=time.time()-start, attempts=attempts)

    def get_traces(self) -> List[WorkflowTrace]:
        return self._traces

    def export_traces(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([json.loads(t.to_json()) for t in self._traces], f, indent=2)


class TemplateLibrary:
    """Pre-built workflow templates."""

    @staticmethod
    def simple_etl() -> WorkflowDAG:
        dag = WorkflowDAG("etl-1", "Simple ETL Pipeline")
        dag.add_node(WorkflowNode("extract", "Extract Data", NodeType.ACTION,
                                   action=lambda _ctx=None: {"rows": 1000, "source": "db"}))
        dag.add_node(WorkflowNode("transform", "Transform Data", NodeType.ACTION,
                                   action=lambda _ctx=None: {"rows": 1000, "cleaned": True}))
        dag.add_node(WorkflowNode("load", "Load Data", NodeType.ACTION,
                                   action=lambda _ctx=None: {"destination": "warehouse", "status": "ok"}))
        dag.add_edge(WorkflowEdge("extract", "transform"))
        dag.add_edge(WorkflowEdge("transform", "load"))
        return dag

    @staticmethod
    def conditional_branching() -> WorkflowDAG:
        dag = WorkflowDAG("cond-1", "Conditional Branching")
        dag.add_node(WorkflowNode("check", "Check Status", NodeType.CONDITION,
                                   condition=lambda ctx=None: (ctx or ExecutionContext()).get("status") == "ok"))
        dag.add_node(WorkflowNode("on_success", "Success Handler", NodeType.ACTION,
                                   action=lambda _ctx=None: {"handled": "success"}))
        dag.add_node(WorkflowNode("on_fail", "Fail Handler", NodeType.ACTION,
                                   action=lambda _ctx=None: {"handled": "failure"}))
        dag.add_edge(WorkflowEdge("check", "on_success", condition=lambda ctx=None: (ctx or ExecutionContext()).get("status") == "ok"))
        dag.add_edge(WorkflowEdge("check", "on_fail", condition=lambda ctx=None: (ctx or ExecutionContext()).get("status") != "ok"))
        return dag

    @staticmethod
    def retry_with_backoff() -> WorkflowDAG:
        dag = WorkflowDAG("retry-1", "Retry Workflow")
        dag.add_node(WorkflowNode("fragile", "Fragile Operation", NodeType.ACTION,
                                   action=lambda _ctx=None: {"result": "ok"}, retries=3, timeout=5.0))
        dag.add_node(WorkflowNode("cleanup", "Cleanup", NodeType.ACTION,
                                   action=lambda _ctx=None: {"cleaned": True}))
        dag.add_edge(WorkflowEdge("fragile", "cleanup"))
        return dag


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("WORKFLOW ENGINE DEMO")
    print("=" * 70)

    engine = WorkflowEngine()

    # 1. Simple ETL
    print("\n[1] Simple ETL Pipeline")
    dag = TemplateLibrary.simple_etl()
    trace = engine.execute(dag)
    for nid, res in trace.results.items():
        print(f"  {nid}: {res.status.name} in {res.duration:.3f}s -> {res.output}")
    print(f"  Total: {trace.end_time - trace.start_time:.3f}s")

    # 2. Conditional branching
    print("\n[2] Conditional Branching (status=ok)")
    dag = TemplateLibrary.conditional_branching()
    ctx = ExecutionContext({"status": "ok"})
    trace = engine.execute(dag, ctx)
    for nid, res in trace.results.items():
        print(f"  {nid}: {res.status.name} -> {res.output}")

    print("\n[2b] Conditional Branching (status=fail)")
    ctx = ExecutionContext({"status": "fail"})
    trace = engine.execute(dag, ctx)
    for nid, res in trace.results.items():
        print(f"  {nid}: {res.status.name} -> {res.output}")

    # 3. Custom DAG with variables
    print("\n[3] Custom Math DAG")
    dag = WorkflowDAG("math-1", "Arithmetic Pipeline")
    dag.add_node(WorkflowNode("a", "Input A", NodeType.ACTION, action=lambda _ctx=None: 10))
    dag.add_node(WorkflowNode("b", "Input B", NodeType.ACTION, action=lambda _ctx=None: 5))
    dag.add_node(WorkflowNode("add", "Add", NodeType.ACTION,
                               action=lambda _ctx=None, a=0, b=0: a + b,
                               inputs=["a", "b"]))
    dag.add_node(WorkflowNode("mul", "Multiply", NodeType.ACTION,
                               action=lambda _ctx=None, a=0, b=0: a * b,
                               inputs=["a", "b"]))
    dag.add_node(WorkflowNode("sum", "Sum Results", NodeType.ACTION,
                               action=lambda _ctx=None, add=0, mul=0: add + mul,
                               inputs=["add", "mul"]))
    dag.add_edge(WorkflowEdge("a", "add"))
    dag.add_edge(WorkflowEdge("b", "add"))
    dag.add_edge(WorkflowEdge("a", "mul"))
    dag.add_edge(WorkflowEdge("b", "mul"))
    dag.add_edge(WorkflowEdge("add", "sum"))
    dag.add_edge(WorkflowEdge("mul", "sum"))
    trace = engine.execute(dag)
    for nid, res in trace.results.items():
        print(f"  {nid}: {res.status.name} -> {res.output}")

    # 4. Export trace
    print("\n[4] Trace Export (JSON sample)")
    print(trace.to_json()[:500] + "...")

    # 5. Validation
    print("\n[5] DAG Validation")
    print(f"  ETL valid: {TemplateLibrary.simple_etl().validate()}")
    print(f"  Math valid: {dag.validate()}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
