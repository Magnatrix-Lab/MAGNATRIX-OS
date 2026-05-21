#!/usr/bin/env python3
"""context-stats Adapter — Token/Cost Monitor for MAGNATRIX"""

import time
from datetime import datetime

class ContextStatsAdapter:
    def __init__(self):
        self.requests = []
        self.zones = {"planning": 0, "code": 0, "critical": 0}

    def track(self, brain, model, tokens, latency_ms):
        self.requests.append({
            "timestamp": datetime.now().isoformat(),
            "brain": brain, "model": model, "tokens": tokens, "latency_ms": latency_ms
        })
        zone = "planning" if tokens < 1000 else "code" if tokens < 3000 else "critical"
        self.zones[zone] += 1

    def statusline(self, brain="HERMES"):
        reqs = len([r for r in self.requests if r["brain"] == brain])
        avg_lat = sum(r["latency_ms"] for r in self.requests if r["brain"] == brain) / reqs if reqs else 0
        total_tokens = sum(r["tokens"] for r in self.requests if r["brain"] == brain)
        print(f"{brain} | reqs={reqs} | avg_lat={avg_lat:.0f}ms | tokens={total_tokens} | zones={self.zones}")

if __name__ == "__main__":
    stats = ContextStatsAdapter()
    stats.track("HERMES", "llama3", 500, 120)
    stats.track("GQRIS", "codellama", 2000, 200)
    stats.track("KIMI_CLAW", "mistral", 3500, 300)
    stats.statusline("HERMES")
