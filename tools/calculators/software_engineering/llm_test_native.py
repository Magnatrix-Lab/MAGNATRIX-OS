"""Test module."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class Test:
    x: int = 0
    def stats(self):
        return {'x': self.x}

def run():
    t = Test(5)
    print(t.stats())

if __name__ == '__main__':
    run()
