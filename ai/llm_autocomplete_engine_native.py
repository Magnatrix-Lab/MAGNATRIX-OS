"""LLM Autocomplete Engine — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from enum import Enum, auto

class AutocompleteEngine:
    def __init__(self) -> None:
        self._trie: Dict = {}
        self._counts: Dict[str, int] = {}

    def add_term(self, term: str, count: int = 1) -> None:
        self._counts[term] = self._counts.get(term, 0) + count
        node = self._trie
        for char in term.lower():
            if char not in node:
                node[char] = {}
            node = node[char]
        node["_end"] = True
        node["_term"] = term

    def _collect(self, node: Dict, prefix: str) -> List[tuple]:
        results = []
        if node.get("_end"):
            term = node.get("_term", prefix)
            results.append((self._counts.get(term, 0), term))
        for char, child in node.items():
            if char.startswith("_"):
                continue
            results.extend(self._collect(child, prefix + char))
        return results

    def suggest(self, prefix: str, top_k: int = 5) -> List[str]:
        node = self._trie
        for char in prefix.lower():
            if char not in node:
                return []
            node = node[char]
        results = self._collect(node, prefix.lower())
        results.sort(key=lambda x: x[0], reverse=True)
        return [term for _, term in results[:top_k]]

    def add_corpus(self, texts: List[str]) -> None:
        for text in texts:
            for word in text.split():
                self.add_term(word.strip().lower())

    def get_stats(self) -> Dict[str, Any]:
        return {"terms": len(self._counts), "unique_prefixes": len(self._trie)}

def run() -> None:
    print("Autocomplete Engine test")
    e = AutocompleteEngine()
    terms = ["machine", "machine learning", "machine vision", "machinery", "macro", "micro", "microsoft", "microphone", "microwave"]
    for t in terms:
        e.add_term(t, 1)
    print("  'mac': " + str(e.suggest("mac", 3)))
    print("  'mic': " + str(e.suggest("mic", 3)))
    print("  'mach': " + str(e.suggest("mach", 3)))
    print("  Stats: " + str(e.get_stats()))
    print("Autocomplete Engine test complete.")

if __name__ == "__main__":
    run()
