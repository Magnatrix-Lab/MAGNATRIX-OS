"""IR Generator — three-address code, basic blocks, CFG, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum, auto

class IROp(Enum):
    ADD = auto(); SUB = auto(); MUL = auto(); DIV = auto(); LOAD = auto(); STORE = auto(); LABEL = auto(); JMP = auto(); BR = auto(); RET = auto()

@dataclass
class IRInstr:
    op: IROp
    dest: str = ""
    src1: str = ""
    src2: str = ""
    label: str = ""

@dataclass
class BasicBlock:
    label: str
    instrs: List[IRInstr] = field(default_factory=list)
    successors: List[str] = field(default_factory=list)
    predecessors: List[str] = field(default_factory=list)

class IRGenerator:
    def __init__(self):
        self.instrs: List[IRInstr] = []
        self.temp_count = 0
        self.blocks: Dict[str, BasicBlock] = {}
        self.current_block = "entry"

    def _new_temp(self) -> str:
        self.temp_count += 1
        return f"t{self.temp_count}"

    def emit(self, op: IROp, dest: str = "", src1: str = "", src2: str = "", label: str = ""):
        self.instrs.append(IRInstr(op, dest, src1, src2, label))

    def emit_binop(self, op: IROp, left: str, right: str) -> str:
        t = self._new_temp()
        self.emit(op, t, left, right)
        return t

    def emit_label(self, label: str):
        self.emit(IROp.LABEL, label=label)
        self.current_block = label
        self.blocks[label] = BasicBlock(label)

    def build_cfg(self):
        for i, instr in enumerate(self.instrs):
            if instr.op == IROp.LABEL:
                self.blocks[instr.label] = BasicBlock(instr.label)
        for i, instr in enumerate(self.instrs):
            if instr.op == IROp.JMP and instr.label:
                self.blocks[self.current_block].successors.append(instr.label)
            elif instr.op == IROp.BR and instr.label:
                self.blocks[self.current_block].successors.append(instr.label)

    def stats(self) -> Dict:
        return {"instrs": len(self.instrs), "blocks": len(self.blocks), "temps": self.temp_count}

def run():
    ir = IRGenerator()
    t1 = ir.emit_binop(IROp.ADD, "a", "b")
    t2 = ir.emit_binop(IROp.MUL, t1, "c")
    ir.emit(IROp.STORE, "result", t2)
    ir.emit_label("exit")
    ir.emit(IROp.RET, src1="result")
    print(ir.stats())

if __name__ == "__main__":
    run()
