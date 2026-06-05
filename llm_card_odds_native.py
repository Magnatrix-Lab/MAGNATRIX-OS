"""Native stdlib module: Card Odds Calculator
Calculates poker odds, hand probabilities, and deck composition.
"""
from dataclasses import dataclass, field
from typing import List, Dict
import math

@dataclass
class CardOddsCalculator:
    deck_size: int = 52
    cards_drawn: int = 0
    known_cards: List[str] = field(default_factory=list)

    def remaining_cards(self) -> int:
        return self.deck_size - len(self.known_cards)

    def _combinations(self, n: int, k: int) -> float:
        if k > n or k < 0:
            return 0.0
        return math.comb(n, k)

    def probability_of_card(self, rank: str, suit: str = None) -> float:
        remaining = self.remaining_cards()
        if remaining == 0:
            return 0.0
        if suit:
            count = 1
        else:
            count = 4
        for card in self.known_cards:
            if rank in card and (suit is None or suit in card):
                count -= 1
        return count / remaining

    def draw_probability(self, target_count: int, total_drawn: int) -> float:
        remaining = self.remaining_cards()
        if remaining < total_drawn:
            return 0.0
        favorable = self._combinations(remaining - target_count, total_drawn - target_count)
        total = self._combinations(remaining, total_drawn)
        if total == 0:
            return 0.0
        return favorable / total

    def outs_to_odds(self, outs: int, cards_to_come: int) -> float:
        remaining = self.remaining_cards()
        if remaining == 0:
            return 0.0
        non_outs = remaining - outs
        if non_outs == 0:
            return 1.0
        prob_miss = 1.0
        for i in range(cards_to_come):
            if remaining - i > 0:
                prob_miss *= (non_outs - i) / (remaining - i)
        return 1 - prob_miss

    def pot_odds_pct(self, call_amount: float, pot_size: float) -> float:
        if call_amount + pot_size == 0:
            return 0.0
        return (call_amount / (call_amount + pot_size)) * 100

    def stats(self, outs: int = 0, cards_to_come: int = 1) -> Dict:
        return {
            "remaining_cards": self.remaining_cards(),
            "cards_drawn": len(self.known_cards),
            "outs_probability": round(self.outs_to_odds(outs, cards_to_come), 4) if outs else None,
            "odds_against": round((1 - self.outs_to_odds(outs, cards_to_come)) / self.outs_to_odds(outs, cards_to_come), 2) if outs and self.outs_to_odds(outs, cards_to_come) > 0 else None,
        }

def run():
    coc = CardOddsCalculator(known_cards=["AH", "KH", "QH"], cards_drawn=3)
    print(coc.stats(outs=9, cards_to_come=2))

if __name__ == "__main__":
    run()
