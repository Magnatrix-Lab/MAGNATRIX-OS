"""Doc Markdown Formatter - Convert extracted content to clean Markdown."""
from __future__ import annotations
import json, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

@dataclass
class MarkdownOutput:
    output_id: str
    source_doc: str
    markdown: str
    sections: List[str] = field(default_factory=list)
    tables: List[str] = field(default_factory=list)
    equations: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {"output_id": self.output_id, "source_doc": self.source_doc,
                "markdown_length": len(self.markdown), "sections": self.sections,
                "tables": self.tables, "equations": self.equations, "images": self.images}

class DocMarkdownFormatter:
    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "doc_markdown"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.outputs: Dict[str, MarkdownOutput] = {}
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for o in data.get("outputs",[]): self.outputs[o["output_id"]] = MarkdownOutput(**o)
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"outputs": [o.to_dict() for o in self.outputs.values()]}, indent=2))

    def format(self, text: str, source_doc: str, tables=None, equations=None, images=None, output_id: str = "") -> MarkdownOutput:
        if not output_id: output_id = "md_" + source_doc + "_" + str(int(time.time()))
        NL = chr(10)
        lines = text.split(NL)
        formatted = []
        for line in lines:
            line = line.strip()
            if line.startswith("Chapter ") or line.startswith("Section "):
                formatted.append("## " + line)
            elif line.startswith("Figure "):
                formatted.append("**" + line + "**")
            elif line:
                formatted.append(line)
        md = NL + NL.join(formatted)
        if tables:
            md += NL + NL + NL.join(tables)
        if equations:
            eq_block = NL.join("$$" + NL + e + NL + "$$" for e in equations)
            md += NL + NL + eq_block
        output = MarkdownOutput(output_id=output_id, source_doc=source_doc, markdown=md,
                                sections=[l for l in lines if l.startswith("Chapter") or l.startswith("Section")],
                                tables=tables or [], equations=equations or [], images=images or [])
        self.outputs[output_id] = output
        self._save_state()
        return output

    def get_stats(self) -> Dict:
        avg = sum(len(o.markdown) for o in self.outputs.values()) / max(1,len(self.outputs))
        return {"outputs_total": len(self.outputs), "avg_markdown_length": round(avg,1)}

    def to_dict(self) -> Dict:
        return {"outputs": [o.to_dict() for o in self.outputs.values()], "stats": self.get_stats()}

__all__ = ["DocMarkdownFormatter", "MarkdownOutput"]
