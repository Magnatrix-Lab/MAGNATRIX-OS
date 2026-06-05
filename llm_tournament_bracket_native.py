"""Native stdlib module: Tournament Bracket Calculator
Manages tournament brackets, seeding, and elimination formats.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class TournamentType(Enum):
    SINGLE_ELIMINATION = "single_elimination"
    DOUBLE_ELIMINATION = "double_elimination"
    ROUND_ROBIN = "round_robin"
    SWISS = "swiss"

@dataclass
class TournamentBracketCalculator:
    tournament_name: str
    num_participants: int
    tournament_type: TournamentType

    def rounds_needed(self) -> int:
        if self.tournament_type == TournamentType.SINGLE_ELIMINATION:
            import math
            return math.ceil(math.log2(self.num_participants))
        elif self.tournament_type == TournamentType.DOUBLE_ELIMINATION:
            import math
            return 2 * math.ceil(math.log2(self.num_participants)) - 1
        elif self.tournament_type == TournamentType.ROUND_ROBIN:
            return self.num_participants - 1
        elif self.tournament_type == TournamentType.SWISS:
            return max(3, math.ceil(math.log2(self.num_participants)))
        return 0

    def total_matches(self) -> int:
        if self.tournament_type == TournamentType.SINGLE_ELIMINATION:
            return self.num_participants - 1
        elif self.tournament_type == TournamentType.DOUBLE_ELIMINATION:
            return 2 * self.num_participants - 2
        elif self.tournament_type == TournamentType.ROUND_ROBIN:
            return (self.num_participants * (self.num_participants - 1)) // 2
        elif self.tournament_type == TournamentType.SWISS:
            return self.num_participants * self.rounds_needed() // 2
        return 0

    def byes_needed(self) -> int:
        import math
        next_power = 2 ** math.ceil(math.log2(self.num_participants))
        return next_power - self.num_participants

    def seeded_matchups(self) -> List[tuple]:
        matchups = []
        for i in range(1, self.num_participants // 2 + 1):
            high = self.num_participants - i + 1
            matchups.append((i, high))
        return matchups

    def stats(self) -> Dict:
        return {
            "tournament": self.tournament_name,
            "type": self.tournament_type.value,
            "participants": self.num_participants,
            "rounds": self.rounds_needed(),
            "total_matches": self.total_matches(),
            "byes": self.byes_needed(),
            "seeded_matchups": self.seeded_matchups(),
        }

def run():
    tbc = TournamentBracketCalculator(tournament_name="Spring Championship", num_participants=16, tournament_type=TournamentType.SINGLE_ELIMINATION)
    print(tbc.stats())

if __name__ == "__main__":
    run()
