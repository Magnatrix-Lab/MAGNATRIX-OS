"""Doc Multi Column Merger - Merge multi-column layouts into single stream."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

@dataclass
class ColumnBlock:
    block_id: str
    col_index: int
    text: str
    start_y: float
    end_y: float

    def to_dict(self) -> Dict:
        return {"block_id": self.block_id, "col_index": self.col_index, "text": self.text,
                "start_y": round(self.start_y,2), "end_y": round(self.end_y,2)}

@dataclass
class MergedPage:
    page_id: str
    page_number: int
    merged_text: str
    column_blocks: List[ColumnBlock] = field(default_factory=list)
    column_count: int = 1

    def to_dict(self) -> Dict:
        return {"page_id": self.page_id, "page_number": self.page_number, "merged_text": self.merged_text,
                "column_blocks": [b.to_dict() for b in self.column_blocks], "column_count": self.column_count}

class DocMultiColumnMerger:
    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "doc_column_merger"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.pages: Dict[str, MergedPage] = {}
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for p in data.get("pages",[]):
                    blocks = [ColumnBlock(**b) for b in p.pop("column_blocks",[])]
                    self.pages[p["page_id"]] = MergedPage(column_blocks=blocks, **p)
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"pages": [p.to_dict() for p in self.pages.values()]}, indent=2))

    def merge(self, columns: List[List[Dict]], page_id: str, page_number: int) -> MergedPage:
        blocks = []
        for ci, col in enumerate(columns):
            for item in col:
                blocks.append(ColumnBlock(
                    block_id=item.get("block_id", page_id + "_c" + str(ci) + "_b"),
                    col_index=ci, text=item.get("text",""),
                    start_y=item.get("y",0.0),
                    end_y=item.get("y",0.0)+item.get("height",0.0)))
        sorted_blocks = sorted(blocks, key=lambda b: (b.start_y, b.col_index))
        NL = chr(10)
        merged_text = NL.join(b.text for b in sorted_blocks if b.text)
        page = MergedPage(page_id=page_id, page_number=page_number, merged_text=merged_text,
                          column_blocks=sorted_blocks, column_count=len(columns))
        self.pages[page_id] = page
        self._save_state()
        return page

    def get_stats(self) -> Dict:
        return {"pages_total": len(self.pages), "multi_column_pages": sum(1 for p in self.pages.values() if p.column_count > 1)}

    def to_dict(self) -> Dict:
        return {"pages": [p.to_dict() for p in self.pages.values()], "stats": self.get_stats()}

__all__ = ["DocMultiColumnMerger", "MergedPage", "ColumnBlock"]
