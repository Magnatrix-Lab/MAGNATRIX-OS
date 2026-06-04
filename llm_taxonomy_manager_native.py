"""Taxonomy Manager — hierarchical classification, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum, auto

class TaxonomyNode:
    def __init__(self, node_id: str, label: str, parent: Optional[str] = None):
        self.node_id = node_id
        self.label = label
        self.parent = parent
        self.children: List[str] = []
        self.items: List[str] = []
        self.depth: int = 0

class TaxonomyManager:
    def __init__(self, root_id: str = "root", root_label: str = "All"):
        self.nodes: Dict[str, TaxonomyNode] = {}
        self.root = TaxonomyNode(root_id, root_label)
        self.nodes[root_id] = self.root
        self.item_map: Dict[str, str] = {}

    def add_node(self, node_id: str, label: str, parent_id: str):
        node = TaxonomyNode(node_id, label, parent_id)
        self.nodes[node_id] = node
        if parent_id in self.nodes:
            self.nodes[parent_id].children.append(node_id)
            node.depth = self.nodes[parent_id].depth + 1

    def add_item(self, item_id: str, node_id: str):
        if node_id in self.nodes:
            self.nodes[node_id].items.append(item_id)
            self.item_map[item_id] = node_id

    def get_path(self, node_id: str) -> List[str]:
        path = []
        current = self.nodes.get(node_id)
        while current:
            path.append(current.node_id)
            current = self.nodes.get(current.parent) if current.parent else None
        return list(reversed(path))

    def get_descendants(self, node_id: str) -> List[str]:
        desc = []
        to_visit = [node_id]
        while to_visit:
            current = to_visit.pop()
            if current in self.nodes:
                for child in self.nodes[current].children:
                    desc.append(child)
                    to_visit.append(child)
        return desc

    def classify(self, item_id: str) -> Optional[str]:
        return self.item_map.get(item_id)

    def get_siblings(self, node_id: str) -> List[str]:
        node = self.nodes.get(node_id)
        if not node or not node.parent:
            return []
        return [c for c in self.nodes[node.parent].children if c != node_id]

    def stats(self) -> Dict:
        total_items = sum(len(n.items) for n in self.nodes.values())
        max_depth = max(n.depth for n in self.nodes.values()) if self.nodes else 0
        return {"nodes": len(self.nodes), "items": total_items, "max_depth": max_depth, "root_children": len(self.root.children)}

def run():
    tax = TaxonomyManager()
    tax.add_node("electronics", "Electronics", "root")
    tax.add_node("phones", "Phones", "electronics")
    tax.add_node("laptops", "Laptops", "electronics")
    tax.add_node("smartphones", "Smartphones", "phones")
    tax.add_item("iphone", "smartphones")
    tax.add_item("macbook", "laptops")
    print(tax.get_path("smartphones"))
    print(tax.get_descendants("electronics"))
    print(tax.stats())

if __name__ == "__main__":
    run()
