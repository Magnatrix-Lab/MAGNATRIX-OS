"""Doc Page Linearizer - Natural reading order for document layout."""
from __future__ import annotations
import json, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

@dataclass
class LayoutElement:
    element_id: str
    element_type: str
    x: float
    y: float
    width: float
    height: float
    content: str = ""
    reading_order: int = 0
    confidence: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "element_id": self.element_id, "element_type": self.element_type,
            "x": round(self.x,2), "y": round(self.y,2), "width": round(self.width,2),
            "height": round(self.height,2), "content": self.content[:200],
            "reading_order": self.reading_order, "confidence": round(self.confidence,3)}

@dataclass
class LinearizedPage:
    page_id: str
    page_number: int
    elements: List[LayoutElement] = field(default_factory=list)
    column_count: int = 1
    reading_order_corrected: bool = False

    def to_dict(self) -> Dict:
        return {
            "page_id": self.page_id, "page_number": self.page_number,
            "elements": [e.to_dict() for e in self.elements],
            "column_count": self.column_count, "reading_order_corrected": self.reading_order_corrected}

class DocPageLinearizer:
    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "doc_linearizer"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.pages: Dict[str, LinearizedPage] = {}
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for p in data.get("pages",[]):
                    elems = [LayoutElement(**e) for e in p.pop("elements",[])]
                    self.pages[p["page_id"]] = LinearizedPage(elements=elems, **p)
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"pages": [p.to_dict() for p in self.pages.values()]}, indent=2))

    def linearize(self, elements: List[Dict], page_id: str = "", page_number: int = 1) -> LinearizedPage:
        elems = []
        for i, e in enumerate(elements):
            elems.append(LayoutElement(
                element_id=e.get("element_id","e"+str(i)), element_type=e.get("element_type","text"),
                x=e.get("x",0.0), y=e.get("y",0.0), width=e.get("width",0.0), height=e.get("height",0.0),
                content=e.get("content",""), confidence=e.get("confidence",0.8)))
        cols = self._detect_columns(elems)
        ordered = self._sort_reading_order(elems, cols)
        page = LinearizedPage(
            page_id=page_id or "page_"+str(page_number)+"_"+str(int(time.time())),
            page_number=page_number, elements=ordered, column_count=cols,
            reading_order_corrected=True)
        self.pages[page.page_id] = page
        self._save_state()
        return page

    def _detect_columns(self, elems: List[LayoutElement]) -> int:
        if not elems: return 1
        xvals = sorted(set(e.x for e in elems if e.element_type == "text"))
        if len(xvals) < 2: return 1
        gaps = [xvals[i+1]-xvals[i] for i in range(len(xvals)-1)]
        return min(sum(1 for g in gaps if g > 50) + 1, 4)

    def _sort_reading_order(self, elems: List[LayoutElement], cols: int) -> List[LayoutElement]:
        if cols <= 1: return sorted(elems, key=lambda e: (e.y, e.x))
        xvals = [e.x for e in elems if e.element_type == "text"]
        if not xvals: return sorted(elems, key=lambda e: (e.y, e.x))
        x_min, x_max = min(xvals), max(xvals)
        col_w = (x_max - x_min) / cols
        ordered = []
        for c in range(cols):
            cs = x_min + c*col_w
            ce = x_min + (c+1)*col_w if c < cols-1 else x_max + 1
            col_elems = sorted([e for e in elems if cs <= e.x < ce], key=lambda e: e.y)
            ordered.extend(col_elems)
        for i, e in enumerate(ordered): e.reading_order = i
        return ordered

    def get_text_stream(self, page_id: str) -> str:
        page = self.pages.get(page_id)
        if not page: return ""
        return chr(10).join(e.content for e in page.elements if e.content)

    def get_stats(self) -> Dict:
        total = sum(len(p.elements) for p in self.pages.values())
        multi = sum(1 for p in self.pages.values() if p.column_count > 1)
        return {"pages_total": len(self.pages), "elements_total": total, "multi_column_pages": multi,
                "avg_elements_per_page": round(total/max(1,len(self.pages)),1)}

    def to_dict(self) -> Dict:
        return {"pages": [p.to_dict() for p in self.pages.values()], "stats": self.get_stats()}

__all__ = ["DocPageLinearizer", "LayoutElement", "LinearizedPage"]
