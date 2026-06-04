"""Bytecode Interpreter - Simple VM for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum, auto

class OpCode(Enum):
    PUSH = auto(); ADD = auto(); SUB = auto(); MUL = auto(); DIV = auto(); POP = auto(); PRINT = auto()

@dataclass
class BytecodeInterpreter:
    stack: List[float] = field(default_factory=list)

    def execute(self, bytecode: List[Tuple[OpCode, any]]) -> None:
        for op, arg in bytecode:
            if op == OpCode.PUSH: self.stack.append(arg)
            elif op == OpCode.ADD: b, a = self.stack.pop(), self.stack.pop(); self.stack.append(a+b)
            elif op == OpCode.SUB: b, a = self.stack.pop(), self.stack.pop(); self.stack.append(a-b)
            elif op == OpCode.MUL: b, a = self.stack.pop(), self.stack.pop(); self.stack.append(a*b)
            elif op == OpCode.DIV: b, a = self.stack.pop(), self.stack.pop(); self.stack.append(a/b if b!=0 else 0)
            elif op == OpCode.POP: self.stack.pop()
            elif op == OpCode.PRINT: print("Stack top:", self.stack[-1] if self.stack else None)

    def stats(self) -> dict:
        return {"stack_size": len(self.stack), "top": self.stack[-1] if self.stack else None}

def run():
    bi = BytecodeInterpreter()
    code = [(OpCode.PUSH, 5), (OpCode.PUSH, 3), (OpCode.ADD, None), (OpCode.PUSH, 2), (OpCode.MUL, None)]
    bi.execute(code)
    print("Stats:", bi.stats())

if __name__ == "__main__": run()
