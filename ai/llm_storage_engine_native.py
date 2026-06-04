"""Storage Engine - Page-based storage for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto

class PageType(Enum):
    DATA = auto(); INDEX = auto(); FREE = auto()

@dataclass
class Page:
    page_id: int = 0
    page_type: PageType = PageType.DATA
    data: Dict[str, str] = field(default_factory=dict)
    next_page: Optional[int] = None

@dataclass
class StorageEngine:
    page_size: int = 4096
    pages: Dict[int, Page] = field(default_factory=dict)
    page_counter: int = 0
    free_pages: List[int] = field(default_factory=list)

    def allocate_page(self, page_type: PageType = PageType.DATA) -> int:
        if self.free_pages:
            page_id = self.free_pages.pop()
            self.pages[page_id] = Page(page_id, page_type)
            return page_id
        self.page_counter += 1
        self.pages[self.page_counter] = Page(self.page_counter, page_type)
        return self.page_counter

    def write(self, page_id: int, key: str, value: str) -> bool:
        if page_id not in self.pages: return False
        self.pages[page_id].data[key] = value
        return True

    def read(self, page_id: int, key: str) -> Optional[str]:
        if page_id not in self.pages: return None
        return self.pages[page_id].data.get(key)

    def delete_page(self, page_id: int) -> bool:
        if page_id not in self.pages: return False
        del self.pages[page_id]
        self.free_pages.append(page_id)
        return True

    def stats(self) -> dict:
        return {"pages": len(self.pages), "free": len(self.free_pages), "page_size": self.page_size}

def run():
    se = StorageEngine()
    pid = se.allocate_page(PageType.DATA)
    se.write(pid, "row1", "data1")
    print("Read:", se.read(pid, "row1"))
    print("Stats:", se.stats())

if __name__ == "__main__": run()
