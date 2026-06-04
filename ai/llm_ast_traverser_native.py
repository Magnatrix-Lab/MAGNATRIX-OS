"""AST Traverser - Abstract syntax tree walker for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from enum import Enum, auto

class TraversalType(Enum):
    PREORDER = auto(); INORDER = auto(); POSTORDER = auto()

@dataclass
class ASTNode:
    value: str
    children: List["ASTNode"] = field(default_factory=list)

@dataclass
class ASTTraverser:
    traversal_type: TraversalType = TraversalType.PREORDER

    def traverse(self, node: ASTNode, callback: Optional[Callable] = None) -> List[str]:
        result = []
        if self.traversal_type == TraversalType.PREORDER:
            result.append(node.value)
            for c in node.children: result.extend(self.traverse(c, callback))
        elif self.traversal_type == TraversalType.INORDER and len(node.children) == 2:
            result.extend(self.traverse(node.children[0], callback))
            result.append(node.value)
            result.extend(self.traverse(node.children[1], callback))
        elif self.traversal_type == TraversalType.POSTORDER:
            for c in node.children: result.extend(self.traverse(c, callback))
            result.append(node.value)
        else:
            result.append(node.value)
            for c in node.children: result.extend(self.traverse(c, callback))
        if callback: callback(node.value)
        return result

    def stats(self, node: ASTNode) -> dict:
        return {"type": self.traversal_type.name, "values": self.traverse(node)}

def run():
    root = ASTNode("+", [ASTNode("2"), ASTNode("*", [ASTNode("3"), ASTNode("4")])])
    for tt in [TraversalType.PREORDER, TraversalType.POSTORDER]:
        t = ASTTraverser(tt)
        print(f"{tt.name}: {t.traverse(root)}")
    print("Stats:", ASTTraverser().stats(root))

if __name__ == "__main__": run()
