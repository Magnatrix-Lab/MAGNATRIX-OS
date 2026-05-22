"""
infrastructure/resource-acquisition/profit_reinvestment.py
=============================================================
MAGNATRIX Autonomous Resource Acquisition Engine
Layer 8: Trading (extends BankrBot + the0)

Profit reinvestment loop: auto-scale infrastructure dari trading profits.
Resource acquisition, cost optimization, infrastructure scaling decisions.
"""

import asyncio, json, time, uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from collections import defaultdict

@dataclass
class InfrastructureNode:
    id: str = ""
    node_type: str = ""  # compute, storage, network
    cost_per_hour: float = 0.0
    capability_score: float = 0.0
    region: str = ""
    provider: str = ""  # hostinger, aws, gcp, azure, self-hosted
    status: str = "idle"  # idle, active, scaling, retiring

class ProfitReinvestmentEngine:
    """
    Autonomous resource acquisition loop.
    Trading profits -> infrastructure scaling -> more capacity -> more profits.
    """

    def __init__(self):
        self.wallet_balance: float = 0.0
        self.profit_history: List[float] = []
        self.infrastructure: Dict[str, InfrastructureNode] = {}
        self.reinvestment_rate: float = 0.7  # 70% of profits reinvested
        self.min_reserve: float = 100.0      # Minimum reserve in USD
        self._acquisition_log: List[Dict] = []

    def record_profit(self, amount: float):
        """Record trading profit/loss"""
        self.profit_history.append(amount)
        self.wallet_balance += amount
        if len(self.profit_history) > 100:
            self.profit_history = self.profit_history[-100:]

    def get_projected_profit(self, days: int = 7) -> float:
        """Project future profit dari moving average"""
        if not self.profit_history:
            return 0.0
        recent = self.profit_history[-min(30, len(self.profit_history)):]
        avg_daily = sum(recent) / len(recent)
        return avg_daily * days

    def should_scale(self) -> bool:
        """Determine if infrastructure should scale up"""
        available = self.wallet_balance - self.min_reserve
        if available <= 0:
            return False
        projected = self.get_projected_profit(7)
        # Scale jika projected profit covers new node cost dalam 30 days
        estimated_node_cost = 50.0 * 24 * 30  # $50/month equivalent
        return projected > estimated_node_cost * 0.5

    def scale_decision(self) -> Optional[Dict]:
        """Make scaling decision: what type of node to acquire"""
        if not self.should_scale():
            return None

        available = self.wallet_balance - self.min_reserve
        reinvestment = available * self.reinvestment_rate

        # Determine node type based on current bottleneck
        node_types = ["compute", "storage", "network"]
        current_counts = defaultdict(int)
        for node in self.infrastructure.values():
            current_counts[node.node_type] += 1

        # Scale the scarcest type
        min_type = min(node_types, key=lambda t: current_counts[t])

        decision = {
            "action": "acquire",
            "node_type": min_type,
            "budget_usd": reinvestment,
            "provider": "hostinger",  # Default, can be multi-cloud
            "region": "auto",
            "timestamp": time.time()
        }
        self._acquisition_log.append(decision)
        self.wallet_balance -= reinvestment
        return decision

    def add_node(self, node: InfrastructureNode):
        """Add acquired infrastructure node"""
        self.infrastructure[node.id] = node

    def retire_node(self, node_id: str) -> bool:
        """Retire underutilized node"""
        node = self.infrastructure.get(node_id)
        if node:
            node.status = "retiring"
            return True
        return False

    def get_utilization(self) -> Dict:
        """Get infrastructure utilization metrics"""
        total = len(self.infrastructure)
        active = sum(1 for n in self.infrastructure.values() if n.status == "active")
        total_cost = sum(n.cost_per_hour for n in self.infrastructure.values())
        return {
            "total_nodes": total,
            "active": active,
            "utilization_rate": active / max(total, 1),
            "hourly_cost": total_cost,
            "monthly_estimated": total_cost * 24 * 30,
            "wallet_balance": self.wallet_balance
        }

    def get_status(self) -> Dict:
        return {
            "wallet": self.wallet_balance,
            "infrastructure_nodes": len(self.infrastructure),
            "profit_history_len": len(self.profit_history),
            "projected_weekly_profit": self.get_projected_profit(7),
            "acquisitions": len(self._acquisition_log)
        }


if __name__ == "__main__":
    async def demo():
        engine = ProfitReinvestmentEngine()

        # Simulate profits
        for _ in range(10):
            engine.record_profit(150.0)

        print(f"Wallet: ${engine.wallet_balance:.2f}")
        print(f"Should scale: {engine.should_scale()}")

        decision = engine.scale_decision()
        print(f"Scale decision: {decision}")
        print(f"Status: {engine.get_status()}")

    asyncio.run(demo())
