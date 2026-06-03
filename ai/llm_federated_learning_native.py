#!/usr/bin/env python3
"""
MAGNATRIX-OS — Federated Learning Engine
ai/llm_federated_learning_native.py

Features:
- Client node simulation (local training, gradient computation)
- Aggregation server (FedAvg, weighted averaging)
- Model distribution and parameter syncing
- Differential privacy simulation (noise injection)
- Client selection and participation tracking

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("federated_learning")


@dataclass
class ClientNode:
    id: str
    data_size: int
    local_weights: Dict[str, float] = field(default_factory=dict)
    gradient: Dict[str, float] = field(default_factory=dict)
    participation_count: int = 0


@dataclass
class FederatedRound:
    round_num: int
    client_weights: Dict[str, Dict[str, float]]
    aggregated_weights: Dict[str, float]
    accuracy: float


class FederatedLearningEngine:
    """Federated learning with FedAvg aggregation."""

    def __init__(self, noise_scale: float = 0.01):
        self.noise_scale = noise_scale
        self._clients: Dict[str, ClientNode] = {}
        self._global_weights: Dict[str, float] = {}
        self._history: List[FederatedRound] = []
        self._round_num = 0

    def register_client(self, client: ClientNode) -> None:
        self._clients[client.id] = client

    def initialize_global(self, weights: Dict[str, float]) -> None:
        self._global_weights = weights.copy()
        for client in self._clients.values():
            client.local_weights = weights.copy()

    def distribute(self) -> None:
        """Send global model to all clients."""
        for client in self._clients.values():
            client.local_weights = self._global_weights.copy()

    def train_local(self, client_id: str, epochs: int = 1) -> Dict[str, float]:
        """Simulate local training by adding small perturbations."""
        client = self._clients.get(client_id)
        if not client:
            return {}
        client.participation_count += 1
        for key in client.local_weights:
            noise = random.gauss(0, self.noise_scale)
            client.local_weights[key] += noise
            client.gradient[key] = noise
        return client.local_weights

    def aggregate(self, selected_clients: List[str], strategy: str = "fedavg") -> Dict[str, float]:
        """Aggregate client weights."""
        total_data = sum(self._clients[cid].data_size for cid in selected_clients if cid in self._clients)
        aggregated = defaultdict(float)
        for cid in selected_clients:
            client = self._clients.get(cid)
            if not client:
                continue
            weight = client.data_size / max(total_data, 1)
            for key, val in client.local_weights.items():
                aggregated[key] += val * weight
        # Add differential privacy noise
        for key in aggregated:
            aggregated[key] += random.gauss(0, self.noise_scale * 0.1)
        self._global_weights = dict(aggregated)
        return self._global_weights

    def run_round(self, selected_clients: Optional[List[str]] = None) -> FederatedRound:
        self._round_num += 1
        clients = selected_clients or list(self._clients.keys())
        self.distribute()
        for cid in clients:
            self.train_local(cid)
        self.aggregate(clients)
        accuracy = 0.5 + min(self._round_num * 0.02, 0.45) + random.gauss(0, 0.01)
        round_result = FederatedRound(self._round_num, {cid: self._clients[cid].local_weights for cid in clients}, self._global_weights, accuracy)
        self._history.append(round_result)
        return round_result

    def get_stats(self) -> Dict[str, Any]:
        return {
            "clients": len(self._clients),
            "rounds": self._round_num,
            "global_weights": len(self._global_weights),
            "latest_accuracy": self._history[-1].accuracy if self._history else 0,
        }


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Federated Learning Engine")
    print("ai/llm_federated_learning_native.py")
    print("=" * 60)

    engine = FederatedLearningEngine(noise_scale=0.01)

    # Register clients
    for i in range(5):
        engine.register_client(ClientNode(f"client-{i}", data_size=random.randint(100, 500)))

    # Initialize global model
    engine.initialize_global({"w1": 0.5, "w2": 0.3, "b1": 0.1})

    # Run rounds
    for r in range(3):
        result = engine.run_round()
        print(f"\nRound {result.round_num}: accuracy={result.accuracy:.3f}")
        print(f"  Global weights: {result.aggregated_weights}")

    # Stats
    print(f"\n{engine.get_stats()}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
