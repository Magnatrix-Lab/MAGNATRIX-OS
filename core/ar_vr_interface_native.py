#!/usr/bin/env python3
"""AR/VR Interface for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

@dataclass
class Vector3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    def distance(self, other: 'Vector3') -> float:
        return math.sqrt((self.x-other.x)**2 + (self.y-other.y)**2 + (self.z-other.z)**2)
    def to_dict(self): return {"x": self.x, "y": self.y, "z": self.z}

@dataclass
class SceneNode:
    node_id: str
    position: Vector3 = field(default_factory=Vector3)
    rotation: Vector3 = field(default_factory=Vector3)
    scale: Vector3 = field(default_factory=lambda: Vector3(1,1,1))
    children: List[str] = field(default_factory=list)
    def to_dict(self): return {"node_id": self.node_id, "position": self.position.to_dict(), "rotation": self.rotation.to_dict(), "scale": self.scale.to_dict(), "children": self.children}

class SceneGraph:
    def __init__(self):
        self.nodes: Dict[str, SceneNode] = {}
    def add_node(self, node: SceneNode):
        self.nodes[node.node_id] = node
    def get_node(self, node_id: str) -> Optional[SceneNode]:
        return self.nodes.get(node_id)
    def to_dict(self): return {"nodes": len(self.nodes)}

class GestureMapper:
    def __init__(self):
        self.gestures: Dict[str, List[Vector3]] = {}
    def register(self, name: str, points: List[Tuple[float,float,float]]):
        self.gestures[name] = [Vector3(*p) for p in points]
    def recognize(self, points: List[Tuple[float,float,float]]) -> Optional[str]:
        if not points: return None
        input_vec = [Vector3(*p) for p in points]
        best_name = None
        best_score = float('inf')
        for name, template in self.gestures.items():
            if len(template) != len(input_vec): continue
            score = sum(t.distance(i) for t,i in zip(template, input_vec))
            if score < best_score:
                best_score = score
                best_name = name
        return best_name
    def to_dict(self): return {"gestures": len(self.gestures)}

class ARVRInterface:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.scene = SceneGraph()
        self.gestures = GestureMapper()
    def add_object(self, obj_id: str, pos: Tuple[float,float,float], rot: Tuple[float,float,float] = (0,0,0)):
        self.scene.add_node(SceneNode(obj_id, Vector3(*pos), Vector3(*rot)))
    def to_dict(self):
        return {"scene": self.scene.to_dict(), "gestures": self.gestures.to_dict()}
