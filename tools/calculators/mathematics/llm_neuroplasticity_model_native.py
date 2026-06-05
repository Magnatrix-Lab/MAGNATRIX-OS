"""Neuroplasticity Model — Hebbian, STDP, synaptic weight update, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class Synapse:
    pre: int
    post: int
    weight: float
    last_pre: float = 0.0
    last_post: float = 0.0

@dataclass
class NeuroplasticityModel:
    synapses: List[Synapse] = field(default_factory=list)
    tau: float = 20.0
    A_plus: float = 0.01
    A_minus: float = -0.01

    def hebbian_update(self, pre_rate: float, post_rate: float, lr: float = 0.001):
        for syn in self.synapses:
            syn.weight += lr * pre_rate * post_rate
            syn.weight = max(0, min(1, syn.weight))

    def stdp_update(self, syn: Synapse, pre_time: float, post_time: float):
        dt = post_time - pre_time
        if dt > 0:
            syn.weight += self.A_plus * math.exp(-dt / self.tau)
        else:
            syn.weight += self.A_minus * math.exp(dt / self.tau)
        syn.weight = max(0, min(1, syn.weight))

    def homeostatic_scale(self, target: float = 0.5):
        mean_w = sum(s.weight for s in self.synapses) / len(self.synapses) if self.synapses else 0
        for syn in self.synapses:
            syn.weight *= target / mean_w if mean_w > 0 else 1
            syn.weight = max(0, min(1, syn.weight))

    def stats(self) -> Dict:
        if not self.synapses:
            return {}
        w = [s.weight for s in self.synapses]
        return {"synapses": len(w), "mean_weight": sum(w)/len(w), "min": min(w), "max": max(w)}

def run():
    nm = NeuroplasticityModel([Synapse(0,1,0.3), Synapse(0,2,0.5)])
    nm.hebbian_update(10, 10)
    nm.stdp_update(nm.synapses[0], 0, 5)
    print(nm.stats())

if __name__ == "__main__":
    run()
