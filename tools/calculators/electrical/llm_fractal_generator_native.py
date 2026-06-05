"""Fractal Generator — Mandelbrot, Julia, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

@dataclass
class Complex:
    real: float
    imag: float

    def __add__(self, other: "Complex") -> "Complex":
        return Complex(self.real + other.real, self.imag + other.imag)

    def __mul__(self, other: "Complex") -> "Complex":
        return Complex(self.real * other.real - self.imag * other.imag, self.real * other.imag + self.imag * other.real)

    def magnitude(self) -> float:
        return math.sqrt(self.real ** 2 + self.imag ** 2)

class FractalGenerator:
    def __init__(self, width: int = 64, height: int = 64):
        self.width = width
        self.height = height
        self.max_iter = 100
        self.escape_radius = 2.0

    def mandelbrot(self, x_min: float = -2.5, x_max: float = 1.0, y_min: float = -1.25, y_max: float = 1.25) -> List[List[int]]:
        result = []
        for py in range(self.height):
            row = []
            for px in range(self.width):
                x0 = x_min + (x_max - x_min) * px / self.width
                y0 = y_min + (y_max - y_min) * py / self.height
                c = Complex(x0, y0)
                z = Complex(0, 0)
                iteration = 0
                while z.magnitude() < self.escape_radius and iteration < self.max_iter:
                    z = z * z + c
                    iteration += 1
                row.append(iteration)
            result.append(row)
        return result

    def julia(self, c: Complex, x_min: float = -2, x_max: float = 2, y_min: float = -2, y_max: float = 2) -> List[List[int]]:
        result = []
        for py in range(self.height):
            row = []
            for px in range(self.width):
                x = x_min + (x_max - x_min) * px / self.width
                y = y_min + (y_max - y_min) * py / self.height
                z = Complex(x, y)
                iteration = 0
                while z.magnitude() < self.escape_radius and iteration < self.max_iter:
                    z = z * z + c
                    iteration += 1
                row.append(iteration)
            result.append(row)
        return result

    def stats(self) -> Dict:
        return {"width": self.width, "height": self.height, "max_iter": self.max_iter}

def run():
    gen = FractalGenerator(32, 32)
    mandelbrot = gen.mandelbrot()
    julia = gen.julia(Complex(-0.7, 0.27015))
    print("Mandelbrot center:", mandelbrot[16][16])
    print("Julia center:", julia[16][16])
    print(gen.stats())

if __name__ == "__main__":
    run()
