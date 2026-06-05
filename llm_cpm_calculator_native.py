"""Native stdlib module: CPM Calculator
Calculates cost per mille, CPC, and ROAS for ad campaigns.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class CPMCalculator:
    campaign_name: str
    spend_usd: float
    impressions: int
    clicks: int
    conversions: int
    revenue_usd: float = 0

    def cpm(self) -> float:
        if self.impressions == 0:
            return 0.0
        return (self.spend_usd / self.impressions) * 1000

    def cpc(self) -> float:
        if self.clicks == 0:
            return 0.0
        return self.spend_usd / self.clicks

    def ctr_pct(self) -> float:
        if self.impressions == 0:
            return 0.0
        return (self.clicks / self.impressions) * 100

    def conversion_rate_pct(self) -> float:
        if self.clicks == 0:
            return 0.0
        return (self.conversions / self.clicks) * 100

    def cost_per_conversion(self) -> float:
        if self.conversions == 0:
            return 0.0
        return self.spend_usd / self.conversions

    def roas(self) -> float:
        if self.spend_usd == 0:
            return 0.0
        return self.revenue_usd / self.spend_usd

    def roi_pct(self) -> float:
        if self.spend_usd == 0:
            return 0.0
        return ((self.revenue_usd - self.spend_usd) / self.spend_usd) * 100

    def stats(self) -> Dict:
        return {
            "campaign": self.campaign_name,
            "spend_usd": self.spend_usd,
            "cpm": round(self.cpm(), 2),
            "cpc": round(self.cpc(), 2),
            "ctr_pct": round(self.ctr_pct(), 2),
            "conversion_rate_pct": round(self.conversion_rate_pct(), 2),
            "cost_per_conversion": round(self.cost_per_conversion(), 2),
            "roas": round(self.roas(), 2),
            "roi_pct": round(self.roi_pct(), 2),
        }

def run():
    cpm = CPMCalculator(campaign_name="SummerSale", spend_usd=5000, impressions=1000000, clicks=25000, conversions=500, revenue_usd=15000)
    print(cpm.stats())

if __name__ == "__main__":
    run()
