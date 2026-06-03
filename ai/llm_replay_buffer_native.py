"""Replay Buffer - Experience replay for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Dict
import random

@dataclass
class ReplayBuffer:
    capacity: int = 100
    buffer: List[Tuple[int,int,float,int]] = field(default_factory=list)
    position: int = 0

    def push(self, state: int, action: int, reward: float, next_state: int) -> None:
        if len(self.buffer) < self.capacity:
            self.buffer.append((state, action, reward, next_state))
        else:
            self.buffer[self.position] = (state, action, reward, next_state)
        self.position = (self.position + 1) % self.capacity

    def sample(self, batch_size: int) -> List[Tuple[int,int,float,int]]:
        return random.sample(self.buffer, min(batch_size, len(self.buffer)))

    def stats(self) -> dict:
        return {"capacity": self.capacity, "size": len(self.buffer)}

def run():
    rb = ReplayBuffer(10)
    for i in range(15):
        rb.push(i, i%2, float(i), i+1)
    print("Sample:", rb.sample(3))
    print("Stats:", rb.stats())

if __name__ == "__main__": run()
