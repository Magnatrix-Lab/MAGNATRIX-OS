"""LLM Query Parser — Native Python (stdlib only)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum, auto

class QueryOperator(Enum):
    AND = auto()
    OR = auto()
    NOT = auto()
    PHRASE = auto()
    WILDCARD = auto()
    RANGE = auto()

@dataclass
class QueryTerm:
    field: Optional[str]
    value: str
    operator: QueryOperator = QueryOperator.AND
    negated: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

class QueryParser:
    def __init__(self) -> None:
        self._terms: List[QueryTerm] = []

    def parse(self, query: str) -> List[QueryTerm]:
        terms = []
        phrases = re.findall(r'"([^"]*)"', query)
        for phrase in phrases:
            terms.append(QueryTerm(None, phrase, QueryOperator.PHRASE))
            query = query.replace('"' + phrase + '"', "")
        field_matches = re.findall(r'(\w+):([^\s]+)', query)
        for field, value in field_matches:
            terms.append(QueryTerm(field, value, QueryOperator.AND))
            query = query.replace(field + ":" + value, "")
        remaining = re.findall(r'\S+', query)
        for word in remaining:
            if word.upper() == "AND":
                continue
            elif word.upper() == "OR":
                continue
            elif word.upper() == "NOT":
                continue
            elif word.startswith("-"):
                terms.append(QueryTerm(None, word[1:], QueryOperator.AND, True))
            elif word.startswith("+"):
                terms.append(QueryTerm(None, word[1:], QueryOperator.AND, False))
            elif "*" in word or "?" in word:
                terms.append(QueryTerm(None, word, QueryOperator.WILDCARD))
            elif ".." in word:
                parts = word.split("..")
                if len(parts) == 2:
                    terms.append(QueryTerm(None, word, QueryOperator.RANGE))
            else:
                terms.append(QueryTerm(None, word, QueryOperator.AND))
        self._terms = terms
        return terms

    def to_dict(self, terms: List[QueryTerm]) -> Dict[str, Any]:
        return {"terms": [{"field": t.field, "value": t.value, "op": t.operator.name, "negated": t.negated} for t in terms]}

    def get_stats(self, terms: List[QueryTerm]) -> Dict[str, Any]:
        counts = {}
        for t in terms:
            counts[t.operator.name] = counts.get(t.operator.name, 0) + 1
        return {"total": len(terms), "by_operator": counts, "has_field": sum(1 for t in terms if t.field is not None)}

def run() -> None:
    print("Query Parser test")
    e = QueryParser()
    query = 'title:"machine learning" author:smith +important -draft date:2020..2024'
    terms = e.parse(query)
    for t in terms:
        print("  " + str(t.field) + ":" + t.value + " (" + t.operator.name + ")")
    print("  Stats: " + str(e.get_stats(terms)))
    print("Query Parser test complete.")

if __name__ == "__main__":
    run()
