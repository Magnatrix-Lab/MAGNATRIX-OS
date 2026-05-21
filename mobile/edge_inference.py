#!/usr/bin/env python3
"""Edge Inference"""

import time

class EdgeInference:
    def infer(self, prompt):
        start = time.perf_counter()
        result = f"Edge: {prompt[:20]}..."
        latency = (time.perf_counter() - start) * 1000
        return {"result": result, "latency_ms": latency}

if __name__ == "__main__":
    e = EdgeInference()
    r = e.infer("Hello world")
    print(f"{r['latency_ms']:.2f}ms | {r['result']}")
