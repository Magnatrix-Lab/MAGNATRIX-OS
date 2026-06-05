"""Camera Controller — view, projection, frustum, native, stdlib only."""
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

class CameraController:
    def __init__(self, fov: float = 60.0, near: float = 0.1, far: float = 100.0, aspect: float = 1.0):
        self.fov = fov
        self.near = near
        self.far = far
        self.aspect = aspect
        self.position = Vec3(0, 0, 0)
        self.target = Vec3(0, 0, 1)
        self.up = Vec3(0, 1, 0)

    def look_at(self, eye: Vec3, target: Vec3, up: Vec3):
        self.position = eye
        self.target = target
        self.up = up

    def perspective_matrix(self) -> List[List[float]]:
        f = 1.0 / math.tan(math.radians(self.fov) / 2)
        nf = 1.0 / (self.near - self.far)
        return [
            [f / self.aspect, 0, 0, 0],
            [0, f, 0, 0],
            [0, 0, (self.far + self.near) * nf, -1],
            [0, 0, 2 * self.far * self.near * nf, 0],
        ]

    def view_matrix(self) -> List[List[float]]:
        z = (self.position - self.target)
        z_len = math.sqrt(z.dot(z))
        z = Vec3(z.x/z_len, z.y/z_len, z.z/z_len) if z_len else Vec3(0,0,0)
        x_vec = self.up
        x_cross = Vec3(x_vec.y*z.z - x_vec.z*z.y, x_vec.z*z.x - x_vec.x*z.z, x_vec.x*z.y - x_vec.y*z.x)
        x_len = math.sqrt(x_cross.dot(x_cross))
        x = Vec3(x_cross.x/x_len, x_cross.y/x_len, x_cross.z/x_len) if x_len else Vec3(0,0,0)
        y = Vec3(z.y*x.z - z.z*x.y, z.z*x.x - z.x*x.z, z.x*x.y - z.y*x.x)
        return [
            [x.x, x.y, x.z, -x.dot(self.position)],
            [y.x, y.y, y.z, -y.dot(self.position)],
            [z.x, z.y, z.z, -z.dot(self.position)],
            [0, 0, 0, 1],
        ]

    def frustum_planes(self) -> List[Dict]:
        return ["near", "far", "left", "right", "top", "bottom"]

    def move(self, delta: Vec3):
        self.position = self.position + delta

    def rotate(self, yaw: float, pitch: float):
        # Simplified
        pass

    def stats(self) -> Dict:
        return {"fov": self.fov, "near": self.near, "far": self.far, "position": (self.position.x, self.position.y, self.position.z)}

def run():
    cam = CameraController(60, 0.1, 100, 1.0)
    cam.look_at(Vec3(0, 0, -5), Vec3(0, 0, 0), Vec3(0, 1, 0))
    print(cam.perspective_matrix()[0])
    print(cam.view_matrix()[0])
    print(cam.stats())

if __name__ == "__main__":
    run()
