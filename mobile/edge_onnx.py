#!/usr/bin/env python3
"""Edge ONNX Inference"""

import time

class EdgeONNX:
    def infer(self, vec):
        start = time.perf_counter()
        out = [sum(x * 0.5 for x in vec)]
        latency = (time.perf_counter() - start) * 1000
        return {"output": out, "latency_ms": latency}

if __name__ == "__main__":
    o = EdgeONNX()
    r = o.infer([1.0, 2.0, 3.0])
    print(f"{r['latency_ms']:.3f}ms | {r['output']}")
