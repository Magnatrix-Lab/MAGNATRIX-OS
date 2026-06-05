"""Circuit Builder — combinational logic, netlist, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum, auto

class CircuitBuilder:
    def __init__(self):
        self.nodes: Dict[str, Dict] = {}
        self.connections: List[Tuple[str, str]] = []

    def add_input(self, name: str):
        self.nodes[name] = {"type": "input", "value": False, "inputs": []}

    def add_output(self, name: str):
        self.nodes[name] = {"type": "output", "value": False, "inputs": []}

    def add_gate(self, name: str, gate_type: str, inputs: List[str]):
        self.nodes[name] = {"type": "gate", "gate_type": gate_type, "inputs": inputs, "value": False}

    def connect(self, from_node: str, to_node: str):
        self.connections.append((from_node, to_node))
        if to_node in self.nodes:
            self.nodes[to_node]["inputs"].append(from_node)

    def _eval_gate(self, gate_type: str, inputs: List[bool]) -> bool:
        if gate_type == "AND":
            return all(inputs)
        elif gate_type == "OR":
            return any(inputs)
        elif gate_type == "NOT":
            return not inputs[0] if inputs else True
        elif gate_type == "XOR":
            return sum(inputs) % 2 == 1
        elif gate_type == "NAND":
            return not all(inputs)
        return False

    def simulate(self, inputs: Dict[str, bool]) -> Dict[str, bool]:
        for name, val in inputs.items():
            if name in self.nodes:
                self.nodes[name]["value"] = val
        # Evaluate in topological order (simple: repeat until stable)
        for _ in range(len(self.nodes)):
            for name, node in self.nodes.items():
                if node["type"] == "gate":
                    vals = [self.nodes[i]["value"] for i in node["inputs"] if i in self.nodes]
                    node["value"] = self._eval_gate(node["gate_type"], vals)
                elif node["type"] == "output":
                    vals = [self.nodes[i]["value"] for i in node["inputs"] if i in self.nodes]
                    node["value"] = vals[0] if vals else False
        return {k: v["value"] for k, v in self.nodes.items()}

    def to_netlist(self) -> List[str]:
        lines = []
        for name, node in self.nodes.items():
            if node["type"] == "gate":
                lines.append(f"{name} = {node['gate_type']}({', '.join(node['inputs'])})")
        return lines

    def stats(self) -> Dict:
        return {"nodes": len(self.nodes), "connections": len(self.connections)}

def run():
    cb = CircuitBuilder()
    cb.add_input("A")
    cb.add_input("B")
    cb.add_gate("g1", "AND", ["A", "B"])
    cb.add_output("Y")
    cb.connect("g1", "Y")
    print(cb.simulate({"A": True, "B": False}))
    print(cb.to_netlist())
    print(cb.stats())

if __name__ == "__main__":
    run()
