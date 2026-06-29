"""NLP Text Similarity -- LSA, cosine similarity, Jaccard, Levenshtein."""
from dataclasses import dataclass
from pathlib import Path
import json, math, re

@dataclass
class SimilarityResult:
    pair_id: str = ""
    text_a: str = ""
    text_b: str = ""
    cosine_sim: float = 0.0
    jaccard_sim: float = 0.0
    levenshtein_dist: int = 0
    combined_score: float = 0.0

class NLPTextSimilarity:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._results: list[SimilarityResult] = []
        self._vocab: set[str] = set()
        self._persist_path = self.root / "nlp_similarity.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._results = [SimilarityResult(**r) for r in data.get("results", [])]
            self._vocab = set(data.get("vocab", []))

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "results": [r.__dict__ for r in self._results],
            "vocab": list(self._vocab)
        }, indent=2))

    def _tokenize(self, text: str) -> list[str]:
        return [re.sub(r'[^\w]', '', w.lower()) for w in text.split() if re.sub(r'[^\w]', '', w.lower())]

    def _vectorize(self, tokens: list[str]) -> dict[str, int]:
        vec = {}
        for t in tokens:
            vec[t] = vec.get(t, 0) + 1
            self._vocab.add(t)
        return vec

    def cosine_similarity(self, text_a: str, text_b: str) -> float:
        a_tokens = self._tokenize(text_a)
        b_tokens = self._tokenize(text_b)
        a_vec = self._vectorize(a_tokens)
        b_vec = self._vectorize(b_tokens)
        dot = sum(a_vec.get(k, 0) * b_vec.get(k, 0) for k in set(a_vec) | set(b_vec))
        norm_a = math.sqrt(sum(v * v for v in a_vec.values()))
        norm_b = math.sqrt(sum(v * v for v in b_vec.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def jaccard_similarity(self, text_a: str, text_b: str) -> float:
        a_set = set(self._tokenize(text_a))
        b_set = set(self._tokenize(text_b))
        intersection = len(a_set & b_set)
        union = len(a_set | b_set)
        return intersection / union if union > 0 else 0.0

    def levenshtein_distance(self, text_a: str, text_b: str) -> int:
        a = text_a.lower()
        b = text_b.lower()
        if len(a) < len(b):
            a, b = b, a
        if len(b) == 0:
            return len(a)
        previous_row = list(range(len(b) + 1))
        for i, c1 in enumerate(a):
            current_row = [i + 1]
            for j, c2 in enumerate(b):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    def compare(self, pair_id: str, text_a: str, text_b: str) -> SimilarityResult:
        cos = self.cosine_similarity(text_a, text_b)
        jac = self.jaccard_similarity(text_a, text_b)
        lev = self.levenshtein_distance(text_a, text_b)
        combined = round((cos + jac) / 2, 4)
        result = SimilarityResult(
            pair_id=pair_id, text_a=text_a, text_b=text_b,
            cosine_sim=round(cos, 4), jaccard_sim=round(jac, 4),
            levenshtein_dist=lev, combined_score=combined
        )
        self._results.append(result)
        self._save()
        return result

    def to_dict(self) -> dict:
        return {"comparison_count": len(self._results), "vocab_size": len(self._vocab)}

    def get_stats(self) -> dict:
        avg_cos = sum(r.cosine_sim for r in self._results) / len(self._results) if self._results else 0
        avg_jac = sum(r.jaccard_sim for r in self._results) / len(self._results) if self._results else 0
        return {"comparisons": len(self._results), "avg_cosine": round(avg_cos, 3), "avg_jaccard": round(avg_jac, 3)}

__all__ = ["NLPTextSimilarity", "SimilarityResult"]
