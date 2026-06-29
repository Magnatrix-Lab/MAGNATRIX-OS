"""
code_graph_analyzer_native.py
MAGNATRIX-OS — Code Graph Analyzer

Inspired by telagod/code-abyss code graph intelligence:
Call graph, impact analysis, hotspot detection, change coupling. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class CodeSymbol:
    symbol_id: str
    name: str
    symbol_type: str  # function, class, method, variable
    file_path: str
    line_number: int
    callers: List[str] = field(default_factory=list)
    callees: List[str] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class ImpactResult:
    symbol_id: str
    direct_callers: int
    transitive_callers: int
    test_coverage: int
    uncovered_paths: int
    risk_score: float


class CodeGraphAnalyzer:
    """Code graph intelligence: call graph, impact analysis, hotspot detection."""

    def __init__(self, data_dir: str = "./code_graph"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.symbols: Dict[str, CodeSymbol] = {}
        self.impacts: Dict[str, ImpactResult] = {}
        self._load()

    def _load(self) -> None:
        for fname in ["symbols.json", "impacts.json"]:
            f = self.data_dir / fname
            if f.exists():
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        if fname == "symbols.json":
                            self.symbols = {k: CodeSymbol(**v) for k, v in data.items()}
                        else:
                            self.impacts = {k: ImpactResult(**v) for k, v in data.items()}
                except Exception:
                    pass

    def _save(self) -> None:
        with open(self.data_dir / "symbols.json", "w", encoding="utf-8") as f:
            json.dump({k: asdict(v) for k, v in self.symbols.items()}, f, indent=2)
        with open(self.data_dir / "impacts.json", "w", encoding="utf-8") as f:
            json.dump({k: asdict(v) for k, v in self.impacts.items()}, f, indent=2)

    def add_symbol(self, symbol_id: str, name: str, symbol_type: str, file_path: str,
                   line_number: int, callers: Optional[List[str]] = None,
                   callees: Optional[List[str]] = None, confidence: float = 1.0) -> CodeSymbol:
        sym = CodeSymbol(
            symbol_id=symbol_id, name=name, symbol_type=symbol_type,
            file_path=file_path, line_number=line_number,
            callers=callers or [], callees=callees or [], confidence=confidence,
        )
        self.symbols[symbol_id] = sym
        self._save()
        return sym

    def trace_callers(self, symbol_id: str, depth: int = 3) -> List[str]:
        """Trace all callers up to a depth limit."""
        result = []
        current = [symbol_id]
        for _ in range(depth):
            next_level = []
            for sid in current:
                sym = self.symbols.get(sid)
                if sym:
                    for caller in sym.callers:
                        if caller not in result and caller != symbol_id:
                            result.append(caller)
                            next_level.append(caller)
            current = next_level
        return result

    def trace_callees(self, symbol_id: str, depth: int = 3) -> List[str]:
        """Trace all callees up to a depth limit."""
        result = []
        current = [symbol_id]
        for _ in range(depth):
            next_level = []
            for sid in current:
                sym = self.symbols.get(sid)
                if sym:
                    for callee in sym.callees:
                        if callee not in result and callee != symbol_id:
                            result.append(callee)
                            next_level.append(callee)
            current = next_level
        return result

    def impact_analysis(self, symbol_id: str) -> ImpactResult:
        """Analyze impact of changing a symbol."""
        sym = self.symbols.get(symbol_id)
        if not sym:
            return ImpactResult(symbol_id, 0, 0, 0, 0, 0.0)
        direct = len(sym.callers)
        transitive = len(self.trace_callers(symbol_id, depth=5))
        tests = sum(1 for s in self.symbols.values() if "test" in s.name.lower() and symbol_id in s.name)
        uncovered = max(0, transitive - tests)
        risk = min(10.0, (direct * 0.3 + transitive * 0.05 + uncovered * 0.1))
        result = ImpactResult(
            symbol_id=symbol_id, direct_callers=direct, transitive_callers=transitive,
            test_coverage=tests, uncovered_paths=uncovered, risk_score=round(risk, 2),
        )
        self.impacts[symbol_id] = result
        self._save()
        return result

    def hotspot_map(self, top_n: int = 10) -> List[CodeSymbol]:
        """Find symbols with highest connectivity."""
        scored = [(s.symbol_id, len(s.callers) + len(s.callees)) for s in self.symbols.values()]
        scored.sort(key=lambda x: x[1], reverse=True)
        top_ids = [sid for sid, _ in scored[:top_n]]
        return [self.symbols[sid] for sid in top_ids if sid in self.symbols]

    def change_coupling(self, file_a: str, file_b: str) -> float:
        """Measure how often two files change together."""
        a_symbols = [s for s in self.symbols.values() if s.file_path == file_a]
        b_symbols = [s for s in self.symbols.values() if s.file_path == file_b]
        shared = 0
        for a in a_symbols:
            for b in b_symbols:
                if a.symbol_id in b.callers or b.symbol_id in a.callers:
                    shared += 1
        total = len(a_symbols) + len(b_symbols)
        return round(shared / max(1, total), 4)

    def get_stats(self) -> Dict[str, Any]:
        return {"symbols": len(self.symbols), "impacts_analyzed": len(self.impacts)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["CodeGraphAnalyzer", "CodeSymbol", "ImpactResult"]