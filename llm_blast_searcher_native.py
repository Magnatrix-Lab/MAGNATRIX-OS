"""BLAST Searcher — seed-and-extend, scoring, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum, auto

class BLASTSearcher:
    def __init__(self, word_size: int = 3, match: int = 1, mismatch: int = -1):
        self.word_size = word_size
        self.match = match
        self.mismatch = mismatch

    def _word_index(self, query: str) -> Dict[str, List[int]]:
        index = {}
        for i in range(len(query) - self.word_size + 1):
            word = query[i:i+self.word_size]
            if word not in index:
                index[word] = []
            index[word].append(i)
        return index

    def _extend(self, query: str, subject: str, q_start: int, s_start: int) -> Tuple[int, int, int]:
        score = 0
        # Extend right
        q_pos, s_pos = q_start, s_start
        while q_pos < len(query) and s_pos < len(subject):
            if query[q_pos] == subject[s_pos]:
                score += self.match
            else:
                score += self.mismatch
            q_pos += 1
            s_pos += 1
        # Extend left
        q_pos, s_pos = q_start - 1, s_start - 1
        while q_pos >= 0 and s_pos >= 0:
            if query[q_pos] == subject[s_pos]:
                score += self.match
            else:
                score += self.mismatch
            q_pos -= 1
            s_pos -= 1
        return q_start - q_pos - 1, s_start - s_pos - 1, score

    def search(self, query: str, database: List[str]) -> List[Dict]:
        word_index = self._word_index(query)
        hits = []
        for seq_id, seq in enumerate(database):
            for i in range(len(seq) - self.word_size + 1):
                word = seq[i:i+self.word_size]
                if word in word_index:
                    for q_pos in word_index[word]:
                        q_start, s_start, score = self._extend(query, seq, q_pos, i)
                        hits.append({"seq_id": seq_id, "score": score, "q_start": q_start, "s_start": s_start})
        hits.sort(key=lambda x: x["score"], reverse=True)
        return hits[:10]

    def stats(self) -> Dict:
        return {"word_size": self.word_size, "match": self.match, "mismatch": self.mismatch}

def run():
    blast = BLASTSearcher(3, 1, -1)
    query = "GATTACA"
    db = ["GCATGCU", "GATTAGA", "ATCGATC", "GATTACAATC"]
    hits = blast.search(query, db)
    for h in hits[:3]:
        print(h)
    print(blast.stats())

if __name__ == "__main__":
    run()
