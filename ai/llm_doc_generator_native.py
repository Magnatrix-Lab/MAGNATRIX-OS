"""LLM Doc Generator — Native Python (stdlib only)."""
from __future__ import annotations
import inspect, re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class DocFormat(Enum):
    MARKDOWN = auto()
    HTML = auto()
    PLAIN = auto()

@dataclass
class FunctionDoc:
    name: str
    signature: str
    docstring: str
    parameters: List[str] = field(default_factory=list)
    returns: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

class DocGenerator:
    def __init__(self) -> None:
        self._functions: List[FunctionDoc] = []

    def parse_module(self, module_name: str, source: str) -> List[FunctionDoc]:
        docs = []
        pattern = r'def\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*([^:]+))?\s*:\s*(?:"""|\'\'\')?(.*?)?(?:"""|\'\'\')?'
        for match in re.finditer(pattern, source, re.DOTALL):
            name, params, returns, doc = match.groups()
            docs.append(FunctionDoc(name, name + "(" + (params or "") + ")", (doc or "").strip(), [p.strip() for p in (params or "").split(",") if p.strip()], returns or ""))
        self._functions.extend(docs)
        return docs

    def to_markdown(self, doc: FunctionDoc) -> str:
        lines = ["## " + doc.name, "", "```python", "def " + doc.signature + ":", "```", ""]
        if doc.docstring:
            lines.append(doc.docstring)
            lines.append("")
        if doc.parameters:
            lines.append("**Parameters:**")
            for p in doc.parameters:
                lines.append("- " + p)
            lines.append("")
        if doc.returns:
            lines.append("**Returns:** " + doc.returns)
            lines.append("")
        return "\n".join(lines)

    def generate(self, format: DocFormat = DocFormat.MARKDOWN) -> str:
        parts = []
        for doc in self._functions:
            if format == DocFormat.MARKDOWN:
                parts.append(self.to_markdown(doc))
        return "\n".join(parts)

    def get_stats(self) -> Dict[str, Any]:
        return {"functions": len(self._functions)}

def run() -> None:
    print("Doc Generator test")
    e = DocGenerator()
    source = '''
def add(a, b):
    """Add two numbers."""
    return a + b

def greet(name):
    """Greet someone."""
    return "Hello " + name
'''
    e.parse_module("test", source)
    print("  Parsed: " + str(len(e._functions)) + " functions")
    print("  Markdown:\n" + e.generate())
    print("Doc Generator test complete.")

if __name__ == "__main__":
    run()
