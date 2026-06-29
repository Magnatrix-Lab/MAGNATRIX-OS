"""
skill_tree_builder_native.py
MAGNATRIX-OS — Skill Tree Builder

Inspired by AgentSkillOS: Hierarchical skill tree for organizing skills by capability. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class SkillNode:
    node_id: str
    name: str
    description: str
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    depth: int = 0


class SkillTreeBuilder:
    """Hierarchical skill tree for organizing 200,000+ skills by capability."""

    def __init__(self, tree_dir: str = "./skill_tree"):
        self.tree_dir = Path(tree_dir)
        self.tree_dir.mkdir(exist_ok=True)
        self.nodes: Dict[str, SkillNode] = {}
        self._load()
        self._init_root()

    def _init_root(self) -> None:
        if "root" not in self.nodes:
            self.nodes["root"] = SkillNode(
                node_id="root", name="Root", description="All skills",
                parent=None, children=[], skills=[], depth=0,
            )

    def _load(self) -> None:
        file = self.tree_dir / "nodes.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for nid, nd in data.items():
                        self.nodes[nid] = SkillNode(**nd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.tree_dir / "nodes.json", "w", encoding="utf-8") as f:
            json.dump({nid: asdict(n) for nid, n in self.nodes.items()}, f, indent=2)

    def add_node(self, node_id: str, name: str, description: str, parent_id: str) -> SkillNode:
        parent = self.nodes.get(parent_id)
        depth = (parent.depth + 1) if parent else 0
        node = SkillNode(
            node_id=node_id, name=name, description=description,
            parent=parent_id, children=[], skills=[], depth=depth,
        )
        self.nodes[node_id] = node
        if parent:
            parent.children.append(node_id)
        self._save()
        return node

    def add_skill(self, node_id: str, skill_id: str) -> bool:
        node = self.nodes.get(node_id)
        if not node:
            return False
        node.skills.append(skill_id)
        self._save()
        return True

    def get_subtree(self, node_id: str) -> List[SkillNode]:
        """Get all nodes in a subtree."""
        node = self.nodes.get(node_id)
        if not node:
            return []
        result = [node]
        for child_id in node.children:
            result.extend(self.get_subtree(child_id))
        return result

    def get_path(self, node_id: str) -> List[str]:
        """Get path from root to node."""
        path = []
        current = self.nodes.get(node_id)
        while current:
            path.append(current.node_id)
            current = self.nodes.get(current.parent) if current.parent else None
        return list(reversed(path))

    def search(self, query: str) -> List[SkillNode]:
        q = query.lower()
        return [n for n in self.nodes.values() if q in n.name.lower() or q in n.description.lower()]

    def get_stats(self) -> Dict[str, Any]:
        total_skills = sum(len(n.skills) for n in self.nodes.values())
        depths = {}
        for n in self.nodes.values():
            depths[n.depth] = depths.get(n.depth, 0) + 1
        return {"total_nodes": len(self.nodes), "total_skills": total_skills, "depths": depths}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["SkillTreeBuilder", "SkillNode"]