#!/usr/bin/env python3
"""modularity_analyzer_native.py — MAGNATRIX-OS Modularity Analyzer

Inspired by Pengrui Han (MIT) LLM Modularity research.
Computes structural modularity metrics: module overlap, domain isolation,
modularity index, power-law analysis. Pure stdlib.
"""
from __future__ import annotations
import ast, json, math, threading, time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

@dataclass
class ModuleProfile:
    name: str; domain: str; file_path: str
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    api_surface: List[str] = field(default_factory=list)
    size_lines: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ModularityReport:
    timestamp: float; total_modules: int; total_domains: int
    domain_sizes: Dict[str, int]
    overlap_matrix: Dict[str, Dict[str, float]]
    domain_isolation_score: float
    modularity_index: float
    power_law_alpha: Optional[float] = None
    recommendations: List[str] = field(default_factory=list)

class ModularityAnalyzerNative:
    DOMAIN_MAP: Dict[str, str] = {
        "vector_memory": "language", "knowledge_graph": "language", "identity": "language", "checkpoint": "language",
        "task_scheduler": "formal", "agent_messaging": "formal", "rbac": "formal", "security_scanner": "formal",
        "metrics_collector": "formal", "modularity_analyzer": "formal", "network_topology": "formal",
        "domain_isolation_test": "formal", "llm_gateway": "physical", "answer_fusion": "physical",
        "auto_recovery": "physical", "boot_optimizer": "physical",
        "deliberation_engine": "social", "human_in_loop": "social", "chat_interface": "social",
    }

    def __init__(self, workspace: str = "./modularity") -> None:
        self.workspace = Path(workspace); self.workspace.mkdir(parents=True, exist_ok=True)
        self._profiles: Dict[str, ModuleProfile] = {}; self._reports: List[ModularityReport] = []
        self._lock = threading.RLock(); self._db_path = self.workspace / "reports.json"; self._load()

    def _load(self) -> None:
        if self._db_path.exists():
            try:
                with open(self._db_path, "r", encoding="utf-8") as f:
                    self._reports = [ModularityReport(**r) for r in json.load(f)]
            except Exception: pass

    def _save(self) -> None:
        with open(self._db_path, "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in self._reports], f, indent=2, default=str)

    def _extract_domain(self, module_name: str) -> str:
        for key, domain in self.DOMAIN_MAP.items():
            if key in module_name.lower(): return domain
        return "unknown"

    def _parse_module(self, file_path: Path) -> Optional[ModuleProfile]:
        try:
            with open(file_path, "r", encoding="utf-8") as f: source = f.read()
            tree = ast.parse(source)
            name = file_path.stem.replace("_native", "").replace(".py", "")
            domain = self._extract_domain(name)
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")]
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import): imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom): imports.append(node.module or "")
            api_surface = classes + functions
            return ModuleProfile(name=name, domain=domain, file_path=str(file_path), classes=classes, functions=functions, imports=list(set(imports)), api_surface=api_surface, size_lines=len(source.splitlines()))
        except Exception: return None

    def scan_modules(self, module_dir: str) -> int:
        count = 0; module_path = Path(module_dir)
        if not module_path.exists(): return 0
        for py_file in module_path.rglob("*.py"):
            if py_file.name.startswith("_"): continue
            profile = self._parse_module(py_file)
            if profile: self._profiles[profile.name] = profile; count += 1
        return count

    def _jaccard(self, a: Set[str], b: Set[str]) -> float:
        if not a and not b: return 1.0
        intersection = len(a & b); union = len(a | b)
        return intersection / union if union > 0 else 0.0

    def _compute_overlap_matrix(self) -> Dict[str, Dict[str, float]]:
        matrix = {}; names = list(self._profiles.keys())
        for i, a in enumerate(names):
            matrix[a] = {}
            for b in names:
                if a == b: matrix[a][b] = 1.0
                else: matrix[a][b] = self._jaccard(set(self._profiles[a].api_surface), set(self._profiles[b].api_surface))
        return matrix

    def _compute_domain_isolation(self, matrix: Dict[str, Dict[str, float]]) -> float:
        within_scores = []; across_scores = []
        for a in matrix:
            for b in matrix[a]:
                if a == b: continue
                domain_a = self._profiles[a].domain; domain_b = self._profiles[b].domain
                score = matrix[a][b]
                if domain_a == domain_b and domain_a != "unknown": within_scores.append(score)
                else: across_scores.append(score)
        avg_within = sum(within_scores) / len(within_scores) if within_scores else 0
        avg_across = sum(across_scores) / len(across_scores) if across_scores else 1
        total = avg_within + avg_across
        if total == 0: return 0.0
        return 1.0 - (avg_across / total)

    def _compute_modularity_index(self, matrix: Dict[str, Dict[str, float]]) -> float:
        names = list(matrix.keys()); n = len(names)
        if n < 2: return 0.0
        within_sum = 0.0; across_sum = 0.0; within_count = 0; across_count = 0
        for i, a in enumerate(names):
            for j, b in enumerate(names):
                if i >= j: continue
                domain_a = self._profiles[a].domain; domain_b = self._profiles[b].domain
                score = matrix[a][b]
                if domain_a == domain_b and domain_a != "unknown": within_sum += score; within_count += 1
                else: across_sum += score; across_count += 1
        avg_within = within_sum / within_count if within_count else 0
        avg_across = across_sum / across_count if across_count else 0
        return max(0.0, (avg_within - avg_across) / (avg_within + avg_across + 0.001))

    def _compute_power_law(self, sizes: List[int]) -> Optional[float]:
        if len(sizes) < 3: return None
        sorted_sizes = sorted(sizes, reverse=True)
        log_x = [math.log(i + 1) for i in range(len(sorted_sizes))]
        log_y = [math.log(s) for s in sorted_sizes if s > 0]
        if len(log_y) < 2: return None
        n = len(log_y); sum_x = sum(log_x[:n]); sum_y = sum(log_y)
        sum_xy = sum(log_x[i] * log_y[i] for i in range(n)); sum_x2 = sum(x * x for x in log_x[:n])
        denom = n * sum_x2 - sum_x * sum_x
        if denom == 0: return None
        return -(n * sum_xy - sum_x * sum_y) / denom

    def _generate_recommendations(self, report: ModularityReport) -> List[str]:
        recs = []
        if report.domain_isolation_score < 0.5: recs.append("Domain isolation is weak. Consider decoupling cross-domain communication via messaging bus.")
        if report.modularity_index < 0.3: recs.append("Modularity index is low. Modules may be too tightly coupled. Refactor shared interfaces.")
        if report.power_law_alpha and (report.power_law_alpha < 1.0 or report.power_law_alpha > 3.0): recs.append(f"Module size distribution alpha={report.power_law_alpha:.2f} is outside typical 1.5-2.5 range. Consider rebalancing module sizes.")
        matrix = report.overlap_matrix
        for a in matrix:
            for b in matrix[a]:
                if a >= b: continue
                if matrix[a][b] > 0.3: recs.append(f"High overlap ({matrix[a][b]:.2f}) between {a} and {b}. Consider merging or isolating shared functionality.")
        if not recs: recs.append("Module architecture is well-modularized. Continue monitoring.")
        return recs[:10]

    def analyze(self, module_dir: Optional[str] = None) -> ModularityReport:
        with self._lock:
            if module_dir: self.scan_modules(module_dir)
            if not self._profiles: return ModularityReport(timestamp=time.time(), total_modules=0, total_domains=0, domain_sizes={}, overlap_matrix={}, domain_isolation_score=0.0, modularity_index=0.0, recommendations=["No modules found."])
            matrix = self._compute_overlap_matrix()
            domains = {}
            for p in self._profiles.values(): domains[p.domain] = domains.get(p.domain, 0) + 1
            sizes = [p.size_lines for p in self._profiles.values()]
            isolation = self._compute_domain_isolation(matrix); q_score = self._compute_modularity_index(matrix); alpha = self._compute_power_law(sizes)
            report = ModularityReport(timestamp=time.time(), total_modules=len(self._profiles), total_domains=len(domains), domain_sizes=domains, overlap_matrix=matrix, domain_isolation_score=isolation, modularity_index=q_score, power_law_alpha=alpha, recommendations=[])
            report.recommendations = self._generate_recommendations(report)
            self._reports.append(report); self._save()
            return report

    def get_latest_report(self) -> Optional[ModularityReport]:
        with self._lock: return self._reports[-1] if self._reports else None

    def get_trend(self, metric: str = "modularity_index", window: int = 10) -> List[float]:
        with self._lock: return [getattr(r, metric, 0.0) for r in self._reports[-window:]]

    def compare_reports(self, report_a_idx: int = -2, report_b_idx: int = -1) -> Dict[str, Any]:
        with self._lock:
            if len(self._reports) < 2: return {"error": "Need at least 2 reports"}
            a = self._reports[report_a_idx]; b = self._reports[report_b_idx]
            return {"time_delta": b.timestamp - a.timestamp, "modules_delta": b.total_modules - a.total_modules, "isolation_delta": b.domain_isolation_score - a.domain_isolation_score, "modularity_delta": b.modularity_index - a.modularity_index, "improved": b.modularity_index > a.modularity_index and b.domain_isolation_score > a.domain_isolation_score}

    def export_json(self, path: Optional[str] = None) -> str:
        report = self.get_latest_report()
        if not report: return "{}"
        output_path = Path(path) if path else self.workspace / "latest_report.json"
        with open(output_path, "w", encoding="utf-8") as f: json.dump(asdict(report), f, indent=2, default=str)
        return str(output_path)

    def print_summary(self, report: Optional[ModularityReport] = None) -> str:
        r = report or self.get_latest_report()
        if not r: return "No report available."
        lines = ["=== Modularity Analysis Report ===", f"Timestamp: {time.ctime(r.timestamp)}", f"Total Modules: {r.total_modules}", f"Domains: {r.total_domains} ({', '.join(f'{k}={v}' for k, v in r.domain_sizes.items())})", f"Domain Isolation Score: {r.domain_isolation_score:.4f} (higher = better)", f"Modularity Index (Q): {r.modularity_index:.4f} (higher = better)"]
        if r.power_law_alpha: lines.append(f"Power-Law Alpha: {r.power_law_alpha:.2f} (typical: 1.5-2.5)")
        lines.append("
--- Recommendations ---")
        for rec in r.recommendations: lines.append(f"- {rec}")
        lines.append("
--- Top Overlap Pairs ---")
        overlaps = [(a, b, r.overlap_matrix[a][b]) for a in r.overlap_matrix for b in r.overlap_matrix[a] if a < b and r.overlap_matrix[a][b] > 0]
        overlaps.sort(key=lambda x: x[2], reverse=True)
        for a, b, score in overlaps[:5]: lines.append(f"  {a} <-> {b}: {score:.4f}")
        return "
".join(lines)

if __name__ == "__main__":
    analyzer = ModularityAnalyzerNative()
    count = analyzer.scan_modules(".")
    print(f"Scanned {count} modules")
    report = analyzer.analyze()
    print(analyzer.print_summary(report))
