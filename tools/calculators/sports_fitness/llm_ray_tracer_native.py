"""Ray Tracer — 3D rendering, ray casting, shading, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

@dataclass
class Vec3:
    x: float
    y: float
    z: float

    def __add__(self, o): return Vec3(self.x+o.x, self.y+o.y, self.z+o.z)
    def __sub__(self, o): return Vec3(self.x-o.x, self.y-o.y, self.z-o.z)
    def __mul__(self, s): return Vec3(self.x*s, self.y*s, self.z*s)
    def dot(self, o): return self.x*o.x + self.y*o.y + self.z*o.z
    def length(self): return math.sqrt(self.dot(self))
    def normalize(self):
        l = self.length()
        return Vec3(self.x/l, self.y/l, self.z/l) if l else Vec3(0,0,0)

@dataclass
class Sphere:
    center: Vec3
    radius: float
    color: Vec3

class RayTracer:
    def __init__(self, width: int = 64, height: int = 64):
        self.width = width
        self.height = height
        self.objects: List[Sphere] = []
        self.light = Vec3(0, 5, -5)
        self.camera = Vec3(0, 0, -5)

    def add_sphere(self, sphere: Sphere):
        self.objects.append(sphere)

    def _intersect(self, ray_origin: Vec3, ray_dir: Vec3, sphere: Sphere) -> Optional[float]:
        oc = ray_origin - sphere.center
        a = ray_dir.dot(ray_dir)
        b = 2.0 * oc.dot(ray_dir)
        c = oc.dot(oc) - sphere.radius ** 2
        discriminant = b ** 2 - 4 * a * c
        if discriminant < 0:
            return None
        t = (-b - math.sqrt(discriminant)) / (2 * a)
        return t if t > 0 else None

    def _trace(self, ray_origin: Vec3, ray_dir: Vec3) -> Vec3:
        closest = None
        closest_obj = None
        for obj in self.objects:
            t = self._intersect(ray_origin, ray_dir, obj)
            if t is not None and (closest is None or t < closest):
                closest = t
                closest_obj = obj
        if closest_obj is None:
            return Vec3(0, 0, 0)
        hit = ray_origin + ray_dir * closest
        normal = (hit - closest_obj.center).normalize()
        light_dir = (self.light - hit).normalize()
        intensity = max(0, normal.dot(light_dir))
        return closest_obj.color * intensity

    def render(self) -> List[List[Vec3]]:
        image = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                u = (x / self.width - 0.5) * 2
                v = (y / self.height - 0.5) * 2
                ray_dir = Vec3(u, v, 1).normalize()
                color = self._trace(self.camera, ray_dir)
                row.append(color)
            image.append(row)
        return image

    def stats(self) -> Dict:
        return {"width": self.width, "height": self.height, "objects": len(self.objects)}

def run():
    rt = RayTracer(32, 32)
    rt.add_sphere(Sphere(Vec3(0, 0, 2), 1.0, Vec3(1, 0, 0)))
    rt.add_sphere(Sphere(Vec3(-1.5, 0, 3), 0.5, Vec3(0, 1, 0)))
    img = rt.render()
    print("Rendered", len(img), "x", len(img[0]))
    print(rt.stats())

if __name__ == "__main__":
    run()
