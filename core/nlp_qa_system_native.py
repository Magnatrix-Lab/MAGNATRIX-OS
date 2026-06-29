"""NLP QA System -- Retrieval-based question answering, passage scoring."""
from dataclasses import dataclass
from pathlib import Path
import json, re

@dataclass
class QAResult:
    question_id: str = ""
    question: str = ""
    answer: str = ""
    passage: str = ""
    confidence: float = 0.0

class NLPQASystem:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._passages: list[str] = []
        self._results: list[QAResult] = []
        self._persist_path = self.root / "nlp_qa.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._passages = data.get("passages", [])
            self._results = [QAResult(**r) for r in data.get("results", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "passages": self._passages,
            "results": [r.__dict__ for r in self._results]
        }, indent=2))

    def add_passage(self, passage: str) -> None:
        self._passages.append(passage)
        self._save()

    def answer(self, question_id: str, question: str) -> QAResult:
        q_words = set(re.sub(r'[^\w]', '', w.lower()) for w in question.split())
        best_passage = ""
        best_score = 0
        for passage in self._passages:
            p_words = set(re.sub(r'[^\w]', '', w.lower()) for w in passage.split())
            overlap = len(q_words & p_words)
            score = overlap / len(q_words) if q_words else 0
            if score > best_score:
                best_score = score
                best_passage = passage
        # Extract answer: first sentence containing overlap words
        answer = ""
        if best_passage:
            for sent in re.split(r'[.!?]+', best_passage):
                if any(w in sent.lower() for w in q_words if len(w) > 3):
                    answer = sent.strip()
                    break
            if not answer:
                answer = best_passage[:200]
        result = QAResult(
            question_id=question_id, question=question,
            answer=answer, passage=best_passage[:200],
            confidence=round(best_score, 3)
        )
        self._results.append(result)
        self._save()
        return result

    def to_dict(self) -> dict:
        return {"passage_count": len(self._passages), "qa_count": len(self._results)}

    def get_stats(self) -> dict:
        avg_conf = sum(r.confidence for r in self._results) / len(self._results) if self._results else 0
        answered = sum(1 for r in self._results if r.answer)
        return {"passages": len(self._passages), "qa": len(self._results), "answered": answered, "avg_conf": round(avg_conf, 3)}

__all__ = ["NLPQASystem", "QAResult"]
