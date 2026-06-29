
"""
graph_community_detector_native.py
MAGNATRIX-OS — Graph Community Detector

Detect communities in knowledge graphs using connected components. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, field


@dataclass
class Community:
    community_id: str
    members: List[str]
    size: int
    density: float
    internal_edges: int
    external_edges: int


class GraphCommunityDetector:
    """Detect communities in knowledge graphs using connected components."""

    def __init__(self, cache_dir: str = "./graph_communities"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.communities: Dict[str, Community] = {}
        self._load()

    def _load(self) -> None:
        f = self.cache_dir / "communities.json"
        if f.exists():
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                    for cid, cd in data.items():
                        self.communities[cid] = Community(**cd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "communities.json", "w", encoding="utf-8") as f:
            json.dump({cid: {"community_id": c.community_id, "members": c.members, "size": c.size, "density": c.density, "internal_edges": c.internal_edges, "external_edges": c.external_edges} for cid, c in self.communities.items()}, f, indent=2)

    def detect(self, edges) -> Dict[str, Community]:
        adj = {}
        for e in edges:
            adj.setdefault(e.source, []).append(e.target)
            adj.setdefault(e.target, []).append(e.source)
        visited = set()
        communities = {}
        comm_id = 0
        for node in adj:
            if node in visited:
                continue
            stack = [node]
            members = []
            while stack:
                current = stack.pop()
                if current not in visited:
                    visited.add(current)
                    members.append(current)
                    for neighbor in adj.get(current, []):
                        if neighbor not in visited:
                            stack.append(neighbor)
            member_set = set(members)
            internal = sum(1 for e in edges if e.source in member_set and e.target in member_set)
            possible = len(members) * (len(members) - 1) / 2 if len(members) > 1 else 1
            density = internal / max(1, possible)
            external = sum(1 for e in edges if (e.source in member_set) != (e.target in member_set))
            communities[f"community_{comm_id}"] = Community(
                community_id=f"community_{comm_id}", members=members, size=len(members),
                density=round(density, 4), internal_edges=internal, external_edges=external,
            )
            comm_id += 1
        self.communities = communities
        self._save()
        return communities

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.communities)
        avg_size = sum(c.size for c in self.communities.values()) / max(1, total)
        avg_density = sum(c.density for c in self.communities.values()) / max(1, total)
        return {"communities": total, "avg_size": round(avg_size, 2), "avg_density": round(avg_density, 4)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["GraphCommunityDetector", "Community"]
