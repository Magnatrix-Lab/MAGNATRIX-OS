"""Native stdlib module: Glossary Checker
Validates glossary term consistency across translated content.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Set

@dataclass
class GlossaryEntry:
    source_term: str
    target_term: str
    context: str = ""

@dataclass
class GlossaryChecker:
    project_name: str
    glossary: List[GlossaryEntry] = field(default_factory=list)

    def term_count(self) -> int:
        return len(self.glossary)

    def check_consistency(self, translations: Dict[str, str]) -> Dict[str, List[str]]:
        issues = {}
        for entry in self.glossary:
            source_lower = entry.source_term.lower()
            for src_text, tgt_text in translations.items():
                if source_lower in src_text.lower():
                    if entry.target_term.lower() not in tgt_text.lower():
                        issues[entry.source_term] = issues.get(entry.source_term, []) + [tgt_text[:50]]
        return issues

    def coverage(self, source_texts: List[str]) -> float:
        if not source_texts or not self.glossary:
            return 0.0
        found = 0
        for entry in self.glossary:
            for text in source_texts:
                if entry.source_term.lower() in text.lower():
                    found += 1
                    break
        return (found / len(self.glossary)) * 100

    def stats(self, source_texts: List[str] = None) -> Dict:
        return {
            "project": self.project_name,
            "term_count": self.term_count(),
            "coverage_pct": round(self.coverage(source_texts or []), 1) if source_texts else None,
        }

def run():
    gc = GlossaryChecker(
        project_name="Software Docs",
        glossary=[
            GlossaryEntry("dashboard", "tableau de bord", "UI"),
            GlossaryEntry("widget", "widget", "UI"),
            GlossaryEntry("pipeline", "pipeline", "tech"),
        ]
    )
    print(gc.stats(["Open the dashboard to view widgets", "Configure the pipeline settings"]))

if __name__ == "__main__":
    run()
