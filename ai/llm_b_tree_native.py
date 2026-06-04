"""B-Tree - Self-balancing tree for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class BTreeNode:
    keys: List[int] = field(default_factory=list)
    children: List[Optional["BTreeNode"]] = field(default_factory=list)
    is_leaf: bool = True

@dataclass
class BTree:
    degree: int = 2
    root: Optional[BTreeNode] = None

    def insert(self, key: int) -> None:
        if self.root is None: self.root = BTreeNode(); self.root.keys.append(key); return
        if len(self.root.keys) == 2*self.degree - 1:
            new_root = BTreeNode(); new_root.is_leaf = False; new_root.children.append(self.root); self.root = new_root
        self._insert_non_full(self.root, key)

    def _insert_non_full(self, node: BTreeNode, key: int) -> None:
        i = len(node.keys) - 1
        if node.is_leaf:
            while i >= 0 and key < node.keys[i]: i -= 1
            node.keys.insert(i+1, key)
        else:
            while i >= 0 and key < node.keys[i]: i -= 1
            i += 1
            if len(node.children[i].keys) == 2*self.degree - 1:
                self._split_child(node, i)
                if key > node.keys[i]: i += 1
            self._insert_non_full(node.children[i], key)

    def _split_child(self, parent: BTreeNode, i: int) -> None:
        y = parent.children[i]; z = BTreeNode(); z.is_leaf = y.is_leaf; mid = self.degree - 1
        z.keys = y.keys[mid+1:]; y.keys = y.keys[:mid+1]
        if not y.is_leaf: z.children = y.children[mid+1:]; y.children = y.children[:mid+1]
        parent.keys.insert(i, y.keys.pop())
        parent.children.insert(i+1, z)

    def search(self, key: int) -> bool:
        return self._search(self.root, key)

    def _search(self, node: Optional[BTreeNode], key: int) -> bool:
        if node is None: return False
        i = 0
        while i < len(node.keys) and key > node.keys[i]: i += 1
        if i < len(node.keys) and key == node.keys[i]: return True
        if node.is_leaf: return False
        return self._search(node.children[i], key)

    def stats(self) -> dict:
        return {"degree": self.degree, "root_keys": len(self.root.keys) if self.root else 0}

def run():
    bt = BTree(2)
    for k in [10,20,5,6,12,30,7,17]: bt.insert(k)
    print("Search 12:", bt.search(12))
    print("Search 100:", bt.search(100))
    print("Stats:", bt.stats())

if __name__ == "__main__": run()
