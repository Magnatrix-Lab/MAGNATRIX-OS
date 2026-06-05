"""Gate Simulator — AND, OR, NOT, XOR, NAND, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto

class GateType(Enum):
    AND = auto()
    OR = auto()
    NOT = auto()
    XOR = auto()
    NAND = auto()
    NOR = auto()

class GateSimulator:
    def __init__(self):
        self.gates: Dict[str, Dict] = {}
        self.wires: Dict[str, bool] = {}

    def add_input(self, name: str, value: bool):
        self.wires[name] = value

    def add_gate(self, gate_id: str, gate_type: GateType, inputs: List[str], output: str):
        self.gates[gate_id] = {"type": gate_type, "inputs": inputs, "output": output}

    def evaluate(self, gate_id: str) -> bool:
        gate = self.gates[gate_id]
        vals = [self.wires.get(i, False) for i in gate["inputs"]]
        gt = gate["type"]
        if gt == GateType.AND:
            result = all(vals)
        elif gt == GateType.OR:
            result = any(vals)
        elif gt == GateType.NOT:
            result = not vals[0] if vals else True
        elif gt == GateType.XOR:
            result = sum(vals) % 2 == 1
        elif gt == GateType.NAND:
            result = not all(vals)
        elif gt == GateType.NOR:
            result = not any(vals)
        else:
            result = False
        self.wires[gate["output"]] = result
        return result

    def simulate(self) -> Dict:
        for gate_id in self.gates:
            self.evaluate(gate_id)
        return {k: v for k, v in self.wires.items()}

    def stats(self) -> Dict:
        return {"gates": len(self.gates), "wires": len(self.wires)}

def run():
    sim = GateSimulator()
    sim.add_input("A", True)
    sim.add_input("B", False)
    sim.add_gate("g1", GateType.AND, ["A", "B"], "C")
    sim.add_gate("g2", GateType.OR, ["A", "B"], "D")
    sim.add_gate("g3", GateType.NOT, ["C"], "E")
    print(sim.simulate())
    print(sim.stats())

if __name__ == "__main__":
    run()
