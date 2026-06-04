"""L-System Generator — fractal grammar, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

@dataclass
class TurtleState:
    x: float = 0.0
    y: float = 0.0
    angle: float = 0.0
    pen_down: bool = True

class LSystem:
    def __init__(self, axiom: str, angle: float = 90.0, step: float = 1.0):
        self.axiom = axiom
        self.angle = math.radians(angle)
        self.step = step
        self.rules: Dict[str, str] = {}
        self.current = axiom
        self.generation = 0

    def add_rule(self, symbol: str, replacement: str):
        self.rules[symbol] = replacement

    def iterate(self, times: int = 1):
        for _ in range(times):
            result = ""
            for c in self.current:
                result += self.rules.get(c, c)
            self.current = result
            self.generation += 1

    def generate_points(self) -> List[Tuple[float, float, float, float]]:
        state = TurtleState()
        stack: List[TurtleState] = []
        lines = []
        for c in self.current:
            if c == "F" or c == "G":
                new_x = state.x + self.step * math.cos(state.angle)
                new_y = state.y + self.step * math.sin(state.angle)
                if state.pen_down:
                    lines.append((state.x, state.y, new_x, new_y))
                state.x, state.y = new_x, new_y
            elif c == "f":
                state.x += self.step * math.cos(state.angle)
                state.y += self.step * math.sin(state.angle)
            elif c == "+":
                state.angle += self.angle
            elif c == "-":
                state.angle -= self.angle
            elif c == "[":
                stack.append(TurtleState(state.x, state.y, state.angle, state.pen_down))
            elif c == "]":
                if stack:
                    state = stack.pop()
        return lines

    def stats(self) -> Dict:
        return {"axiom": self.axiom, "generation": self.generation, "length": len(self.current), "rules": len(self.rules)}

def run():
    lsys = LSystem("F", angle=60, step=1)
    lsys.add_rule("F", "F+F--F+F")
    lsys.iterate(3)
    points = lsys.generate_points()
    print("String length:", len(lsys.current))
    print("Lines:", len(points))
    print(lsys.stats())

if __name__ == "__main__":
    run()
