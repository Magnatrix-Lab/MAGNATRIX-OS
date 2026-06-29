"""NLP POS Tagger -- Part-of-speech tagging, rule-based and statistical."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class POSTag:
    word: str = ""
    tag: str = ""
    confidence: float = 0.0

class NLPPOSTagger:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._tagged: list[list[POSTag]] = []
        self._rules: dict[str, str] = {
            "the": "DET", "a": "DET", "an": "DET",
            "is": "VB", "are": "VB", "was": "VB", "were": "VB",
            "has": "VB", "have": "VB", "had": "VB",
            "running": "VBG", "walking": "VBG", "eating": "VBG",
            "quickly": "RB", "slowly": "RB", "very": "RB",
            "happy": "JJ", "sad": "JJ", "big": "JJ", "small": "JJ",
            "dog": "NN", "cat": "NN", "car": "NN", "tree": "NN",
            "person": "NN", "place": "NN", "thing": "NN",
        }
        self._suffix_rules = {
            "ly": "RB", "ing": "VBG", "ed": "VBD", "s": "NNS",
        }
        self._persist_path = self.root / "nlp_pos.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._tagged = [[POSTag(**t) for t in sent] for sent in data.get("tagged", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "tagged": [[t.__dict__ for t in sent] for sent in self._tagged]
        }, indent=2))

    def tag(self, sentence: str) -> list[POSTag]:
        words = sentence.split()
        tags = []
        for word in words:
            w = word.lower().strip(".,!?;:'\"")
            tag = self._rules.get(w, "")
            if not tag:
                for suffix, t in self._suffix_rules.items():
                    if w.endswith(suffix):
                        tag = t
                        break
            if not tag:
                if w[0].isupper() and len(words) > 1 and words.index(word) == 0:
                    tag = "NNP"
                elif w[0].isupper():
                    tag = "NNP"
                else:
                    tag = "NN"
            tags.append(POSTag(word=word, tag=tag, confidence=0.8))
        self._tagged.append(tags)
        self._save()
        return tags

    def tag_corpus(self, sentences: list[str]) -> list[list[POSTag]]:
        return [self.tag(s) for s in sentences]

    def add_rule(self, word: str, tag: str) -> None:
        self._rules[word] = tag

    def get_tag_distribution(self) -> dict:
        dist = {}
        for sent in self._tagged:
            for t in sent:
                dist[t.tag] = dist.get(t.tag, 0) + 1
        return dist

    def to_dict(self) -> dict:
        return {"sentence_count": len(self._tagged)}

    def get_stats(self) -> dict:
        by_tag = self.get_tag_distribution()
        return {"sentences": len(self._tagged), "by_tag": by_tag}

__all__ = ["NLPPOSTagger", "POSTag"]
