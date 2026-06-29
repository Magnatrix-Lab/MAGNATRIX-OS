"""NLP Text Summarizer -- Extractive and abstractive summarization."""
from dataclasses import dataclass
from pathlib import Path
import json, re

@dataclass
class Summary:
    summary_id: str = ""
    original_length: int = 0
    summary_length: int = 0
    compression_ratio: float = 0.0
    method: str = ""  # extractive | abstractive
    text: str = ""

class NLPTextSummarizer:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._summaries: list[Summary] = []
        self._persist_path = self.root / "nlp_summarizer.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._summaries = [Summary(**s) for s in data.get("summaries", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "summaries": [s.__dict__ for s in self._summaries]
        }, indent=2))

    def extractive(self, text: str, num_sentences: int = 3) -> Summary:
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        # Score sentences by word frequency
        word_freq = {}
        for s in sentences:
            for w in s.lower().split():
                w = re.sub(r'[^\w]', '', w)
                if w:
                    word_freq[w] = word_freq.get(w, 0) + 1
        scores = []
        for s in sentences:
            score = sum(word_freq.get(re.sub(r'[^\w]', '', w.lower()), 0) for w in s.split())
            scores.append(score)
        ranked = sorted(zip(sentences, scores), key=lambda x: x[1], reverse=True)
        top = [s for s, _ in ranked[:num_sentences]]
        summary_text = ". ".join(top) + "."
        summary = Summary(
            summary_id=f"sum_{len(self._summaries)}",
            original_length=len(text),
            summary_length=len(summary_text),
            compression_ratio=round(len(summary_text) / len(text), 2) if text else 0,
            method="extractive", text=summary_text
        )
        self._summaries.append(summary)
        self._save()
        return summary

    def abstractive(self, text: str) -> Summary:
        # Simplified abstractive: take first sentence, add last sentence
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if len(sentences) >= 2:
            summary_text = sentences[0] + ". " + sentences[-1] + "."
        elif sentences:
            summary_text = sentences[0] + "."
        else:
            summary_text = ""
        summary = Summary(
            summary_id=f"sum_{len(self._summaries)}",
            original_length=len(text),
            summary_length=len(summary_text),
            compression_ratio=round(len(summary_text) / len(text), 2) if text else 0,
            method="abstractive", text=summary_text
        )
        self._summaries.append(summary)
        self._save()
        return summary

    def to_dict(self) -> dict:
        return {"summary_count": len(self._summaries)}

    def get_stats(self) -> dict:
        by_method = {}
        for s in self._summaries:
            by_method[s.method] = by_method.get(s.method, 0) + 1
        avg_ratio = sum(s.compression_ratio for s in self._summaries) / len(self._summaries) if self._summaries else 0
        return {"summaries": len(self._summaries), "by_method": by_method, "avg_compression": round(avg_ratio, 2)}

__all__ = ["NLPTextSummarizer", "Summary"]
