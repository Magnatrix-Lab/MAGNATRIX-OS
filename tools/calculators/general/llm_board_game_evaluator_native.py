"""Native stdlib module: Board Game Evaluator
Evaluates board game positions by material count and positional factors.
"""
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class PieceValue:
    piece_name: str
    count: int
    value: float

@dataclass
class BoardGameEvaluator:
    game_name: str
    player_pieces: List[PieceValue] = field(default_factory=list)
    opponent_pieces: List[PieceValue] = field(default_factory=list)
    positional_score: float = 0.0

    def material_score(self, pieces: List[PieceValue]) -> float:
        return sum(p.count * p.value for p in pieces)

    def material_advantage(self) -> float:
        return self.material_score(self.player_pieces) - self.material_score(self.opponent_pieces)

    def total_pieces(self, pieces: List[PieceValue]) -> int:
        return sum(p.count for p in pieces)

    def piece_count_advantage(self) -> int:
        return self.total_pieces(self.player_pieces) - self.total_pieces(self.opponent_pieces)

    def total_score(self) -> float:
        return self.material_advantage() + self.positional_score

    def evaluation(self) -> str:
        score = self.total_score()
        if score > 3:
            return "winning"
        elif score > 0.5:
            return "better"
        elif score > -0.5:
            return "equal"
        elif score > -3:
            return "worse"
        return "losing"

    def stats(self) -> Dict:
        return {
            "game": self.game_name,
            "material_advantage": round(self.material_advantage(), 2),
            "piece_count_advantage": self.piece_count_advantage(),
            "positional_score": round(self.positional_score, 2),
            "total_score": round(self.total_score(), 2),
            "evaluation": self.evaluation(),
        }

def run():
    bge = BoardGameEvaluator(
        game_name="Chess",
        player_pieces=[
            PieceValue("pawn", 8, 1),
            PieceValue("knight", 2, 3),
            PieceValue("bishop", 2, 3),
            PieceValue("rook", 2, 5),
            PieceValue("queen", 1, 9),
        ],
        opponent_pieces=[
            PieceValue("pawn", 7, 1),
            PieceValue("knight", 2, 3),
            PieceValue("bishop", 1, 3),
            PieceValue("rook", 2, 5),
            PieceValue("queen", 1, 9),
        ],
        positional_score=0.5
    )
    print(bge.stats())

if __name__ == "__main__":
    run()
