"""
code_reuse_detector_native.py
MAGNATRIX-OS — Code Reuse Detector

Inspired by Ponytail: "Reuse before you write." Detect existing code patterns before generating new code. Pure stdlib.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class ReuseCandidate:
    candidate_id: str
    pattern: str
    source_file: str
    similarity: float
    match_type: str
    line_range: Optional[tuple] = None


class CodeReuseDetector:
    """Detect existing code patterns before generating new code."""

    def __init__(self, cache_dir: str = "./reuse_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.patterns: Dict[str, str] = {}
        self.candidates: List[ReuseCandidate] = []
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "patterns.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    self.patterns = json.load(f)
            except Exception:
                pass
        file2 = self.cache_dir / "candidates.json"
        if file2.exists():
            try:
                with open(file2, "r", encoding="utf-8") as f:
                    self.candidates = [ReuseCandidate(**c) for c in json.load(f)]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "patterns.json", "w", encoding="utf-8") as f:
            json.dump(self.patterns, f, indent=2)
        with open(self.cache_dir / "candidates.json", "w", encoding="utf-8") as f:
            json.dump([asdict(c) for c in self.candidates], f, indent=2)

    def index_file(self, file_path: str, content: str) -> None:
        """Index a source file for pattern matching."""
        self.patterns[file_path] = content
        self._save()

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization for similarity."""
        return re.findall(r'[a-zA-Z_]+', text.lower())

    def _jaccard(self, a: List[str], b: List[str]) -> float:
        if not a or not b:
            return 0.0
        sa, sb = set(a), set(b)
        inter = len(sa & sb)
        union = len(sa | sb)
        return inter / union if union > 0 else 0.0

    def find_reuse(self, query: str, threshold: float = 0.5) -> List[ReuseCandidate]:
        """Find existing code patterns similar to the query."""
        query_tokens = self._tokenize(query)
        results = []
        for path, content in self.patterns.items():
            content_tokens = self._tokenize(content)
            sim = self._jaccard(query_tokens, content_tokens)
            if sim >= threshold:
                results.append(ReuseCandidate(
                    candidate_id=f"{path}_{len(results)}", pattern=content[:200],
                    source_file=path, similarity=round(sim, 4), match_type="jaccard",
                ))
        results.sort(key=lambda x: x.similarity, reverse=True)
        self.candidates = results[:20]
        self._save()
        return results[:10]

    def should_reuse(self, query: str, threshold: float = 0.7) -> bool:
        results = self.find_reuse(query, threshold)
        return len(results) > 0

    def get_stats(self) -> Dict[str, Any]:
        return {"indexed_files": len(self.patterns), "candidates": len(self.candidates)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["CodeReuseDetector", "ReuseCandidate"]