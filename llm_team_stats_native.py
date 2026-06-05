"""Native stdlib module: Team Stats Analyzer
Analyzes team performance stats like win rate, goal differential, and efficiency.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class GameResult:
    opponent: str
    team_score: int
    opponent_score: int
    home: bool = True

@dataclass
class TeamStatsAnalyzer:
    team_name: str
    season: str
    games: List[GameResult] = field(default_factory=list)

    def wins(self) -> int:
        return sum(1 for g in self.games if g.team_score > g.opponent_score)

    def losses(self) -> int:
        return sum(1 for g in self.games if g.team_score < g.opponent_score)

    def draws(self) -> int:
        return sum(1 for g in self.games if g.team_score == g.opponent_score)

    def win_rate_pct(self) -> float:
        if not self.games:
            return 0.0
        return (self.wins() / len(self.games)) * 100

    def goal_differential(self) -> int:
        return sum(g.team_score - g.opponent_score for g in self.games)

    def goals_for(self) -> int:
        return sum(g.team_score for g in self.games)

    def goals_against(self) -> int:
        return sum(g.opponent_score for g in self.games)

    def home_win_rate_pct(self) -> float:
        home_games = [g for g in self.games if g.home]
        if not home_games:
            return 0.0
        return (sum(1 for g in home_games if g.team_score > g.opponent_score) / len(home_games)) * 100

    def stats(self) -> Dict:
        return {
            "team": self.team_name,
            "season": self.season,
            "games": len(self.games),
            "wins": self.wins(),
            "losses": self.losses(),
            "draws": self.draws(),
            "win_rate_pct": round(self.win_rate_pct(), 1),
            "goal_differential": self.goal_differential(),
            "goals_for": self.goals_for(),
            "goals_against": self.goals_against(),
            "home_win_rate_pct": round(self.home_win_rate_pct(), 1),
        }

def run():
    tsa = TeamStatsAnalyzer(
        team_name="Lions FC",
        season="2024",
        games=[
            GameResult("Tigers", 3, 1, True),
            GameResult("Bears", 1, 2, False),
            GameResult("Wolves", 2, 2, True),
            GameResult("Eagles", 4, 0, False),
            GameResult("Sharks", 1, 1, True),
        ]
    )
    print(tsa.stats())

if __name__ == "__main__":
    run()
