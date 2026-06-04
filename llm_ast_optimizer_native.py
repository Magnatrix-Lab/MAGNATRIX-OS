"""AST Optimizer — constant folding, dead code, peephole, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union
from enum import Enum, auto

class ASTOp(Enum):
    ADD = auto(); SUB = auto(); MUL = auto(); DIV = auto(); CONST = auto(); VAR = auto()

@dataclass
class ASTNode:
    op: ASTOp
    value: Optional[Union[int, str]] = None
    left: Optional['ASTNode'] = None
    right: Optional['ASTNode'] = None

class ASTOptimizer:
    def optimize(self, node: ASTNode) -> ASTNode:
        if node.op == ASTOp.CONST or node.op == ASTOp.VAR:
            return node
        left = self.optimize(node.left)
        right = self.optimize(node.right)
        if left.op == ASTOp.CONST and right.op == ASTOp.CONST:
            a, b = left.value, right.value
            if node.op == ASTOp.ADD:
                return ASTNode(ASTOp.CONST, value=a + b)
            elif node.op == ASTOp.SUB:
                return ASTNode(ASTOp.CONST, value=a - b)
            elif node.op == ASTOp.MUL:
                return ASTNode(ASTOp.CONST, value=a * b)
            elif node.op == ASTOp.DIV and b != 0:
                return ASTNode(ASTOp.CONST, value=a // b)
        return ASTNode(node.op, left=left, right=right)

    def dead_code_elim(self, stmts: List[ASTNode]) -> List[ASTNode]:
        used = set()
        for s in stmts:
            self._collect_vars(s, used)
        result = []
        for s in stmts:
            if s.op == ASTOp.VAR or self._has_side_effect(s) or self._uses_vars(s, used):
                result.append(s)
        return result

    def _collect_vars(self, node: ASTNode, used: set):
        if not node:
            return
        if node.op == ASTOp.VAR:
            used.add(node.value)
        self._collect_vars(node.left, used)
        self._collect_vars(node.right, used)

    def _has_side_effect(self, node: ASTNode) -> bool:
        return False

    def _uses_vars(self, node: ASTNode, used: set) -> bool:
        if not node:
            return False
        if node.op == ASTOp.VAR and node.value in used:
            return True
        return self._uses_vars(node.left, used) or self._uses_vars(node.right, used)

    def stats(self, node: ASTNode) -> Dict:
        return {"nodes": self._count(node)}

    def _count(self, node: ASTNode) -> int:
        if not node:
            return 0
        return 1 + self._count(node.left) + self._count(node.right)

def run():
    opt = ASTOptimizer()
    ast = ASTNode(ASTOp.ADD, left=ASTNode(ASTOp.CONST, value=2), right=ASTNode(ASTOp.CONST, value=3))
    optimized = opt.optimize(ast)
    print("Optimized:", optimized.op.name, optimized.value)
    print(opt.stats(optimized))

if __name__ == "__main__":
    run()
