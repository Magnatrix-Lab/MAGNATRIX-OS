#!/usr/bin/env python3
"""Self-Healing Node"""

import random

class SelfHealing:
    def check(self):
        results = []
        battery = random.uniform(10, 100)
        if battery < 20:
            results.append({"issue": "low_battery", "action": "reduce_polling", "to": 300})
        memory = random.uniform(70, 98)
        if memory > 90:
            results.append({"issue": "high_memory", "action": "clear_cache"})
        return results

if __name__ == "__main__":
    h = SelfHealing()
    for i in h.check():
        print(f"🔧 {i['issue']} → {i['action']}")
