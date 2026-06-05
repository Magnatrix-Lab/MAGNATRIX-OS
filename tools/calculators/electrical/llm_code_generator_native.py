"""Code Generator — target assembly, register allocation, instruction selection, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set

@dataclass
class Instruction:
    opcode: str
    operands: List[str] = field(default_factory=list)

class CodeGenerator:
    def __init__(self):
        self.instrs: List[Instruction] = []
        self.registers: Dict[str, str] = {}
        self.reg_pool = ["R0", "R1", "R2", "R3", "R4", "R5"]
        self.used_regs: Set[str] = set()

    def allocate_reg(self, var: str) -> str:
        if var in self.registers:
            return self.registers[var]
        for r in self.reg_pool:
            if r not in self.used_regs:
                self.registers[var] = r
                self.used_regs.add(r)
                return r
        self.registers[var] = self.reg_pool[0]
        return self.reg_pool[0]

    def emit(self, opcode: str, *operands: str):
        self.instrs.append(Instruction(opcode, list(operands)))

    def generate_arith(self, op: str, dest: str, src1: str, src2: str):
        r1 = self.allocate_reg(src1)
        r2 = self.allocate_reg(src2)
        rd = self.allocate_reg(dest)
        self.emit("LOAD", r1, src1)
        self.emit("LOAD", r2, src2)
        if op == "+":
            self.emit("ADD", rd, r1, r2)
        elif op == "-":
            self.emit("SUB", rd, r1, r2)
        elif op == "*":
            self.emit("MUL", rd, r1, r2)
        self.emit("STORE", rd, dest)

    def generate_program(self, ops: List[Tuple[str, str, str, str]]):
        for op, dest, s1, s2 in ops:
            self.generate_arith(op, dest, s1, s2)

    def stats(self) -> Dict:
        return {"instructions": len(self.instrs), "registers_used": len(self.used_regs)}

def run():
    cg = CodeGenerator()
    cg.generate_program([("+", "t1", "a", "b"), ("*", "t2", "t1", "c")])
    print([(i.opcode, i.operands) for i in cg.instrs])
    print(cg.stats())

if __name__ == "__main__":
    run()
