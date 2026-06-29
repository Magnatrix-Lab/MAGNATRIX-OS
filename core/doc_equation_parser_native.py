"""Doc Equation Parser - Extract and format mathematical equations."""
from __future__ import annotations
import json, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class Equation:
    equation_id: str
    raw_text: str = ""
    latex: str = ""
    inline: bool = False
    confidence: float = 0.0
    page_number: int = 0

    def to_dict(self) -> Dict:
        return {"equation_id": self.equation_id, "raw_text": self.raw_text, "latex": self.latex,
                "inline": self.inline, "confidence": round(self.confidence,3), "page_number": self.page_number}

class DocEquationParser:
    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "doc_equation"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.equations: Dict[str, Equation] = {}
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for e in data.get("equations",[]): self.equations[e["equation_id"]] = Equation(**e)
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(json.dumps({"equations": [e.to_dict() for e in self.equations.values()]}, indent=2))

    def _to_latex(self, raw: str) -> str:
        raw = raw.strip()
        latex = raw.replace("^","^").replace("_","_")
        # Simple fraction detection
        if "/" in latex and not latex.startswith("\frac"):
            parts = latex.split("/",1)
            if len(parts) == 2:
                latex = f"\frac{{{parts[0].strip()}}}{{{parts[1].strip()}}}"
        return latex

    def parse(self, raw_text: str, page_number: int = 1, inline: bool = False, equation_id: str = "") -> Equation:
        if not equation_id: equation_id = f"eq_{page_number}_{int(time.time()*1000)}"
        eq = Equation(equation_id=equation_id, raw_text=raw_text, latex=self._to_latex(raw_text),
                      inline=inline, confidence=0.85, page_number=page_number)
        self.equations[equation_id] = eq
        self._save_state()
        return eq

    def batch_parse(self, raw_equations: List[str], page_number: int = 1) -> List[Equation]:
        return [self.parse(r, page_number, inline=False, equation_id=f"eq_{page_number}_{i}_{int(time.time())}") for i,r in enumerate(raw_equations)]

    def get_stats(self) -> Dict:
        inline_count = sum(1 for e in self.equations.values() if e.inline)
        return {"equations_total": len(self.equations), "inline": inline_count, "display": len(self.equations)-inline_count}

    def to_dict(self) -> Dict:
        return {"equations": [e.to_dict() for e in self.equations.values()], "stats": self.get_stats()}

__all__ = ["DocEquationParser", "Equation"]
