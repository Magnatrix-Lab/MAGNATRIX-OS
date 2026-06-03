"""LLM Batch Processor — Native Python (stdlib only)."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto

class BatchStatus(Enum):
    PENDING = auto()
    PROCESSING = auto()
    COMPLETED = auto()
    FAILED = auto()

@dataclass
class BatchItem:
    id: str
    payload: Dict[str, Any]
    status: BatchStatus = BatchStatus.PENDING
    result: Any = None
    error: Optional[str] = None

class BatchProcessor:
    def __init__(self, batch_size: int = 10) -> None:
        self.batch_size = batch_size
        self._items: List[BatchItem] = []
        self._processor: Optional[Callable[[List[BatchItem]], List[Any]]] = None

    def set_processor(self, processor: Callable[[List[BatchItem]], List[Any]]) -> None:
        self._processor = processor

    def add(self, item: BatchItem) -> None:
        self._items.append(item)

    def process(self) -> List[BatchItem]:
        if not self._processor:
            raise ValueError("No processor set")
        for i in range(0, len(self._items), self.batch_size):
            batch = self._items[i:i + self.batch_size]
            for item in batch:
                item.status = BatchStatus.PROCESSING
            try:
                results = self._processor(batch)
                for item, result in zip(batch, results):
                    item.result = result
                    item.status = BatchStatus.COMPLETED
            except Exception as ex:
                for item in batch:
                    item.status = BatchStatus.FAILED
                    item.error = str(ex)
        return self._items

    def get_stats(self) -> Dict[str, Any]:
        return {"total": len(self._items), "completed": sum(1 for i in self._items if i.status == BatchStatus.COMPLETED), "failed": sum(1 for i in self._items if i.status == BatchStatus.FAILED)}

def run() -> None:
    print("Batch Processor test")
    e = BatchProcessor(batch_size=3)
    e.set_processor(lambda batch: ["Result for " + item.id for item in batch])
    for i in range(7):
        e.add(BatchItem("item" + str(i), {"data": i}))
    results = e.process()
    for item in results:
        print("  " + item.id + ": " + item.status.name + (" -> " + str(item.result) if item.result else ""))
    print("  Stats: " + str(e.get_stats()))
    print("Batch Processor test complete.")

if __name__ == "__main__":
    run()
