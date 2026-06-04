"""Virtual Memory — paging, page tables, TLB, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum, auto

@dataclass
class Page:
    page_id: int
    physical_frame: Optional[int] = None
    present: bool = False
    dirty: bool = False

class VirtualMemory:
    def __init__(self, page_size: int = 4096, num_pages: int = 16, num_frames: int = 4):
        self.page_size = page_size
        self.num_pages = num_pages
        self.num_frames = num_frames
        self.page_table: Dict[int, Page] = {i: Page(i) for i in range(num_pages)}
        self.frames: List[Optional[int]] = [None] * num_frames
        self.tlb: Dict[int, int] = {}
        self.faults = 0
        self.accesses = 0

    def translate(self, virtual_address: int) -> Optional[int]:
        page_num = virtual_address // self.page_size
        offset = virtual_address % self.page_size
        self.accesses += 1
        if page_num in self.tlb:
            frame = self.tlb[page_num]
            return frame * self.page_size + offset
        page = self.page_table.get(page_num)
        if not page or not page.present:
            self.faults += 1
            if not self._page_in(page_num):
                return None
        frame = page.physical_frame
        self.tlb[page_num] = frame
        return frame * self.page_size + offset

    def _page_in(self, page_num: int) -> bool:
        page = self.page_table[page_num]
        for i, frame in enumerate(self.frames):
            if frame is None:
                self.frames[i] = page_num
                page.physical_frame = i
                page.present = True
                return True
        # FIFO replacement
        victim = self.frames.pop(0)
        if victim is not None:
            self.page_table[victim].present = False
            self.page_table[victim].physical_frame = None
        self.frames.append(page_num)
        page.physical_frame = len(self.frames) - 1
        page.present = True
        return True

    def write(self, virtual_address: int):
        page_num = virtual_address // self.page_size
        page = self.page_table.get(page_num)
        if page:
            page.dirty = True

    def stats(self) -> Dict:
        return {"page_size": self.page_size, "faults": self.faults, "accesses": self.accesses, "hit_rate": 1 - self.faults / self.accesses if self.accesses else 0}

def run():
    vm = VirtualMemory(4096, 8, 2)
    print(vm.translate(0))
    print(vm.translate(4096))
    print(vm.translate(8192))
    print(vm.translate(0))
    print(vm.stats())

if __name__ == "__main__":
    run()
