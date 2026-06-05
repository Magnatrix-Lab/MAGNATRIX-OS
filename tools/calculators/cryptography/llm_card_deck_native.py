"""Card Deck — shuffle, deal, hand evaluation, probability, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
import random

@dataclass
class CardDeck:
    suits: List[str] = field(default_factory=lambda: ["Hearts", "Diamonds", "Clubs", "Spades"])
    ranks: List[str] = field(default_factory=lambda: ["2","3","4","5","6","7","8","9","10","J","Q","K","A"])
    cards: List[Tuple[str, str]] = field(default_factory=list)

    def build(self):
        self.cards = [(s, r) for s in self.suits for r in self.ranks]

    def shuffle(self):
        random.shuffle(self.cards)

    def deal(self, num: int) -> List[Tuple[str, str]]:
        dealt = self.cards[:num]
        self.cards = self.cards[num:]
        return dealt

    def hand_value(self, hand: List[Tuple[str, str]]) -> int:
        values = {"2":2,"3":3,"4":4,"5":5,"6":6,"7":7,"8":8,"9":9,"10":10,"J":10,"Q":10,"K":10,"A":11}
        total = sum(values.get(r, 0) for s, r in hand)
        aces = sum(1 for s, r in hand if r == "A")
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        return total

    def poker_hand_rank(self, hand: List[Tuple[str, str]]) -> str:
        ranks = [r for s, r in hand]
        suits = [s for s, r in hand]
        rank_counts = {}
        for r in ranks:
            rank_counts[r] = rank_counts.get(r, 0) + 1
        counts = sorted(rank_counts.values(), reverse=True)
        flush = len(set(suits)) == 1
        if 4 in counts: return "four of a kind"
        if counts == [3, 2]: return "full house"
        if flush: return "flush"
        if 3 in counts: return "three of a kind"
        if counts == [2, 2, 1]: return "two pair"
        if 2 in counts: return "pair"
        return "high card"

    def stats(self) -> Dict:
        return {"cards": len(self.cards)}

def run():
    cd = CardDeck()
    cd.build()
    cd.shuffle()
    hand = cd.deal(5)
    print("Hand:", hand)
    print("Poker rank:", cd.poker_hand_rank(hand))
    print(cd.stats())

if __name__ == "__main__":
    run()
