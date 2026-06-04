"""Radix Tree - Compressed trie for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class RadixNode:
    prefix: str = ""
    children: Dict[str, "RadixNode"] = field(default_factory=dict)
    is_end: bool = False

@dataclass
class RadixTree:
    root: RadixNode = field(default_factory=RadixNode)

    def insert(self, key: str) -> None:
        self._insert(self.root, key)

    def _insert(self, node: RadixNode, key: str) -> None:
        if not key: node.is_end = True; return
        for child_key, child in list(node.children.items()):
            common = 0
            while common < len(child_key) and common < len(key) and child_key[common] == key[common]: common += 1
            if common > 0:
                if common < len(child_key):
                    new_child = RadixNode(child_key[common:]); new_child.children = child.children; new_child.is_end = child.is_end
                    node.children[child_key[:common]] = RadixNode(child_key[:common], {child_key[common:]: new_child}, False)
                    del node.children[child_key]
                    child = node.children[child_key[:common]]
                if common == len(key): child.is_end = True
                else: self._insert(child, key[common:])
                return
        node.children[key] = RadixNode(key, {}, True)

    def search(self, key: str) -> bool:
        node = self.root
        while key:
            found = False
            for child_key, child in node.children.items():
                if key.startswith(child_key):
                    key = key[len(child_key):]; node = child; found = True; break
            if not found: return False
        return node.is_end

    def stats(self) -> dict:
        return {"children": len(self.root.children)}

def run():
    rt = RadixTree()
    rt.insert("romane"); rt.insert("romanus"); rt.insert("romulus"); rt.insert("rubens")
    print("Search romanus:", rt.search("romanus"))
    print("Search rubicon:", rt.search("rubicon"))
    print("Stats:", rt.stats())

if __name__ == "__main__": run()
