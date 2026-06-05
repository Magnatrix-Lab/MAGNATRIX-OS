"""Pool Allocator — fixed-size blocks, reuse, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum, auto

class PoolAllocator:
    def __init__(self, block_size: int = 64, pool_size: int = 1024):
        self.block_size = block_size
        self.pool_size = pool_size
        self.num_blocks = pool_size // block_size
        self.free_list: List[int] = list(range(self.num_blocks))
        self.allocated: Dict[int, int] = {}
        self.alloc_count = 0

    def allocate(self) -> Optional[int]:
        if not self.free_list:
            return None
        idx = self.free_list.pop()
        self.alloc_count += 1
        self.allocated[self.alloc_count] = idx
        return self.alloc_count

    def free(self, handle: int) -> bool:
        idx = self.allocated.pop(handle, None)
        if idx is None:
            return False
        self.free_list.append(idx)
        return True

    def get_address(self, handle: int) -> int:
        idx = self.allocated.get(handle)
        return idx * self.block_size if idx is not None else -1

    def stats(self) -> Dict:
        return {"block_size": self.block_size, "total_blocks": self.num_blocks, "free": len(self.free_list), "allocated": len(self.allocated)}

def run():
    pool = PoolAllocator(64, 256)
    h1 = pool.allocate()
    h2 = pool.allocate()
    print("Addresses:", pool.get_address(h1), pool.get_address(h2))
    pool.free(h1)
    print(pool.stats())

if __name__ == "__main__":
    run()
