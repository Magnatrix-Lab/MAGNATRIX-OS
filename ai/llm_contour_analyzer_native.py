"""Contour Analyzer - Contour tracing for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Set, Tuple
from collections import deque

@dataclass
class ContourAnalyzer:
    connectivity: int = 4

    def find_contours(self, binary: List[List[int]]) -> List[List[Tuple[int,int]]]:
        h, w = len(binary), len(binary[0])
        visited = [[False]*w for _ in range(h)]
        contours = []
        for i in range(h):
            for j in range(w):
                if binary[i][j] > 0 and not visited[i][j]:
                    contour = self._flood_fill(binary, i, j, visited)
                    contours.append(contour)
        return contours

    def _flood_fill(self, binary, si, sj, visited) -> List[Tuple[int,int]]:
        h, w = len(binary), len(binary[0])
        queue = deque([(si,sj)]); visited[si][sj] = True; contour = []
        dirs = [(-1,0),(1,0),(0,-1),(0,1)] if self.connectivity == 4 else [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]
        while queue:
            i,j = queue.popleft(); contour.append((i,j))
            for di,dj in dirs:
                ni,nj = i+di,j+dj
                if 0<=ni<h and 0<=nj<w and not visited[ni][nj] and binary[ni][nj]>0:
                    visited[ni][nj] = True; queue.append((ni,nj))
        return contour

    def stats(self, binary: List[List[int]]) -> dict:
        contours = self.find_contours(binary)
        return {"contours": len(contours), "largest": max(len(c) for c in contours) if contours else 0}

def run():
    binary = [[0,0,0,0,0],[0,1,1,0,0],[0,1,1,0,0],[0,0,0,1,1],[0,0,0,1,1]]
    ca = ContourAnalyzer()
    print("Contours:", len(ca.find_contours(binary)))
    print("Stats:", ca.stats(binary))

if __name__ == "__main__": run()
