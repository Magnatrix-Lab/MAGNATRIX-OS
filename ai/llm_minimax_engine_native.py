"""Minimax Engine - Adversarial search for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from enum import Enum, auto

@dataclass
class GameState:
    board: List[int] = field(default_factory=list)
    player: int = 1

@dataclass
class MinimaxEngine:
    depth_limit: int = 3

    def evaluate(self, state: GameState) -> int:
        return sum(state.board) * state.player

    def minimax(self, state: GameState, depth: int, is_maximizing: bool) -> Tuple[int, Optional[int]]:
        if depth == 0 or len(state.board) >= 9:
            return self.evaluate(state), None
        if is_maximizing:
            best_score = float('-inf')
            best_move = None
            for i in range(9):
                if i not in state.board:
                    new_state = GameState(state.board + [i], state.player)
                    score, _ = self.minimax(new_state, depth - 1, False)
                    if score > best_score:
                        best_score = score
                        best_move = i
            return best_score, best_move
        else:
            best_score = float('inf')
            best_move = None
            for i in range(9):
                if i not in state.board:
                    new_state = GameState(state.board + [i], -state.player)
                    score, _ = self.minimax(new_state, depth - 1, True)
                    if score < best_score:
                        best_score = score
                        best_move = i
            return best_score, best_move

    def stats(self, state: GameState) -> dict:
        score, move = self.minimax(state, self.depth_limit, True)
        return {"score": score, "best_move": move, "depth": self.depth_limit}

def run():
    me = MinimaxEngine(2)
    state = GameState([0, 1, 4], 1)
    print("Stats:", me.stats(state))

if __name__ == "__main__": run()
