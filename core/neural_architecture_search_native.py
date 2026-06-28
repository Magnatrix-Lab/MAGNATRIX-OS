#!/usr/bin/env python3
"""Neural Architecture Search for MAGNATRIX-OS."""
from __future__ import annotations
import random, time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

@dataclass
class ArchitectureSpec:
    arch_id: str
    layers: List[Dict[str, Any]] = field(default_factory=list)
    params_estimate: int = 0
    accuracy_proxy: float = 0.0
    def to_dict(self): return asdict(self)

class SearchSpace:
    def __init__(self):
        self.ops = ["conv3x3", "conv5x5", "dconv3x3", "maxpool", "avgpool", "skip", "none"]
    def sample_random(self):
        depth = random.randint(3, 15)
        layers = [{"op": random.choice(self.ops), "width": random.choice([16,32,64,128,256,512])} for _ in range(depth)]
        return ArchitectureSpec(arch_id=f"arch_{int(time.time())}_{random.randint(1000,9999)}", layers=layers, params_estimate=sum(l["width"]*9 for l in layers))
    def mutate(self, parent):
        child = [l.copy() for l in parent.layers]
        if child and random.random() < 0.3:
            child[random.randint(0, len(child)-1)]["op"] = random.choice(self.ops)
        return ArchitectureSpec(arch_id=f"arch_{int(time.time())}_{random.randint(1000,9999)}", layers=child, params_estimate=sum(l["width"]*9 for l in child))

class ProxyEvaluator:
    def evaluate(self, arch):
        depth = len(arch.layers)
        score = 1.0 - abs(depth - 8) / 8.0
        ops_used = set(l["op"] for l in arch.layers)
        score += len(ops_used) / 7 * 0.3
        skips = sum(1 for l in arch.layers if l["op"] == "skip")
        score += min(skips * 0.05, 0.2)
        return max(0.0, min(1.0, score))

class EvolutionSearcher:
    def __init__(self, pop_size=20, gens=10):
        self.pop_size = pop_size
        self.gens = gens
        self.space = SearchSpace()
        self.evaluator = ProxyEvaluator()
        self.pop = []
        self.best = None
    def evolve(self):
        self.pop = [self.space.sample_random() for _ in range(self.pop_size)]
        for _ in range(self.gens):
            for a in self.pop: a.accuracy_proxy = self.evaluator.evaluate(a)
            self.pop.sort(key=lambda a: a.accuracy_proxy, reverse=True)
            self.best = self.pop[0]
            elites = self.pop[:self.pop_size//2]
            new_pop = elites.copy()
            while len(new_pop) < self.pop_size:
                new_pop.append(self.space.mutate(random.choice(elites)))
            self.pop = new_pop
        return self.best
    def get_stats(self):
        return {"population": len(self.pop), "generations": self.gens, "best_score": self.best.accuracy_proxy if self.best else 0}

class NeuralArchitectureSearch:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.searcher = EvolutionSearcher()
        self.history = []
    def search(self):
        best = self.searcher.evolve()
        self.history.append(best)
        return best
    def to_dict(self):
        return self.searcher.get_stats()
