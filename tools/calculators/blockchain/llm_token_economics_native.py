"""Token Economics — supply, demand, inflation, staking, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

class TokenType(Enum):
    UTILITY = auto()
    GOVERNANCE = auto()
    STABLE = auto()
    NFT = auto()

@dataclass
class Tokenomics:
    total_supply: float
    circulating_supply: float
    max_supply: float
    inflation_rate: float
    burn_rate: float
    staking_reward: float

class TokenEconomics:
    def __init__(self, tokenomics: Tokenomics):
        self.tokenomics = tokenomics
        self.holders: Dict[str, float] = {}
        self.staked: Dict[str, float] = {}
        self.history: List[Dict] = []

    def mint(self, amount: float):
        if self.tokenomics.total_supply + amount <= self.tokenomics.max_supply:
            self.tokenomics.total_supply += amount
            self.tokenomics.circulating_supply += amount

    def burn(self, amount: float):
        self.tokenomics.total_supply -= amount
        self.tokenomics.circulating_supply -= amount

    def transfer(self, from_addr: str, to_addr: str, amount: float) -> bool:
        if self.holders.get(from_addr, 0) >= amount:
            self.holders[from_addr] -= amount
            self.holders[to_addr] = self.holders.get(to_addr, 0) + amount
            return True
        return False

    def stake(self, addr: str, amount: float) -> bool:
        if self.holders.get(addr, 0) >= amount:
            self.holders[addr] -= amount
            self.staked[addr] = self.staked.get(addr, 0) + amount
            return True
        return False

    def distribute_rewards(self):
        total_staked = sum(self.staked.values())
        if total_staked == 0:
            return
        reward_per_token = self.tokenomics.staking_reward / total_staked
        for addr, amount in self.staked.items():
            reward = amount * reward_per_token
            self.holders[addr] = self.holders.get(addr, 0) + reward
            self.tokenomics.circulating_supply += reward
            self.tokenomics.total_supply += reward

    def get_apr(self) -> float:
        total_staked = sum(self.staked.values())
        if total_staked == 0:
            return 0.0
        return (self.tokenomics.staking_reward / total_staked) * 100

    def stats(self) -> Dict:
        return {"total": self.tokenomics.total_supply, "circulating": self.tokenomics.circulating_supply, "holders": len(self.holders), "staked": sum(self.staked.values()), "apr": self.get_apr()}

def run():
    tok = Tokenomics(total_supply=1000000, circulating_supply=500000, max_supply=10000000, inflation_rate=0.05, burn_rate=0.01, staking_reward=10000)
    econ = TokenEconomics(tok)
    econ.holders["Alice"] = 1000
    econ.holders["Bob"] = 500
    econ.stake("Alice", 200)
    econ.stake("Bob", 100)
    econ.distribute_rewards()
    print(econ.stats())

if __name__ == "__main__":
    run()
