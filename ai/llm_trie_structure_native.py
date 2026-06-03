"""Trie Structure - Prefix tree for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class TrieNode:
    children: Dict[str, "TrieNode"] = field(default_factory=dict)
    is_end: bool = False

@dataclass
class TrieStructure:
    root: TrieNode = field(default_factory=TrieNode)

    def insert(self, word: str) -> None:
        node = self.root
        for c in word:
            if c not in node.children: node.children[c] = TrieNode()
            node = node.children[c]
        node.is_end = True

    def search(self, word: str) -> bool:
        node = self.root
        for c in word:
            if c not in node.children: return False
            node = node.children[c]
        return node.is_end

    def starts_with(self, prefix: str) -> bool:
        node = self.root
        for c in prefix:
            if c not in node.children: return False
            node = node.children[c]
        return True

    def stats(self) -> dict:
        return {"root_children": len(self.root.children)}

def run():
    trie = TrieStructure()
    for w in ["apple", "app", "banana"]: trie.insert(w)
    print("Search app:", trie.search("app"))
    print("Starts with ap:", trie.starts_with("ap"))
    print("Stats:", trie.stats())

if __name__ == "__main__": run()
