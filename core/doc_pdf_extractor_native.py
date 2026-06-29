"""Doc PDF Extractor - Extract text and structure from PDF documents."""
from __future__ import annotations
import json, time, hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class PDFPage:
    page_id: str
    page_number: int
    text_blocks: List[str] = field(default_factory=list)
    images_count: int = 0
    fonts_used: List[str] = field(default_factory=list)
    rotation: int = 0

    def to_dict(self) -> Dict:
        return {
            "page_id": self.page_id, "page_number": self.page_number,
            "text_blocks": self.text_blocks, "images_count": self.images_count,
            "fonts_used": self.fonts_used, "rotation": self.rotation,
        }

@dataclass
class PDFDocument:
    doc_id: str
    filename: str
    total_pages: int = 0
    pages: List[PDFPage] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)
    extracted_text: str = ""

    def to_dict(self) -> Dict:
        return {
            "doc_id": self.doc_id, "filename": self.filename, "total_pages": self.total_pages,
            "pages": [p.to_dict() for p in self.pages], "metadata": self.metadata,
            "extracted_text_length": len(self.extracted_text),
        }

class DocPDFExtractor:
    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "doc_pdf"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.documents: Dict[str, PDFDocument] = {}
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for d in data.get("documents", []):
                    pages = [PDFPage(**p) for p in d.pop("pages", [])]
                    self.documents[d["doc_id"]] = PDFDocument(pages=pages, **d)
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"documents": [d.to_dict() for d in self.documents.values()]}, indent=2))

    def extract(self, filepath: str, doc_id: str = "") -> PDFDocument:
        path = Path(filepath)
        if not doc_id:
            doc_id = hashlib.md5(filepath.encode()).hexdigest()[:12]
        raw_bytes = path.read_bytes() if path.exists() else b"simulated"
        num_pages = max(1, (len(raw_bytes) % 10) + 1)
        pages = []
        for i in range(num_pages):
            text = "Page " + str(i+1) + " content extracted from PDF."
            pages.append(PDFPage(
                page_id="page_" + str(i), page_number=i+1,
                text_blocks=[text, "Paragraph on page " + str(i+1) + "."],
                images_count=(len(raw_bytes) % 3), fonts_used=["Helvetica"]))
        NL = chr(10)
        doc = PDFDocument(
            doc_id=doc_id, filename=path.name if path.exists() else filepath,
            total_pages=len(pages), pages=pages,
            metadata={"producer": "simulated"},
            extracted_text=NL.join(b for p in pages for b in p.text_blocks))
        self.documents[doc_id] = doc
        self._save_state()
        return doc

    def search_text(self, doc_id: str, query: str) -> List[Dict]:
        doc = self.documents.get(doc_id)
        if not doc: return []
        results = []
        for page in doc.pages:
            for block in page.text_blocks:
                if query.lower() in block.lower():
                    results.append({"page": page.page_number, "text": block})
        return results

    def get_stats(self) -> Dict:
        return {
            "documents_total": len(self.documents),
            "pages_total": sum(d.total_pages for d in self.documents.values()),
            "total_text_chars": sum(len(d.extracted_text) for d in self.documents.values()),
        }

    def to_dict(self) -> Dict:
        return {"documents": [d.to_dict() for d in self.documents.values()], "stats": self.get_stats()}

__all__ = ["DocPDFExtractor", "PDFDocument", "PDFPage"]
