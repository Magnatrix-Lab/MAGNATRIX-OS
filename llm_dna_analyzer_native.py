"""DNA Analyzer."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class DNAAnalyzer:
    sequence: str = ""
    def gc_content(self) -> float:
        if not self.sequence: return 0.0
        gc = self.sequence.upper().count("G") + self.sequence.upper().count("C")
        return gc / len(self.sequence)
    def transcribe(self) -> str:
        return self.sequence.upper().replace("T", "U")
    def translate(self) -> str:
        t = {"UUU":"F","UUC":"F","UUA":"L","UUG":"L","CUU":"L","CUC":"L","CUA":"L","CUG":"L","AUU":"I","AUC":"I","AUA":"I","AUG":"M","GUU":"V","GUC":"V","GUA":"V","GUG":"V","UCU":"S","UCC":"S","UCA":"S","UCG":"S","CCU":"P","CCC":"P","CCA":"P","CCG":"P","ACU":"T","ACC":"T","ACA":"T","ACG":"T","GCU":"A","GCC":"A","GCA":"A","GCG":"A","UAU":"Y","UAC":"Y","UAA":"*","UAG":"*","CAU":"H","CAC":"H","CAA":"Q","CAG":"Q","AAU":"N","AAC":"N","AAA":"K","AAG":"K","GAU":"D","GAC":"D","GAA":"E","GAG":"E","UGU":"C","UGC":"C","UGA":"*","UGG":"W","CGU":"R","CGC":"R","CGA":"R","CGG":"R","AGU":"S","AGC":"S","AGA":"R","AGG":"R","GGU":"G","GGC":"G","GGA":"G","GGG":"G"}
        r = self.transcribe()
        return "".join(t.get(r[i:i+3], "?") for i in range(0, len(r)-2, 3))
    def reverse_complement(self) -> str:
        c = {"A":"T","T":"A","G":"C","C":"G","U":"A","N":"N"}
        return "".join(c.get(b, "N") for b in self.sequence.upper()[::-1])
    def find_motif(self, motif: str) -> List[int]:
        m = motif.upper()
        return [i for i in range(len(self.sequence)-len(m)+1) if self.sequence.upper()[i:i+len(m)] == m]
    def stats(self) -> Dict:
        return {"length": len(self.sequence), "gc": round(self.gc_content(), 3)}

def run():
    dna = DNAAnalyzer("ATGCGATCGATCGATCG")
    print(dna.stats())

if __name__ == "__main__":
    run()
