"""Dependency Parser — grammar rules, head-dependent, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum, auto

class DepRelation(Enum):
    SUBJ = auto()
    OBJ = auto()
    ROOT = auto()
    MOD = auto()
    COMP = auto()
    AUX = auto()

@dataclass
class DepNode:
    word: str
    pos: str
    head: Optional[int] = None
    dep_rel: Optional[DepRelation] = None
    children: List[int] = field(default_factory=list)

class DependencyParser:
    def __init__(self):
        self.rules = {
            "SUBJ": [("NOUN", "VERB"), ("PRON", "VERB")],
            "OBJ": [("NOUN", "VERB"), ("PRON", "VERB")],
            "MOD": [("ADJ", "NOUN"), ("ADV", "VERB")],
            "AUX": [("AUX", "VERB")],
        }

    def parse(self, tokens: List[Tuple[str, str]]) -> List[DepNode]:
        nodes = [DepNode(word, pos) for word, pos in tokens]
        # Simple rule-based parsing: first verb as root
        root_idx = next((i for i, n in enumerate(nodes) if n.pos == "VERB"), 0)
        nodes[root_idx].head = -1
        nodes[root_idx].dep_rel = DepRelation.ROOT
        for i, node in enumerate(nodes):
            if i == root_idx:
                continue
            for rel, patterns in self.rules.items():
                for child_pos, head_pos in patterns:
                    if node.pos == child_pos:
                        # Find nearest matching head
                        for j in range(len(nodes)):
                            if nodes[j].pos == head_pos and j != i:
                                node.head = j
                                node.dep_rel = DepRelation[rel]
                                nodes[j].children.append(i)
                                break
                        break
                if node.head is not None:
                    break
            if node.head is None:
                node.head = root_idx
                node.dep_rel = DepRelation.MOD
                nodes[root_idx].children.append(i)
        return nodes

    def to_tree(self, nodes: List[DepNode]) -> Dict:
        root = next((i for i, n in enumerate(nodes) if n.dep_rel == DepRelation.ROOT), 0)
        def build(idx):
            return {
                "word": nodes[idx].word,
                "pos": nodes[idx].pos,
                "rel": nodes[idx].dep_rel.name if nodes[idx].dep_rel else None,
                "children": [build(c) for c in nodes[idx].children]
            }
        return build(root)

    def stats(self) -> Dict:
        return {"rules": len(self.rules)}

def run():
    parser = DependencyParser()
    tokens = [("The", "DET"), ("cat", "NOUN"), ("sat", "VERB"), ("quickly", "ADV"), ("on", "PREP"), ("mat", "NOUN")]
    nodes = parser.parse(tokens)
    for n in nodes:
        print(f"{n.word} -> {n.head} ({n.dep_rel.name if n.dep_rel else None})")
    print(parser.to_tree(nodes))
    print(parser.stats())

if __name__ == "__main__":
    run()
