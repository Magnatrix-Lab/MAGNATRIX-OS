"""LLM Dependency Parser — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class DepRelation(Enum):
    SUBJECT = auto()
    OBJECT = auto()
    MODIFIER = auto()
    ROOT = auto()
    COMPOUND = auto()
    APPOSITIVE = auto()
    CONJUNCT = auto()
    AUXILIARY = auto()
    PREPOSITIONAL = auto()
    UNKNOWN = auto()

@dataclass
class DepNode:
    id: int
    word: str
    head: int = -1
    relation: DepRelation = DepRelation.UNKNOWN
    children: List[int] = field(default_factory=list)

class DependencyParser:
    def __init__(self) -> None:
        self._subjects = {"i", "you", "he", "she", "it", "we", "they", "alice", "bob", "the", "a", "an", "this", "that"}
        self._verbs = {"is", "are", "was", "were", "be", "been", "have", "has", "had", "do", "does", "did", "will", "would", "can", "could", "may", "might", "shall", "should", "must", "run", "runs", "running", "ran", "jump", "jumps", "jumping", "jumped", "eat", "eats", "eating", "ate", "go", "goes", "going", "went", "make", "makes", "making", "made", "take", "takes", "taking", "took", "see", "sees", "seeing", "saw", "know", "knows", "knowing", "knew", "get", "gets", "getting", "got", "give", "gives", "giving", "gave", "find", "finds", "finding", "found", "think", "thinks", "thinking", "thought", "tell", "tells", "telling", "told", "become", "becomes", "becoming", "became", "show", "shows", "showing", "showed", "leave", "leaves", "leaving", "left", "feel", "feels", "feeling", "felt", "put", "puts", "putting", "bring", "brings", "bringing", "brought", "begin", "begins", "beginning", "began", "keep", "keeps", "keeping", "kept", "hold", "holds", "holding", "held", "write", "writes", "writing", "wrote", "stand", "stands", "standing", "stood", "hear", "hears", "hearing", "heard", "let", "lets", "letting", "mean", "means", "meaning", "meant", "set", "sets", "setting", "meet", "meets", "meeting", "met", "pay", "pays", "paying", "paid", "sit", "sits", "sitting", "sat", "speak", "speaks", "speaking", "spoke", "lie", "lies", "lying", "lay", "lead", "leads", "leading", "led", "read", "reads", "reading", "grow", "grows", "growing", "grew", "lose", "loses", "losing", "lost", "add", "adds", "adding", "added", "spend", "spends", "spending", "spent"}
        self._prepositions = {"in", "on", "at", "to", "for", "with", "from", "by", "about", "into", "through", "during", "before", "after", "above", "below", "between", "under", "of", "off", "over", "up", "down", "out", "again", "further", "then", "once"}
        self._auxiliaries = {"is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "shall", "should", "can", "could", "may", "might", "must"}

    def parse(self, words: List[str]) -> List[DepNode]:
        nodes = [DepNode(i, w) for i, w in enumerate(words)]
        root = -1
        for i, word in enumerate(words):
            lower = word.lower()
            if lower in self._verbs and root == -1:
                root = i
                nodes[i].relation = DepRelation.ROOT
        if root == -1:
            root = 0
            nodes[0].relation = DepRelation.ROOT
        for i, word in enumerate(words):
            if i == root:
                continue
            lower = word.lower()
            if lower in self._subjects and i < root:
                nodes[i].head = root
                nodes[i].relation = DepRelation.SUBJECT
                nodes[root].children.append(i)
            elif lower in self._verbs and i != root:
                nodes[i].head = root
                nodes[i].relation = DepRelation.AUXILIARY
                nodes[root].children.append(i)
            elif lower in self._prepositions:
                nodes[i].head = root
                nodes[i].relation = DepRelation.PREPOSITIONAL
                nodes[root].children.append(i)
            elif i > root:
                nodes[i].head = root
                nodes[i].relation = DepRelation.OBJECT
                nodes[root].children.append(i)
            else:
                nodes[i].head = root
                nodes[i].relation = DepRelation.MODIFIER
                nodes[root].children.append(i)
        return nodes

    def to_tree(self, nodes: List[DepNode]) -> Dict[str, Any]:
        root = next((n for n in nodes if n.relation == DepRelation.ROOT), None)
        if not root:
            return {}
        def build_tree(node_id: int) -> Dict[str, Any]:
            node = nodes[node_id]
            return {
                "word": node.word,
                "relation": node.relation.name,
                "children": [build_tree(c) for c in node.children]
            }
        return build_tree(root.id)

    def get_stats(self, nodes: List[DepNode]) -> Dict[str, Any]:
        counts = {}
        for n in nodes:
            counts[n.relation.name] = counts.get(n.relation.name, 0) + 1
        return {"nodes": len(nodes), "by_relation": counts, "root": next((n.word for n in nodes if n.relation == DepRelation.ROOT), "None")}

def run() -> None:
    print("Dependency Parser test")
    e = DependencyParser()
    words = ["Alice", "quickly", "runs", "to", "the", "store", "in", "Tokyo"]
    nodes = e.parse(words)
    for n in nodes:
        print("  " + n.word + " -> head=" + str(n.head) + " rel=" + n.relation.name)
    tree = e.to_tree(nodes)
    print("  Tree root: " + tree.get("word", "None"))
    print("  Stats: " + str(e.get_stats(nodes)))
    print("Dependency Parser test complete.")

if __name__ == "__main__":
    run()
