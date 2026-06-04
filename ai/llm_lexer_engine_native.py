"""Lexer Engine - Token lexer for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import re

class TokenType(Enum):
    NUMBER = auto(); IDENTIFIER = auto(); OPERATOR = auto(); KEYWORD = auto(); STRING = auto(); EOF = auto()

@dataclass
class LexerEngine:
    keywords: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.keywords: self.keywords = ["if", "else", "while", "for", "return", "def", "class"]

    def tokenize(self, code: str) -> List[Tuple[TokenType, str]]:
        tokens = []
        i = 0
        while i < len(code):
            if code[i].isspace(): i += 1; continue
            m = re.match(r"\d+", code[i:])
            if m: tokens.append((TokenType.NUMBER, m.group())); i += m.end(); continue
            m = re.match(r'"[^"]*"', code[i:])
            if m: tokens.append((TokenType.STRING, m.group())); i += m.end(); continue
            m = re.match(r"[a-zA-Z_][a-zA-Z0-9_]*", code[i:])
            if m:
                word = m.group()
                ttype = TokenType.KEYWORD if word in self.keywords else TokenType.IDENTIFIER
                tokens.append((ttype, word)); i += m.end(); continue
            if code[i] in "+-*/=<>(){}[];:": tokens.append((TokenType.OPERATOR, code[i])); i += 1; continue
            i += 1
        tokens.append((TokenType.EOF, ""))
        return tokens

    def stats(self, code: str) -> dict:
        tokens = self.tokenize(code)
        counts = {}
        for t, _ in tokens: counts[t.name] = counts.get(t.name, 0) + 1
        return {"tokens": len(tokens), "counts": counts}

def run():
    le = LexerEngine()
    code = 'def foo(x): return x + 10'
    print("Tokens:", [(t.name, v) for t, v in le.tokenize(code)])
    print("Stats:", le.stats(code))

if __name__ == "__main__": run()
