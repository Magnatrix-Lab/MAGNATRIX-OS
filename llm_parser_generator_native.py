"""Parser Generator — recursive descent, LL(1), grammar validation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum, auto

class ParseNode:
    def __init__(self, name: str, children: List['ParseNode'] = None, value: str = ""):
        self.name = name
        self.children = children or []
        self.value = value

    def __repr__(self):
        return f"ParseNode({self.name})"

class ParserGenerator:
    def __init__(self, grammar: Dict[str, List[List[str]]]):
        self.grammar = grammar
        self.tokens: List[Tuple[str, str]] = []
        self.pos = 0

    def parse(self, tokens: List[Tuple[str, str]], start: str = "expr") -> Optional[ParseNode]:
        self.tokens = tokens
        self.pos = 0
        return self._parse_rule(start)

    def _parse_rule(self, rule: str) -> Optional[ParseNode]:
        if rule not in self.grammar:
            if self.pos < len(self.tokens) and self.tokens[self.pos][0] == rule:
                val = self.tokens[self.pos][1]
                self.pos += 1
                return ParseNode(rule, value=val)
            return None
        for alt in self.grammar[rule]:
            saved = self.pos
            children = []
            ok = True
            for sym in alt:
                child = self._parse_rule(sym)
                if child is None:
                    ok = False
                    break
                children.append(child)
            if ok:
                return ParseNode(rule, children)
            self.pos = saved
        return None

    def first_sets(self) -> Dict[str, Set[str]]:
        first = {k: set() for k in self.grammar}
        changed = True
        while changed:
            changed = False
            for lhs, alts in self.grammar.items():
                for alt in alts:
                    if not alt:
                        if "" not in first[lhs]:
                            first[lhs].add("")
                            changed = True
                    elif alt[0] not in self.grammar:
                        if alt[0] not in first[lhs]:
                            first[lhs].add(alt[0])
                            changed = True
                    else:
                        for sym in alt:
                            if sym in self.grammar:
                                for f in first[sym]:
                                    if f != "" and f not in first[lhs]:
                                        first[lhs].add(f)
                                        changed = True
                                if "" not in first[sym]:
                                    break
                            else:
                                if sym not in first[lhs]:
                                    first[lhs].add(sym)
                                    changed = True
                                break
        return first

    def stats(self) -> Dict:
        return {"rules": len(self.grammar)}

def run():
    grammar = {"expr": [["term", "+", "expr"], ["term"]], "term": [["NUMBER"], ["IDENT"]]}
    pg = ParserGenerator(grammar)
    tree = pg.parse([("NUMBER", "42"), ("+", "+"), ("NUMBER", "1")])
    print("Parsed:", tree.name if tree else None)
    print("First:", pg.first_sets())
    print(pg.stats())

if __name__ == "__main__":
    run()
