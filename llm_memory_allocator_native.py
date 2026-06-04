"""Memory Allocator — block allocation, fragmentation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto

@dataclass
class MemoryBlock:
    start: int
    size: int
    allocated: bool
    block_id: str

class MemoryAllocator:
    def __init__(self, total_size: int = 1024):
        self.total_size = total_size
        self.blocks: List[MemoryBlock] = [MemoryBlock(0, total_size, False, "free_0")]
        self.allocations: Dict[str, MemoryBlock] = {}
        self.alloc_count = 0

    def allocate(self, size: int) -> Optional[str]:
        for i, block in enumerate(self.blocks):
            if not block.allocated and block.size >= size:
                if block.size > size:
                    # Split
                    new_free = MemoryBlock(block.start + size, block.size - size, False, f"free_{i}")
                    self.blocks.insert(i + 1, new_free)
                block.size = size
                block.allocated = True
                block.block_id = f"alloc_{self.alloc_count}"
                self.alloc_count += 1
                self.allocations[block.block_id] = block
                return block.block_id
        return None

    def free(self, block_id: str) -> bool:
        block = self.allocations.pop(block_id, None)
        if not block:
            return False
        block.allocated = False
        block.block_id = f"free_{block.start}"
        # Merge adjacent free blocks
        self._merge_free()
        return True

    def _merge_free(self):
        self.blocks.sort(key=lambda b: b.start)
        i = 0
        while i < len(self.blocks) - 1:
            if not self.blocks[i].allocated and not self.blocks[i + 1].allocated:
                self.blocks[i].size += self.blocks[i + 1].size
                self.blocks.pop(i + 1)
            else:
                i += 1

    def fragmentation(self) -> float:
        free_blocks = [b for b in self.blocks if not b.allocated]
        if not free_blocks:
            return 0.0
        total_free = sum(b.size for b in free_blocks)
        largest_free = max(b.size for b in free_blocks)
        return 1 - largest_free / total_free if total_free else 0.0

    def stats(self) -> Dict:
        allocated = sum(b.size for b in self.blocks if b.allocated)
        return {"total": self.total_size, "allocated": allocated, "free": self.total_size - allocated, "fragmentation": self.fragmentation(), "blocks": len(self.blocks)}

def run():
    alloc = MemoryAllocator(1024)
    a1 = alloc.allocate(100)
    a2 = alloc.allocate(200)
    a3 = alloc.allocate(50)
    print(alloc.stats())
    alloc.free(a2)
    print("After free:", alloc.stats())

if __name__ == "__main__":
    run()
