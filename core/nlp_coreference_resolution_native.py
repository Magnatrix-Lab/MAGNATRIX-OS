"""NLP Coreference Resolution -- Pronoun resolution, entity mentions."""
from dataclasses import dataclass
from pathlib import Path
import json, re

@dataclass
class CoreferenceChain:
    chain_id: str = ""
    mentions: list[str] = None
    head: str = ""
    entity_type: str = ""

    def __post_init__(self):
        if self.mentions is None:
            self.mentions = []

class NLPCoreferenceResolution:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._chains: list[CoreferenceChain] = []
        self._pronouns: list[str] = ["he", "she", "it", "they", "him", "her", "them", "his", "her", "their", "this", "that", "these", "those"]
        self._persist_path = self.root / "nlp_coref.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._chains = [CoreferenceChain(**c) for c in data.get("chains", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "chains": [c.__dict__ for c in self._chains]
        }, indent=2))

    def resolve(self, text: str) -> list[CoreferenceChain]:
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        chains = []

        # Find named entities (capitalized words)
        entities = []
        for sent in sentences:
            words = re.findall(r'\b[A-Z][a-z]+\b', sent)
            entities.extend(words)
        entities = list(set(entities))

        # Link pronouns to nearest entity
        for i, sent in enumerate(sentences):
            words = re.findall(r'\b\w+\b', sent)
            for w in words:
                if w.lower() in self._pronouns:
                    # Find nearest preceding entity
                    for e in reversed(entities):
                        chain = CoreferenceChain(
                            chain_id=f"chain_{len(chains)}",
                            mentions=[e, w],
                            head=e,
                            entity_type="PERSON" if w.lower() in ("he", "she", "him", "her", "his") else "THING"
                        )
                        chains.append(chain)
                        break
        self._chains.extend(chains)
        self._save()
        return chains

    def get_chains(self, entity: str) -> list[CoreferenceChain]:
        return [c for c in self._chains if c.head == entity]

    def to_dict(self) -> dict:
        return {"chain_count": len(self._chains)}

    def get_stats(self) -> dict:
        by_type = {}
        for c in self._chains:
            by_type[c.entity_type] = by_type.get(c.entity_type, 0) + 1
        return {"chains": len(self._chains), "by_type": by_type}

__all__ = ["NLPCoreferenceResolution", "CoreferenceChain"]
