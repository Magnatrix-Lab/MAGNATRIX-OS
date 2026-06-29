"""NLP Constituency Parser -- Phrase structure grammar, parse trees."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class ParseTreeNode:
    label: str = ""
    children: list = None
    text: str = ""

    def __post_init__(self):
        if self.children is None:
            self.children = []

class NLPConstituencyParser:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._trees: list[ParseTreeNode] = []
        self._grammar: dict[str, list[str]] = {
            "S": ["NP VP", "S PP"],
            "NP": ["DET N", "ADJ N", "N", "NP PP"],
            "VP": ["V NP", "V PP", "V", "VP PP"],
            "PP": ["P NP"],
            "DET": ["the", "a", "an"],
            "N": ["dog", "cat", "car", "tree", "person", "house", "book", "idea"],
            "V": ["runs", "jumps", "drives", "reads", "eats", "loves", "sees", "finds"],
            "ADJ": ["big", "small", "happy", "sad", "quick", "slow", "red", "blue"],
            "P": ["in", "on", "at", "with", "by", "from", "to", "of"],
        }
        self._persist_path = self.root / "nlp_constituency.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._trees = [ParseTreeNode(**t) for t in data.get("trees", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "trees": [self._node_to_dict(t) for t in self._trees]
        }, indent=2))

    def _node_to_dict(self, node: ParseTreeNode) -> dict:
        return {
            "label": node.label,
            "text": node.text,
            "children": [self._node_to_dict(c) for c in node.children]
        }

    def parse(self, sentence: str) -> ParseTreeNode:
        words = sentence.split()
        root = ParseTreeNode(label="S")
        # Simple heuristic: first noun phrase, then verb phrase
        np = ParseTreeNode(label="NP")
        vp = ParseTreeNode(label="VP")

        for i, word in enumerate(words):
            w = word.lower().strip(".,!?")
            if w in self._grammar.get("DET", []) or w in self._grammar.get("ADJ", []) or w in self._grammar.get("N", []):
                if not vp.children:
                    np.children.append(ParseTreeNode(label="WORD", text=w))
                else:
                    vp.children.append(ParseTreeNode(label="WORD", text=w))
            elif w in self._grammar.get("V", []):
                vp.children.append(ParseTreeNode(label="WORD", text=w))
            elif w in self._grammar.get("P", []):
                pp = ParseTreeNode(label="PP")
                pp.children.append(ParseTreeNode(label="WORD", text=w))
                if i + 1 < len(words):
                    pp.children.append(ParseTreeNode(label="WORD", text=words[i+1].lower().strip(".,!?")))
                if vp.children:
                    vp.children.append(pp)
                else:
                    np.children.append(pp)

        if np.children:
            root.children.append(np)
        if vp.children:
            root.children.append(vp)
        self._trees.append(root)
        self._save()
        return root

    def to_dict(self) -> dict:
        return {"tree_count": len(self._trees)}

    def get_stats(self) -> dict:
        by_label = {}
        for tree in self._trees:
            self._count_labels(tree, by_label)
        return {"trees": len(self._trees), "by_label": by_label}

    def _count_labels(self, node: ParseTreeNode, counts: dict) -> None:
        counts[node.label] = counts.get(node.label, 0) + 1
        for c in node.children:
            self._count_labels(c, counts)

__all__ = ["NLPConstituencyParser", "ParseTreeNode"]
