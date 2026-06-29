"""Doc Image OCR - OCR extraction from images and image-based documents."""
from __future__ import annotations
import json, time, hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class OCRRegion:
    region_id: str
    text: str
    x: float
    y: float
    width: float
    height: float
    confidence: float

    def to_dict(self) -> Dict:
        return {"region_id": self.region_id, "text": self.text, "x": round(self.x,2), "y": round(self.y,2),
                "width": round(self.width,2), "height": round(self.height,2), "confidence": round(self.confidence,3)}

@dataclass
class OCRResult:
    result_id: str
    image_path: str
    full_text: str
    regions: List[OCRRegion] = field(default_factory=list)
    language: str = "en"
    confidence: float = 0.0

    def to_dict(self) -> Dict:
        return {"result_id": self.result_id, "image_path": self.image_path, "full_text": self.full_text,
                "regions": [r.to_dict() for r in self.regions], "language": self.language, "confidence": round(self.confidence,3)}

class DocImageOCR:
    """Simulated OCR extraction from image-based documents."""
    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "doc_ocr"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.results: Dict[str, OCRResult] = {}
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for r in data.get("results",[]):
                    regions = [OCRRegion(**rg) for rg in r.pop("regions",[])]
                    self.results[r["result_id"]] = OCRResult(regions=regions, **r)
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(json.dumps({"results": [r.to_dict() for r in self.results.values()]}, indent=2))

    def extract(self, image_path: str, result_id: str = "") -> OCRResult:
        if not result_id: result_id = f"ocr_{hashlib.md5(image_path.encode()).hexdigest()[:12]}"
        h = hash(image_path)
        simulated_text = f"Extracted text from image {image_path}. Simulated OCR result with confidence."
        regions = [
            OCRRegion(region_id=f"{result_id}_r0", text="Line 1 OCR text", x=10, y=10, width=200, height=20, confidence=0.92),
            OCRRegion(region_id=f"{result_id}_r1", text="Line 2 OCR text", x=10, y=35, width=200, height=20, confidence=0.88),
        ]
        result = OCRResult(result_id=result_id, image_path=image_path, full_text=simulated_text,
                           regions=regions, confidence=0.90)
        self.results[result_id] = result
        self._save_state()
        return result

    def get_stats(self) -> Dict:
        avg_conf = sum(r.confidence for r in self.results.values()) / max(1,len(self.results))
        return {"results_total": len(self.results), "avg_confidence": round(avg_conf,3)}

    def to_dict(self) -> Dict:
        return {"results": [r.to_dict() for r in self.results.values()], "stats": self.get_stats()}

__all__ = ["DocImageOCR", "OCRResult", "OCRRegion"]
