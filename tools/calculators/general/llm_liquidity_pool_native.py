"""Native stdlib module: Liquidity Pool Calculator
Calculates DEX liquidity pool shares, impermanent loss, and fees.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class LiquidityPoolCalculator:
    token_a_reserve: float
    token_b_reserve: float
    user_token_a: float
    user_token_b: float
    fee_pct: float = 0.3

    def pool_constant(self) -> float:
        return self.token_a_reserve * self.token_b_reserve

    def pool_share_pct(self) -> float:
        total_a = self.token_a_reserve + self.user_token_a
        if total_a == 0:
            return 0.0
        return (self.user_token_a / total_a) * 100

    def token_a_price_in_b(self) -> float:
        if self.token_a_reserve == 0:
            return 0.0
        return self.token_b_reserve / self.token_a_reserve

    def token_b_price_in_a(self) -> float:
        if self.token_b_reserve == 0:
            return 0.0
        return self.token_a_reserve / self.token_b_reserve

    def swap_output(self, token_a_in: float) -> float:
        if self.token_a_reserve == 0 or self.token_b_reserve == 0:
            return 0.0
        fee = token_a_in * (self.fee_pct / 100)
        effective_in = token_a_in - fee
        new_a = self.token_a_reserve + effective_in
        new_b = self.pool_constant() / new_a
        return self.token_b_reserve - new_b

    def impermanent_loss_pct(self, price_ratio_change: float) -> float:
        if price_ratio_change == 0:
            return 0.0
        r = price_ratio_change
        return ((2 * math.sqrt(r)) / (1 + r) - 1) * 100

    def fee_earnings_annual_pct(self, volume_daily: float) -> float:
        total_pool = self.token_a_reserve * self.token_a_price_in_b() + self.token_b_reserve
        if total_pool == 0:
            return 0.0
        annual_volume = volume_daily * 365
        fees = annual_volume * (self.fee_pct / 100)
        return (fees / total_pool) * 100

    def stats(self, price_ratio_change: float = 0, volume_daily: float = 0) -> Dict:
        return {
            "pool_share_pct": round(self.pool_share_pct(), 4),
            "token_a_price_in_b": round(self.token_a_price_in_b(), 6),
            "token_b_price_in_a": round(self.token_b_price_in_a(), 6),
            "impermanent_loss_pct": round(self.impermanent_loss_pct(price_ratio_change), 2) if price_ratio_change else None,
            "fee_earnings_annual_pct": round(self.fee_earnings_annual_pct(volume_daily), 2) if volume_daily else None,
        }

def run():
    lpc = LiquidityPoolCalculator(token_a_reserve=1000, token_b_reserve=50000, user_token_a=100, user_token_b=5000, fee_pct=0.3)
    print(lpc.stats(price_ratio_change=2, volume_daily=100000))

if __name__ == "__main__":
    run()
