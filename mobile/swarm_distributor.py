#!/usr/bin/env python3
"""Swarm Task Distributor"""

class SwarmDistributor:
    def route(self, task, local_cpu=50):
        if local_cpu > 80:
            return {"action": "offload", "target": "edge-002"}
        return {"action": "local"}

if __name__ == "__main__":
    d = SwarmDistributor()
    print(d.route("heavy", 85))
    print(d.route("light", 40))
