"""LLM Execution Graph — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable, Set
from enum import Enum, auto

class NodeStatus(Enum):
    IDLE = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()

@dataclass
class ExecutionNode:
    id: str
    processor: Callable[[Dict[str, Any]], Any]
    inputs: List[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.IDLE
    output: Any = None
    error: Optional[str] = None

class ExecutionGraph:
    def __init__(self) -> None:
        self._nodes: Dict[str, ExecutionNode] = {}
        self._edges: Dict[str, List[str]] = {}

    def add_node(self, node: ExecutionNode) -> None:
        self._nodes[node.id] = node

    def add_edge(self, from_node: str, to_node: str) -> None:
        if from_node not in self._edges:
            self._edges[from_node] = []
        self._edges[from_node].append(to_node)

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        outputs = dict(inputs)
        executed: Set[str] = set()

        def can_execute(node: ExecutionNode) -> bool:
            return all(inp in outputs or inp in executed for inp in node.inputs)

        while len(executed) < len(self._nodes):
            progress = False
            for node in self._nodes.values():
                if node.id in executed or node.status == NodeStatus.FAILED:
                    continue
                if can_execute(node):
                    node.status = NodeStatus.RUNNING
                    try:
                        node_inputs = {inp: outputs.get(inp) for inp in node.inputs}
                        node.output = node.processor(node_inputs)
                        node.status = NodeStatus.COMPLETED
                        outputs[node.id] = node.output
                        executed.add(node.id)
                        progress = True
                    except Exception as ex:
                        node.status = NodeStatus.FAILED
                        node.error = str(ex)
            if not progress:
                break
        return outputs

    def get_stats(self) -> Dict[str, Any]:
        return {"nodes": len(self._nodes), "completed": sum(1 for n in self._nodes.values() if n.status == NodeStatus.COMPLETED), "failed": sum(1 for n in self._nodes.values() if n.status == NodeStatus.FAILED)}

def run() -> None:
    print("Execution Graph test")
    e = ExecutionGraph()
    e.add_node(ExecutionNode("n1", lambda inputs: inputs["raw"] * 2))
    e.add_node(ExecutionNode("n2", lambda inputs: inputs["n1"] + 10, inputs=["n1"]))
    e.add_node(ExecutionNode("n3", lambda inputs: inputs["n2"] / 2, inputs=["n2"]))
    e.add_edge("n1", "n2")
    e.add_edge("n2", "n3")
    outputs = e.execute({"raw": 5})
    print("  Outputs: " + str(outputs))
    print("  Stats: " + str(e.get_stats()))
    print("Execution Graph test complete.")

if __name__ == "__main__":
    run()
