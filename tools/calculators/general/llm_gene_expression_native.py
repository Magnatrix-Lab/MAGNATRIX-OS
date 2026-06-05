"""Gene Expression — TPM/FPKM, differential, normalization, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class GeneExpression:
    counts: Dict[str, List[int]] = field(default_factory=dict)
    """gene -> raw counts across samples"""

    def tpm(self, gene_lengths: Dict[str, int]) -> Dict[str, List[float]]:
        tpm = {}
        for gene, counts in self.counts.items():
            length = gene_lengths.get(gene, 1000)
            rpk = [c / (length / 1000) for c in counts]
            total = sum(rpk) / 1e6
            tpm[gene] = [r / total if total > 0 else 0 for r in rpk]
        return tpm

    def log2_fold_change(self, group1: List[str], group2: List[str], pseudo: float = 1.0) -> Dict[str, float]:
        fc = {}
        for gene, counts in self.counts.items():
            c1 = [counts[self._sample_idx(s)] for s in group1 if self._sample_idx(s) is not None]
            c2 = [counts[self._sample_idx(s)] for s in group2 if self._sample_idx(s) is not None]
            m1 = sum(c1) / len(c1) if c1 else 0
            m2 = sum(c2) / len(c2) if c2 else 0
            fc[gene] = math.log2((m2 + pseudo) / (m1 + pseudo))
        return fc

    def _sample_idx(self, name: str) -> Optional[int]:
        try:
            return int(name)
        except:
            return None

    def normalize_median(self) -> Dict[str, List[float]]:
        """Median-of-ratios normalization."""
        if not self.counts:
            return {}
        genes = list(self.counts.keys())
        n = len(self.counts[genes[0]])
        geometric_means = []
        for i in range(n):
            vals = [self.counts[g][i] for g in genes if self.counts[g][i] > 0]
            gm = math.exp(sum(math.log(v) for v in vals) / len(vals)) if vals else 1
            geometric_means.append(gm)
        ratios = {g: [c / gm for c, gm in zip(self.counts[g], geometric_means)] for g in genes}
        medians = [sorted([ratios[g][i] for g in genes])[len(genes)//2] for i in range(n)]
        return {g: [c / medians[i] for i, c in enumerate(self.counts[g])] for g in genes}

    def stats(self) -> Dict:
        return {"genes": len(self.counts), "samples": len(next(iter(self.counts.values()))) if self.counts else 0}

def run():
    ge = GeneExpression({"A": [100, 200, 150], "B": [50, 60, 55]})
    print("TPM:", ge.tpm({"A": 1000, "B": 500}))
    print("Log2FC:", ge.log2_fold_change(["0"], ["1"]))
    print(ge.stats())

if __name__ == "__main__":
    run()
