"""DB BTree Index -- B-tree index implementation, range queries, insertion, deletion."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class BTreeNode:
    node_id: str = ""
    keys: list = None
    values: list = None
    children: list = None
    leaf: bool = True
    parent: str = ""

    def __post_init__(self):
        if self.keys is None:
            self.keys = []
        if self.values is None:
            self.values = []
        if self.children is None:
            self.children = []

class DBBTreeIndex:
    def __init__(self, root: str = ".", order: int = 4):
        self.root = Path(root)
        self._order = order
        self._nodes: dict[str, BTreeNode] = {}
        self._root_id: str = ""
        self._persist_path = self.root / "db_btree.json"
        self._load()
        if not self._root_id:
            self._create_root()

    def _create_root(self) -> None:
        root = BTreeNode(node_id="root", leaf=True)
        self._nodes[root.node_id] = root
        self._root_id = root.node_id
        self._save()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._nodes = {k: BTreeNode(**v) for k, v in data.get("nodes", {}).items()}
            self._root_id = data.get("root_id", "")
            self._order = data.get("order", 4)

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "nodes": {k: v.__dict__ for k, v in self._nodes.items()},
            "root_id": self._root_id,
            "order": self._order
        }, indent=2))

    def _new_node(self, leaf: bool = True) -> BTreeNode:
        node = BTreeNode(node_id=f"node_{len(self._nodes)}", leaf=leaf)
        self._nodes[node.node_id] = node
        return node

    def insert(self, key, value) -> bool:
        root = self._nodes[self._root_id]
        if len(root.keys) >= (2 * self._order) - 1:
            new_root = self._new_node(leaf=False)
            new_root.children.append(self._root_id)
            self._split_child(new_root, 0)
            self._root_id = new_root.node_id
            root = new_root
        self._insert_non_full(root, key, value)
        self._save()
        return True

    def _insert_non_full(self, node: BTreeNode, key, value) -> None:
        i = len(node.keys) - 1
        if node.leaf:
            while i >= 0 and key < node.keys[i]:
                i -= 1
            node.keys.insert(i + 1, key)
            node.values.insert(i + 1, value)
        else:
            while i >= 0 and key < node.keys[i]:
                i -= 1
            i += 1
            child = self._nodes[node.children[i]]
            if len(child.keys) >= (2 * self._order) - 1:
                self._split_child(node, i)
                if key > node.keys[i]:
                    i += 1
            self._insert_non_full(self._nodes[node.children[i]], key, value)

    def _split_child(self, parent: BTreeNode, i: int) -> None:
        child = self._nodes[parent.children[i]]
        mid = self._order - 1
        new_node = self._new_node(leaf=child.leaf)
        new_node.keys = child.keys[mid + 1:]
        new_node.values = child.values[mid + 1:]
        child.keys = child.keys[:mid]
        child.values = child.values[:mid]
        if not child.leaf:
            new_node.children = child.children[mid + 1:]
            child.children = child.children[:mid + 1]
        parent.keys.insert(i, child.keys[mid])
        parent.values.insert(i, child.values[mid])
        parent.children.insert(i + 1, new_node.node_id)

    def search(self, key) -> any:
        node = self._nodes[self._root_id]
        while True:
            i = 0
            while i < len(node.keys) and key > node.keys[i]:
                i += 1
            if i < len(node.keys) and key == node.keys[i]:
                return node.values[i]
            if node.leaf:
                return None
            node = self._nodes[node.children[i]]

    def range_search(self, low, high) -> list[tuple]:
        results = []
        self._range_search_node(self._nodes[self._root_id], low, high, results)
        return results

    def _range_search_node(self, node: BTreeNode, low, high, results: list) -> None:
        i = 0
        while i < len(node.keys) and node.keys[i] < low:
            i += 1
        while i < len(node.keys) and node.keys[i] <= high:
            if not node.leaf and i < len(node.children):
                self._range_search_node(self._nodes[node.children[i]], low, high, results)
            results.append((node.keys[i], node.values[i]))
            i += 1
        if not node.leaf and i < len(node.children):
            self._range_search_node(self._nodes[node.children[i]], low, high, results)

    def to_dict(self) -> dict:
        return {"node_count": len(self._nodes), "root": self._root_id}

    def get_stats(self) -> dict:
        leaf_count = sum(1 for n in self._nodes.values() if n.leaf)
        total_keys = sum(len(n.keys) for n in self._nodes.values())
        return {"nodes": len(self._nodes), "leaf_nodes": leaf_count, "total_keys": total_keys}

__all__ = ["DBBTreeIndex", "BTreeNode"]
