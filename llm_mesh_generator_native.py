"""Mesh Generator — cube, sphere, plane, OBJ export, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

@dataclass
class Vertex:
    x: float; y: float; z: float

@dataclass
class Face:
    indices: List[int]

class MeshGenerator:
    def __init__(self):
        self.vertices: List[Vertex] = []
        self.faces: List[Face] = []

    def add_vertex(self, v: Vertex) -> int:
        self.vertices.append(v)
        return len(self.vertices) - 1

    def add_face(self, indices: List[int]):
        self.faces.append(Face(indices))

    def generate_cube(self, size: float = 1.0) -> "MeshGenerator":
        s = size / 2
        for x in [-s, s]:
            for y in [-s, s]:
                for z in [-s, s]:
                    self.add_vertex(Vertex(x, y, z))
        self.faces = [
            Face([0, 1, 3, 2]), Face([4, 6, 7, 5]),
            Face([0, 2, 6, 4]), Face([1, 5, 7, 3]),
            Face([0, 4, 5, 1]), Face([2, 3, 7, 6]),
        ]
        return self

    def generate_sphere(self, radius: float = 1.0, segments: int = 16) -> "MeshGenerator":
        for lat in range(segments + 1):
            theta = math.pi * lat / segments
            for lon in range(segments + 1):
                phi = 2 * math.pi * lon / segments
                x = radius * math.sin(theta) * math.cos(phi)
                y = radius * math.cos(theta)
                z = radius * math.sin(theta) * math.sin(phi)
                self.add_vertex(Vertex(x, y, z))
        for lat in range(segments):
            for lon in range(segments):
                first = lat * (segments + 1) + lon
                second = first + segments + 1
                self.add_face([first, second, first + 1])
                self.add_face([second, second + 1, first + 1])
        return self

    def generate_plane(self, width: float = 1.0, depth: float = 1.0) -> "MeshGenerator":
        w = width / 2
        d = depth / 2
        self.add_vertex(Vertex(-w, 0, -d))
        self.add_vertex(Vertex(w, 0, -d))
        self.add_vertex(Vertex(-w, 0, d))
        self.add_vertex(Vertex(w, 0, d))
        self.add_face([0, 2, 3])
        self.add_face([0, 3, 1])
        return self

    def to_obj(self) -> str:
        lines = []
        for v in self.vertices:
            lines.append(f"v {v.x} {v.y} {v.z}")
        for f in self.faces:
            lines.append(f"f {' '.join(str(i+1) for i in f.indices)}")
        return '\n'.join(lines)

    def stats(self) -> Dict:
        return {"vertices": len(self.vertices), "faces": len(self.faces)}

def run():
    mesh = MeshGenerator().generate_sphere(1.0, 8)
    print(mesh.stats())
    print(mesh.to_obj()[:100])

if __name__ == "__main__":
    run()
