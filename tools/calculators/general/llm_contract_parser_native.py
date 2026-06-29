"""Contract Parser — clause extraction, parties, obligations, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto
import re

class ContractParser:
    def __init__(self):
        self.contracts: List[Dict] = []
        self.clause_patterns = {
            "parties": r"(?:Party|Between)\s+([A-Z][\w\s]+)",
            "effective_date": r"(?:Effective|Commencement)\s+Date.*?([\d]{1,2}[/-][\d]{1,2}[/-][\d]{2,4})",
            "term": r"(?:Term|Period).*?(\d+)\s*(year|month|day)",
            "payment": r"(?:Payment|Fee|Price).*?\$?([\d,]+\.?\d*)",
            "termination": r"(?:Termination|Cancel).*?(\d+)\s*day",
        }

    def parse(self, contract_text: str) -> Dict:
        result = {"text": contract_text[:200], "clauses": {}}
        for clause_type, pattern in self.clause_patterns.items():
            matches = re.findall(pattern, contract_text, re.IGNORECASE)
            if matches:
                result["clauses"][clause_type] = matches
        self.contracts.append(result)
        return result

    def extract_obligations(self, text: str) -> List[str]:
        sentences = re.split(r'[.\n]+', text)
        obligations = []
        for s in sentences:
            if any(w in s.lower() for w in ["shall", "must", "will", "agrees to", "is required"]):
                obligations.append(s.strip()[:100])
        return obligations

    def extract_dates(self, text: str) -> List[str]:
        return re.findall(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", text)

    def stats(self) -> Dict:
        return {"contracts": len(self.contracts), "patterns": len(self.clause_patterns)}

def run():
    cp = ContractParser()
    text = "Party A and Party B agree. Effective Date: 01/15/2024. Payment of $5000. Term: 2 years."
    print(cp.parse(text))
    print(cp.extract_obligations("Party A shall deliver goods. Party B must pay within 30 days."))
    print(cp.stats())

if __name__ == "__main__":
    run()
