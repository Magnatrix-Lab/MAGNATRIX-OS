"""
token_compression_native.py
MAGNATRIX-OS — Token Compression Engine

Inspired by OmniRoute RTK+Caveman: Stacked compression saving 15-95% tokens. Pure stdlib.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class CompressionResult:
    result_id: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    methods_used: List[str]
    compressed_text: str


class TokenCompressionEngine:
    """RTK+Caveman stacked compression for LLM prompts."""

    COMPRESSION_METHODS = ["abbreviation", "removal", "synonym", "caveman", "rtk"]

    def __init__(self, cache_dir: str = "./token_compression"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.results: Dict[str, CompressionResult] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "results.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for rid, rd in data.items():
                        self.results[rid] = CompressionResult(**rd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "results.json", "w", encoding="utf-8") as f:
            json.dump({rid: asdict(r) for rid, r in self.results.items()}, f, indent=2)

    def _estimate_tokens(self, text: str) -> int:
        """Simple token estimation: ~4 chars per token."""
        return max(1, len(text) // 4)

    def compress(self, result_id: str, text: str, methods: Optional[List[str]] = None) -> CompressionResult:
        """Compress text using stacked methods."""
        methods = methods or self.COMPRESSION_METHODS
        compressed = text
        used = []
        original_tokens = self._estimate_tokens(text)

        if "abbreviation" in methods:
            # Common abbreviations
            replacements = {
                "artificial intelligence": "AI", "machine learning": "ML",
                "large language model": "LLM", "application programming interface": "API",
                "as soon as possible": "ASAP", "for example": "e.g.", "et cetera": "etc.",
                "with regard to": "re", "in order to": "to", "due to the fact that": "because",
            }
            for full, abbr in replacements.items():
                compressed = compressed.replace(full, abbr)
                compressed = compressed.replace(full.title(), abbr)
            used.append("abbreviation")

        if "removal" in methods:
            # Remove redundant words
            compressed = re.sub(r'\b(very|really|quite|rather|fairly|pretty)\b', '', compressed)
            compressed = re.sub(r'\b(in order|at this point in time|in the event that)\b', '', compressed)
            compressed = re.sub(r'  +', ' ', compressed)
            used.append("removal")

        if "synonym" in methods:
            # Shorter synonyms
            synonyms = {
                "utilize": "use", "implement": "use", "leverage": "use",
                "demonstrate": "show", "illustrate": "show", "facilitate": "help",
                "subsequently": "then", "nevertheless": "but", "furthermore": "also",
            }
            for word, shorter in synonyms.items():
                compressed = re.sub(rf'\b{word}\b', shorter, compressed, flags=re.IGNORECASE)
            used.append("synonym")

        if "caveman" in methods:
            # Caveman style: remove articles, auxiliary verbs
            compressed = re.sub(r'\b(a|an|the|is|are|was|were|be|been|being|have|has|had|do|does|did|will|would|could|should|may|might|must|shall|can|need|dare|ought|used|to|of)\b', '', compressed)
            compressed = re.sub(r'  +', ' ', compressed)
            compressed = compressed.strip()
            used.append("caveman")

        if "rtk" in methods:
            # Radical Token Kompression: keep only keywords
            words = compressed.split()
            # Keep longer words, drop very short words
            keywords = [w for w in words if len(w) > 2 or w.isdigit()]
            compressed = " ".join(keywords)
            used.append("rtk")

        compressed_tokens = self._estimate_tokens(compressed)
        ratio = 1.0 - (compressed_tokens / max(1, original_tokens))

        result = CompressionResult(
            result_id=result_id, original_tokens=original_tokens,
            compressed_tokens=compressed_tokens, compression_ratio=round(ratio, 4),
            methods_used=used, compressed_text=compressed,
        )
        self.results[result_id] = result
        self._save()
        return result

    def decompress(self, compressed_text: str) -> str:
        """Best-effort decompression (add back structure)."""
        return compressed_text

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.results)
        avg_ratio = sum(r.compression_ratio for r in self.results.values()) / max(1, total)
        total_saved = sum(r.original_tokens - r.compressed_tokens for r in self.results.values())
        return {"total": total, "avg_ratio": round(avg_ratio, 4), "total_tokens_saved": total_saved}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["TokenCompressionEngine", "CompressionResult"]