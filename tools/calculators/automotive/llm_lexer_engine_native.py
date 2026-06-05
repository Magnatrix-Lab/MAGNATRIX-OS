"""Lexer Engine — tokenization, DFA, regex-based, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import re

class TokenType(Enum):
    NUMBER = auto(); IDENT = auto(); OP = auto(); KEYWORD = auto(); STRING = auto(); WS = auto(); EOF = auto()

@dataclass
class Token:
    type: TokenType
    value: str
    pos: int

class LexerEngine:
    def __init__(self):
        self.patterns = [
            (TokenType.KEYWORD, r'(if|else|while|for|return|def|class)'),
            (TokenType.NUMBER, r'\d+(\.\d+)?'),
            (TokenType.IDENT, r'[a-zA-Z_][a-zA-Z0-9_]*'),
            (TokenType.OP, r'[+−*/=<>!&|]+|==|!=|<=|>='),
            (TokenType.STRING, r'"[^"]*"|\'[^\']*\''),
            (TokenType.WS, r'\s+'),
        ]

    def tokenize(self, text: str) -> List[Token]:
        tokens = []
        pos = 0
        while pos < len(text):
            match = None
            for ttype, pattern in self.patterns:
                regex = re.compile(pattern)
                m = regex.match(text, pos)
                if m:
                    match = (ttype, m)
                    break
            if not match:
                pos += 1
                continue
            ttype, m = match
            if ttype != TokenType.WS:
                tokens.append(Token(ttype, m.group(), pos))
            pos = m.end()
        tokens.append(Token(TokenType.EOF, "", pos))
        return tokens

    def stats(self, tokens: List[Token]) -> Dict:
        counts = {}
        for t in tokens:
            counts[t.type.name] = counts.get(t.type.name, 0) + 1
        return {"tokens": len(tokens), "types": counts}

def run():
    lex = LexerEngine()
    tokens = lex.tokenize("def foo(x): return x + 42")
    print([(t.type.name, t.value) for t in tokens])
    print(lex.stats(tokens))

if __name__ == "__main__":
    run()
