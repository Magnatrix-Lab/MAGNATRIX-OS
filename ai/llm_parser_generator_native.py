"""Parser Generator - Recursive descent parser for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto

class ASTNodeType(Enum):
    BINARY = auto(); UNARY = auto(); LITERAL = auto(); IDENTIFIER = auto()

@dataclass
class ASTNode:
    node_type: ASTNodeType
    value: str
    left: Optional["ASTNode"] = None
    right: Optional["ASTNode"] = None

@dataclass
class ParserGenerator:
    tokens: List[Tuple[str, str]] = field(default_factory=list)
    pos: int = 0

    def parse(self, tokens: List[Tuple[str, str]]) -> Optional[ASTNode]:
        self.tokens = tokens; self.pos = 0
        return self.expr()

    def expr(self) -> Optional[ASTNode]:
        left = self.term()
        while self.pos < len(self.tokens) and self.tokens[self.pos][1] in "+-":
            op = self.tokens[self.pos][1]; self.pos += 1
            right = self.term()
            left = ASTNode(ASTNodeType.BINARY, op, left, right)
        return left

    def term(self) -> Optional[ASTNode]:
        tok = self.tokens[self.pos] if self.pos < len(self.tokens) else ("", "")
        self.pos += 1
        if tok[0] == "NUMBER": return ASTNode(ASTNodeType.LITERAL, tok[1])
        if tok[0] == "IDENTIFIER": return ASTNode(ASTNodeType.IDENTIFIER, tok[1])
        return None

    def stats(self) -> dict:
        return {"tokens": len(self.tokens), "pos": self.pos}

def run():
    pg = ParserGenerator()
    tokens = [("NUMBER", "2"), ("OPERATOR", "+"), ("NUMBER", "3"), ("OPERATOR", "*"), ("NUMBER", "4")]
    ast = pg.parse(tokens)
    print("AST:", ast.value if ast else None)
    print("Stats:", pg.stats())

if __name__ == "__main__": run()
