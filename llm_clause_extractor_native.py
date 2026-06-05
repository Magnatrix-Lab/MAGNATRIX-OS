"""Clause Extractor — boilerplate, key terms, definitions, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
import re

@dataclass
class ClauseExtractor:
    text: str = ""

    def extract_definitions(self) -> Dict[str, str]:
        defs = {}
        for m in re.finditer(r'"([^"]+)"\s+means\s+([^.;]+)', self.text):
            defs[m.group(1)] = m.group(2).strip()
        return defs

    def extract_dates(self) -> List[str]:
        return re.findall(r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}', self.text)

    def extract_amounts(self) -> List[str]:
        return re.findall(r'\$[\d,]+(?:\.\d{2})?', self.text)

    def extract_parties(self) -> List[str]:
        return re.findall(r'(?:between|among)\s+([A-Z][A-Za-z\s]+(?:and|&)[A-Z][A-Za-z\s]+)', self.text)

    def key_terms(self) -> List[str]:
        terms = []
        for phrase in ["confidential information", "intellectual property", "force majeure", "indemnification", "termination for cause"]:
            if phrase in self.text.lower():
                terms.append(phrase)
        return terms

    def stats(self) -> Dict:
        return {"definitions": len(self.extract_definitions()), "dates": len(self.extract_dates()), "amounts": len(self.extract_amounts())}

def run():
    text = 'The "Service" means the software. Between ABC Corp and XYZ Inc. Payment of $10,000 due on January 15, 2025. Confidential information must be protected.'
    ce = ClauseExtractor(text)
    print(ce.stats())
    print("Definitions:", ce.extract_definitions())
    print("Key terms:", ce.key_terms())

if __name__ == "__main__":
    run()
