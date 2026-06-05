"""Cart Abandonment — recovery, probability, triggers, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class CartAbandonment:
    abandonment_rate: float = 0.7
    recovery_rate: float = 0.15
    avg_cart_value: float = 100.0

    def lost_revenue(self, total_carts: int) -> float:
        return total_carts * self.abandonment_rate * self.avg_cart_value

    def recoverable_revenue(self, total_carts: int) -> float:
        return self.lost_revenue(total_carts) * self.recovery_rate

    def email_effectiveness(self, emails_sent: int, recovered: int) -> float:
        return recovered / emails_sent if emails_sent > 0 else 0.0

    def optimal_send_time(self, abandon_times: List[float]) -> float:
        if not abandon_times:
            return 1.0
        return sum(abandon_times) / len(abandon_times)

    def trigger_probability(self, steps_completed: int, total_steps: int) -> float:
        if total_steps == 0:
            return 0.0
        return 1 - (steps_completed / total_steps) ** 2

    def stats(self, total_carts: int) -> Dict:
        return {"lost": round(self.lost_revenue(total_carts), 2), "recoverable": round(self.recoverable_revenue(total_carts), 2), "recovery_rate": self.recovery_rate}

def run():
    ca = CartAbandonment(abandonment_rate=0.75, recovery_rate=0.2, avg_cart_value=150)
    print(ca.stats(1000))
    print("Trigger prob 2/5:", ca.trigger_probability(2, 5))

if __name__ == "__main__":
    run()
