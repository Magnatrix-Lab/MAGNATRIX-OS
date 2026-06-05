"""CRISPR Designer"""
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Tuple, Optional
import re, statistics

class PAMType(Enum):
    NGG = auto(); NAG = auto(); NNG = auto(); CUSTOM = auto()

@dataclass
class PAMSite:
    position: int; pam: str; strand: str; pam_type: PAMType

@dataclass
class GuideRNA:
    sequence: str; pam: str; position: int; strand: str
    gc_content: float; doench_score: float; poly_t: bool; self_complement: bool

@dataclass
class OffTarget:
    sequence: str; chrom: str; position: int
    mismatches: int; seed_mismatches: int; score: float

@dataclass
class CRISPRResult:
    target: str
    pam_sites: List[PAMSite] = field(default_factory=list)
    guides: List[GuideRNA] = field(default_factory=list)
    off_targets: List[OffTarget] = field(default_factory=list)
    top_guide: Optional[GuideRNA] = None
    def stats(self) -> Dict[str, float]:
        if not self.guides: return {}
        scores = [g.doench_score for g in self.guides]
        gcs = [g.gc_content for g in self.guides]
        return {"guides_found": len(self.guides), "avg_doench": round(statistics.mean(scores), 4), "best_doench": round(max(scores), 4), "avg_gc": round(statistics.mean(gcs), 4), "off_targets": len(self.off_targets)}

class CRISPRDesigner:
    SEED_LENGTH = 12; GUIDE_LENGTH = 20
    PAM_PATTERNS = {PAMType.NGG: r"(?=([ATCG]{20}GG))", PAMType.NAG: r"(?=([ATCG]{20}AG))", PAMType.NNG: r"(?=([ATCG]{20}CG|TG|AG|GG))"}
    def __init__(self, pam_type=PAMType.NGG, custom_pam=None):
        self.pam_type = pam_type; self.custom_pam = custom_pam; self._init_pattern()
    def _init_pattern(self):
        if self.pam_type == PAMType.CUSTOM and self.custom_pam:
            self.pattern = re.compile(r"(?=([ATCG]{20}" + self.custom_pam + r"))")
        else:
            self.pattern = re.compile(self.PAM_PATTERNS[self.pam_type])
    def _reverse_complement(self, seq):
        comp = {"A": "T", "T": "A", "C": "G", "G": "C", "N": "N"}
        return "".join(comp.get(b, b) for b in reversed(seq))
    def find_pam_sites(self, dna):
        sites = []; dna = dna.upper().replace("U", "T")
        for m in self.pattern.finditer(dna):
            start = m.start(); pam_seq = dna[start: start + self.GUIDE_LENGTH + 2]
            sites.append(PAMSite(start, pam_seq, "+", self.pam_type))
        rev = self._reverse_complement(dna)
        for m in self.pattern.finditer(rev):
            start = m.start(); pam_seq = rev[start: start + self.GUIDE_LENGTH + 2]
            sites.append(PAMSite(len(dna) - start - self.GUIDE_LENGTH - 2, pam_seq, "-", self.pam_type))
        return sorted(sites, key=lambda x: x.position)
    def _gc_content(self, seq):
        gc = seq.count("G") + seq.count("C"); return round(gc / len(seq), 4) if seq else 0.0
    def _has_poly_t(self, seq):
        return "TTTT" in seq or "AAAA" in seq
    def _self_complement_score(self, seq):
        first = seq[:8]; last_rc = self._reverse_complement(seq[-8:])
        return sum(1 for a, b in zip(first, last_rc) if a == b) >= 6
    def _doench_score(self, seq):
        score = 50.0; gc = self._gc_content(seq)
        if gc < 0.35: score -= 15.0
        elif gc > 0.65: score -= 10.0
        else: score += 10.0
        if seq[0] == "G": score += 5.0
        if seq.startswith("GG"): score += 5.0
        if self._has_poly_t(seq): score -= 20.0
        if self._self_complement_score(seq): score -= 10.0
        return max(0.0, min(100.0, round(score, 4)))
    def extract_guides(self, dna, top_n=5):
        sites = self.find_pam_sites(dna); guides = []
        for site in sites:
            if site.strand == "+":
                guide_seq = site.pam[:self.GUIDE_LENGTH]
            else:
                guide_seq = self._reverse_complement(site.pam[:self.GUIDE_LENGTH])
            gc = self._gc_content(guide_seq); doench = self._doench_score(guide_seq)
            guides.append(GuideRNA(sequence=guide_seq, pam=site.pam[-2:], position=site.position,
                strand=site.strand, gc_content=gc, doench_score=doench,
                poly_t=self._has_poly_t(guide_seq),
                self_complement=self._self_complement_score(guide_seq)))
        guides.sort(key=lambda g: g.doench_score, reverse=True)
        return guides[:top_n]
    def score_off_targets(self, guide, genome_chunks):
        hits = []; seed = guide.sequence[-self.SEED_LENGTH:]
        for chrom, chunk in genome_chunks:
            chunk = chunk.upper().replace("U", "T")
            for i in range(len(chunk) - len(guide.sequence)):
                sub = chunk[i: i + len(guide.sequence)]
                mm = sum(1 for a, b in zip(guide.sequence, sub) if a != b)
                seed_mm = sum(1 for a, b in zip(seed, sub[-self.SEED_LENGTH:]) if a != b)
                if mm <= 3 and seed_mm <= 1:
                    score = max(0.0, 100.0 - (mm * 25.0) - (seed_mm * 50.0))
                    hits.append(OffTarget(sub, chrom, i, mm, seed_mm, round(score, 4)))
        hits.sort(key=lambda x: x.score, reverse=True)
        return hits[:20]
    def design(self, target_dna, genome=None):
        result = CRISPRResult(target=target_dna)
        result.pam_sites = self.find_pam_sites(target_dna)
        result.guides = self.extract_guides(target_dna, top_n=10)
        if genome and result.guides:
            result.off_targets = self.score_off_targets(result.guides[0], genome)
        if result.guides:
            result.top_guide = result.guides[0]
        return result

def run():
    dna = "ATGCGATCGATCGATCGATCGG" * 10
    designer = CRISPRDesigner(pam_type=PAMType.NGG)
    result = designer.design(dna)
    print("CRISPR Design Result:")
    print(f"  Guides found: {len(result.guides)}")
    if result.top_guide:
        print(f"  Top guide: {result.top_guide.sequence}")
        print(f"  Doench score: {result.top_guide.doench_score}")
    print(f"  Stats: {result.stats()}")

if __name__ == "__main__":
    run()
