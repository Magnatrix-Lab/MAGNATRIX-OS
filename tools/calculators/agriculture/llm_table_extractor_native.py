"""Table Extractor — CSV, TSV, markdown tables, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import re

class TableExtractor:
    def __init__(self):
        self.tables: List[Dict] = []

    def parse_csv(self, text: str, delimiter: str = ',') -> List[List[str]]:
        return [line.split(delimiter) for line in text.strip().split('')]

    def parse_markdown_table(self, text: str) -> List[List[str]]:
        lines = [line.strip() for line in text.strip().split('') if line.strip() and '|' in line]
        if not lines:
            return []
        rows = []
        for line in lines:
            cells = [cell.strip() for cell in line.split('|')]
            cells = [c for c in cells if c]
            if cells and not all(c.replace('-', '') == '' for c in cells):
                rows.append(cells)
        return rows

    def to_csv(self, table: List[List[str]]) -> str:
        return ''.join(','.join(f'"{cell}"' for cell in row) for row in table)

    def to_html(self, table: List[List[str]]) -> str:
        if not table:
            return ""
        html = ["<table>"]
        html.append("<tr>" + "".join(f"<th>{c}</th>" for c in table[0]) + "</tr>")
        for row in table[1:]:
            html.append("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>")
        html.append("</table>")
        return ''.join(html)

    def transpose(self, table: List[List[str]]) -> List[List[str]]:
        if not table:
            return []
        return [[row[i] for row in table] for i in range(len(table[0]))]

    def stats(self, table: List[List[str]]) -> Dict:
        if not table:
            return {}
        return {"rows": len(table), "cols": len(table[0]), "cells": len(table) * len(table[0])}

def run():
    ext = TableExtractor()
    csv = "Name,Age\nAlice,30\nBob,25"
    table = ext.parse_csv(csv)
    print(table)
    md = "| Name | Age |\n|------|-----|\n| Alice | 30 |\n| Bob | 25 |"
    print(ext.parse_markdown_table(md))
    print(ext.to_html(table))
    print(ext.stats(table))

if __name__ == "__main__":
    run()
