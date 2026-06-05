"""Native stdlib module: Chess Rating Calculator
Calculates Elo rating changes, expected scores, and performance ratings.
"""
from dataclasses import dataclass, field
from typing import List, Dict
import math

@dataclass
class ChessGame:
    opponent_rating: float
    result: float  # 1 = win, 0.5 = draw, 0 = loss

@dataclass
class ChessRatingCalculator:
    current_rating: float
    k_factor: int = 20
    games: List[ChessGame] = field(default_factory=list)

    def expected_score(self, opponent_rating: float) -> float:
        return 1 / (1 + 10 ** ((opponent_rating - self.current_rating) / 400))

    def rating_change(self, game: ChessGame) -> float:
        expected = self.expected_score(game.opponent_rating)
        return self.k_factor * (game.result - expected)

    def total_rating_change(self) -> float:
        return sum(self.rating_change(g) for g in self.games)

    def new_rating(self) -> float:
        return self.current_rating + self.total_rating_change()

    def performance_rating(self) -> float:
        if not self.games:
            return self.current_rating
        total_score = sum(g.result for g in self.games)
        avg_opponent = sum(g.opponent_rating for g in self.games) / len(self.games)
        dp = 400 * math.log10(total_score / (len(self.games) - total_score)) if (len(self.games) - total_score) > 0 else 0
        return avg_opponent + dp

    def win_rate_pct(self) -> float:
        if not self.games:
            return 0.0
        return (sum(g.result for g in self.games) / len(self.games)) * 100

    def stats(self) -> Dict:
        return {
            "current_rating": self.current_rating,
            "new_rating": round(self.new_rating(), 1),
            "total_change": round(self.total_rating_change(), 1),
            "performance_rating": round(self.performance_rating(), 1),
            "win_rate_pct": round(self.win_rate_pct(), 1),
            "games_played": len(self.games),
        }

def run():
    crc = ChessRatingCalculator(
        current_rating=1500,
        k_factor=20,
        games=[
            ChessGame(1450, 1),
            ChessGame(1520, 0.5),
            ChessGame(1600, 0),
            ChessGame(1480, 1),
            ChessGame(1550, 1),
        ]
    )
    print(crc.stats())

if __name__ == "__main__":
    run()
