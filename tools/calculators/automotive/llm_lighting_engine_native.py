"""Lighting Engine — Phong, diffuse, ambient, specular, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

@dataclass
class Vec3:
    x: float; y: float; z: float
    def __add__(self, o): return Vec3(self.x+o.x, self.y+o.y, self.z+o.z)
    def __sub__(self, o): return Vec3(self.x-o.x, self.y-o.y, self.z-o.z)
    def __mul__(self, s): return Vec3(self.x*s, self.y*s, self.z*s)
    def dot(self, o): return self.x*o.x + self.y*o.y + self.z*o.z
    def length(self): return math.sqrt(self.dot(self))
    def normalize(self):
        l = self.length()
        return Vec3(self.x/l, self.y/l, self.z/l) if l else Vec3(0,0,0)

@dataclass
class Light:
    position: Vec3
    color: Vec3
    intensity: float

@dataclass
class Material:
    ambient: Vec3
    diffuse: Vec3
    specular: Vec3
    shininess: float

class LightingEngine:
    def __init__(self):
        self.lights: List[Light] = []
        self.ambient = Vec3(0.1, 0.1, 0.1)

    def add_light(self, light: Light):
        self.lights.append(light)

    def phong(self, position: Vec3, normal: Vec3, view_dir: Vec3, material: Material) -> Vec3:
        normal = normal.normalize()
        result = material.ambient * self.ambient.x
        for light in self.lights:
            light_dir = (light.position - position).normalize()
            diff = max(0, normal.dot(light_dir))
            diffuse = material.diffuse * diff * light.color * light.intensity
            reflect = Vec3(2*normal.dot(light_dir)*normal.x - light_dir.x, 2*normal.dot(light_dir)*normal.y - light_dir.y, 2*normal.dot(light_dir)*normal.z - light_dir.z).normalize()
            spec = max(0, reflect.dot(view_dir.normalize())) ** material.shininess
            specular = material.specular * spec * light.color * light.intensity
            result = Vec3(result.x + diffuse.x + specular.x, result.y + diffuse.y + specular.y, result.z + diffuse.z + specular.z)
        return result

    def stats(self) -> Dict:
        return {"lights": len(self.lights), "ambient": (self.ambient.x, self.ambient.y, self.ambient.z)}

def run():
    le = LightingEngine()
    le.add_light(Light(Vec3(5, 5, 5), Vec3(1, 1, 1), 1.0))
    mat = Material(Vec3(0.1, 0, 0), Vec3(1, 0, 0), Vec3(1, 1, 1), 32)
    color = le.phong(Vec3(0, 0, 0), Vec3(0, 1, 0), Vec3(0, 0, -1), mat)
    print(f"Color: ({color.x:.2f}, {color.y:.2f}, {color.z:.2f})")
    print(le.stats())

if __name__ == "__main__":
    run()
