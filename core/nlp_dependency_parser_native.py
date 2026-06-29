"""NLP Dependency Parser -- Dependency tree parsing, head/modifier relations."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class Dependency:
    head: str = ""
    dependent: str = ""
    relation: str = ""  # nsubj | dobj | pobj | amod | advmod | root
    head_index: int = 0
    dep_index: int = 0

class NLPDependencyParser:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._trees: list[list[Dependency]] = []
        self._persist_path = self.root / "nlp_dependency.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._trees = [[Dependency(**d) for d in tree] for tree in data.get("trees", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "trees": [[d.__dict__ for d in tree] for tree in self._trees]
        }, indent=2))

    def parse(self, sentence: str, pos_tags: list[str] = None) -> list[Dependency]:
        words = sentence.split()
        if pos_tags is None:
            pos_tags = ["NN"] * len(words)
        deps = []
        # Simple heuristic parsing
        root = None
        for i, (word, tag) in enumerate(zip(words, pos_tags)):
            if tag.startswith("VB") and root is None:
                root = i
                deps.append(Dependency(head="ROOT", dependent=word, relation="root", head_index=-1, dep_index=i))
        if root is None:
            root = 0
            deps.append(Dependency(head="ROOT", dependent=words[0], relation="root", head_index=-1, dep_index=0))

        for i, (word, tag) in enumerate(zip(words, pos_tags)):
            if i == root:
                continue
            if tag.startswith("NN") or tag == "NNP":
                # Check if it's likely subject or object
                if i < root:
                    deps.append(Dependency(head=words[root], dependent=word, relation="nsubj", head_index=root, dep_index=i))
                else:
                    deps.append(Dependency(head=words[root], dependent=word, relation="dobj", head_index=root, dep_index=i))
            elif tag.startswith("JJ"):
                deps.append(Dependency(head=words[root], dependent=word, relation="amod", head_index=root, dep_index=i))
            elif tag.startswith("RB"):
                deps.append(Dependency(head=words[root], dependent=word, relation="advmod", head_index=root, dep_index=i))
            elif tag == "IN":
                if i + 1 < len(words):
                    deps.append(Dependency(head=words[i+1], dependent=word, relation="case", head_index=i+1, dep_index=i))
        self._trees.append(deps)
        self._save()
        return deps

    def to_dict(self) -> dict:
        return {"tree_count": len(self._trees)}

    def get_stats(self) -> dict:
        by_relation = {}
        for tree in self._trees:
            for d in tree:
                by_relation[d.relation] = by_relation.get(d.relation, 0) + 1
        return {"trees": len(self._trees), "by_relation": by_relation}

__all__ = ["NLPDependencyParser", "Dependency"]
