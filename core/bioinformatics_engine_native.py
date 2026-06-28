#!/usr/bin/env python3
"""Bioinformatics Engine for MAGNATRIX-OS."""
from __future__ import annotations
from typing import Any, Dict, List, Optional

class BioinformaticsEngine:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.codon_table = {
            "AUG": "Methionine", "UUU": "Phenylalanine", "UUC": "Phenylalanine",
            "UUA": "Leucine", "UUG": "Leucine", "CUU": "Leucine", "CUC": "Leucine",
        }
    def translate(self, rna: str) -> List[str]:
        proteins = []
        for i in range(0, len(rna) - 2, 3):
            codon = rna[i:i+3]
            proteins.append(self.codon_table.get(codon, "Unknown"))
        return proteins
    def gc_content(self, dna: str) -> float:
        if not dna: return 0.0
        return (dna.count("G") + dna.count("C")) / len(dna) * 100
    def to_dict(self): return {"codons": len(self.codon_table)}
