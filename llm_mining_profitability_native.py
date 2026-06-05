"""Native stdlib module: Mining Profitability Calculator
Calculates mining profitability by hashrate, difficulty, and electricity costs.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class MiningProfitabilityCalculator:
    hashrate_th_s: float
    network_difficulty: float
    block_reward: float
    electricity_cost_per_kwh: float
    power_consumption_w: float
    pool_fee_pct: float = 2.0
    hardware_cost_usd: float = 0.0

    def daily_blocks(self) -> float:
        if self.network_difficulty == 0:
            return 0.0
        seconds_per_day = 86400
        hash_per_block = self.network_difficulty * 2**32
        return (self.hashrate_th_s * 1e12 * seconds_per_day) / hash_per_block

    def daily_revenue_coins(self) -> float:
        return self.daily_blocks() * self.block_reward * (1 - self.pool_fee_pct / 100)

    def daily_power_cost_usd(self) -> float:
        kwh_per_day = (self.power_consumption_w * 24) / 1000
        return kwh_per_day * self.electricity_cost_per_kwh

    def daily_profit_usd(self, coin_price_usd: float) -> float:
        return self.daily_revenue_coins() * coin_price_usd - self.daily_power_cost_usd()

    def payback_period_days(self, coin_price_usd: float) -> float:
        daily_profit = self.daily_profit_usd(coin_price_usd)
        if daily_profit <= 0:
            return float('inf')
        return self.hardware_cost_usd / daily_profit

    def efficiency_j_th(self) -> float:
        if self.hashrate_th_s == 0:
            return 0.0
        return self.power_consumption_w / self.hashrate_th_s

    def stats(self, coin_price_usd: float = 50000) -> Dict:
        return {
            "hashrate_th_s": self.hashrate_th_s,
            "daily_revenue_coins": round(self.daily_revenue_coins(), 6),
            "daily_power_cost_usd": round(self.daily_power_cost_usd(), 2),
            "daily_profit_usd": round(self.daily_profit_usd(coin_price_usd), 2),
            "payback_days": round(self.payback_period_days(coin_price_usd), 1) if self.payback_period_days(coin_price_usd) != float('inf') else "inf",
            "efficiency_j_th": round(self.efficiency_j_th(), 2),
        }

def run():
    mpc = MiningProfitabilityCalculator(hashrate_th_s=100, network_difficulty=50e15, block_reward=6.25, electricity_cost_per_kwh=0.1, power_consumption_w=3000, pool_fee_pct=2, hardware_cost_usd=5000)
    print(mpc.stats(coin_price_usd=60000))

if __name__ == "__main__":
    run()
