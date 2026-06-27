#!/usr/bin/env python3
"""
Federated Learning for MAGNATRIX-OS
====================================
Distributed model training across swarm nodes without sharing raw data.
Gradient aggregation, differential privacy, model versioning. Pure stdlib.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations
import hashlib, json, random, time
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class GradientVector:
    """Represents model gradients as a simple vector."""
    layer_id: str
    values: List[float] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    node_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ModelUpdate:
    """A model update from a node."""
    update_id: str
    node_id: str
    model_version: str
    gradients: List[GradientVector] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    dataset_size: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["gradients"] = [g.to_dict() for g in self.gradients]
        return d


@dataclass
class ModelVersion:
    """Versioned model checkpoint."""
    version_id: str
    parent_version: str = ""
    aggregated_from: List[str] = field(default_factory=list)
    accuracy: float = 0.0
    loss: float = 0.0
    created_at: float = field(default_factory=time.time)
    gradient_checksum: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DifferentialPrivacy:
    """Adds differential privacy noise to gradients."""
    
    def __init__(self, epsilon: float = 1.0, delta: float = 1e-5, noise_scale: float = 0.01) -> None:
        self.epsilon = epsilon
        self.delta = delta
        self.noise_scale = noise_scale
    
    def clip(self, gradient: List[float], max_norm: float = 1.0) -> List[float]:
        """Clip gradient to max norm."""
        norm = sum(v**2 for v in gradient) ** 0.5
        if norm > max_norm and norm > 0:
            scale = max_norm / norm
            return [v * scale for v in gradient]
        return gradient
    
    def add_noise(self, gradient: List[float], sensitivity: float = 1.0) -> List[float]:
        """Add Gaussian noise for differential privacy."""
        noise_std = self.noise_scale * sensitivity / self.epsilon
        return [v + random.gauss(0, noise_std) for v in gradient]
    
    def privatize(self, gradient: List[float]) -> List[float]:
        """Apply both clipping and noise."""
        clipped = self.clip(gradient)
        return self.add_noise(clipped)


class LocalTrainer:
    """Trains model locally on a node's data."""
    
    def __init__(self, node_id: str, dp: DifferentialPrivacy) -> None:
        self.node_id = node_id
        self.dp = dp
        self.local_data: List[Dict[str, Any]] = []
        self.model_weights: Dict[str, List[float]] = {}
    
    def add_data(self, samples: List[Dict[str, Any]]) -> None:
        self.local_data.extend(samples)
    
    def compute_gradients(self) -> List[GradientVector]:
        """Simulate gradient computation on local data."""
        gradients = []
        for layer_id, weights in self.model_weights.items():
            # Simulate gradient: small random perturbation from current weights
            grads = [random.gauss(-w * 0.01, 0.05) for w in weights]
            grads = self.dp.privatize(grads)
            gradients.append(GradientVector(layer_id=layer_id, values=grads, node_id=self.node_id))
        return gradients
    
    def update_weights(self, aggregated_gradients: List[GradientVector], lr: float = 0.01) -> None:
        for grad in aggregated_gradients:
            if grad.layer_id in self.model_weights:
                self.model_weights[grad.layer_id] = [
                    w - lr * g for w, g in zip(self.model_weights[grad.layer_id], grad.values)
                ]


class GradientAggregator:
    """Aggregates gradients from multiple nodes."""
    
    def __init__(self) -> None:
        self.received_updates: List[ModelUpdate] = []
    
    def receive(self, update: ModelUpdate) -> None:
        self.received_updates.append(update)
    
    def aggregate_fedavg(self) -> List[GradientVector]:
        """Federated Averaging aggregation."""
        if not self.received_updates:
            return []
        
        # Group gradients by layer
        layer_grads: Dict[str, List[List[float]]] = {}
        weights: Dict[str, float] = {}
        
        for update in self.received_updates:
            weight = update.dataset_size
            for grad in update.gradients:
                if grad.layer_id not in layer_grads:
                    layer_grads[grad.layer_id] = []
                    weights[grad.layer_id] = 0.0
                layer_grads[grad.layer_id].append(grad.values)
                weights[grad.layer_id] += weight
        
        aggregated = []
        for layer_id, grad_list in layer_grads.items():
            total_weight = weights[layer_id]
            if total_weight == 0:
                continue
            avg_grad = []
            for i in range(len(grad_list[0])):
                weighted_sum = sum(g[i] * w for g, w in zip(grad_list, [u.dataset_size for u in self.received_updates]))
                avg_grad.append(weighted_sum / total_weight)
            aggregated.append(GradientVector(layer_id=layer_id, values=avg_grad))
        
        return aggregated
    
    def clear(self) -> None:
        self.received_updates = []


class ModelVersioning:
    """Manages model versions and lineage."""
    
    def __init__(self) -> None:
        self.versions: Dict[str, ModelVersion] = {}
        self._counter = 0
    
    def create_version(self, parent: str = "", node_ids: List[str] = None, accuracy: float = 0.0, loss: float = 0.0) -> ModelVersion:
        self._counter += 1
        version_id = f"v{self._counter}_{int(time.time())}"
        version = ModelVersion(
            version_id=version_id,
            parent_version=parent,
            aggregated_from=node_ids or [],
            accuracy=accuracy,
            loss=loss,
        )
        self.versions[version_id] = version
        return version
    
    def get_version(self, version_id: str) -> Optional[ModelVersion]:
        return self.versions.get(version_id)
    
    def get_lineage(self, version_id: str) -> List[str]:
        lineage = []
        current = version_id
        while current:
            lineage.append(current)
            v = self.versions.get(current)
            current = v.parent_version if v else ""
        return lineage
    
    def get_best_version(self) -> Optional[ModelVersion]:
        if not self.versions:
            return None
        return max(self.versions.values(), key=lambda v: v.accuracy)


class FederatedLearningEngine:
    """Top-level federated learning engine."""
    
    def __init__(self, model_id: str = "default") -> None:
        self.model_id = model_id
        self.dp = DifferentialPrivacy()
        self.aggregator = GradientAggregator()
        self.versioning = ModelVersioning()
        self.trainers: Dict[str, LocalTrainer] = {}
        self._round_counter = 0
        self.global_model: Dict[str, List[float]] = {}
    
    def register_node(self, node_id: str) -> None:
        self.trainers[node_id] = LocalTrainer(node_id, self.dp)
    
    def initialize_model(self, architecture: Dict[str, int]) -> None:
        """Initialize model weights."""
        for layer_id, size in architecture.items():
            self.global_model[layer_id] = [random.gauss(0, 0.01) for _ in range(size)]
        # Sync to all trainers
        for trainer in self.trainers.values():
            trainer.model_weights = {k: v.copy() for k, v in self.global_model.items()}
    
    def train_round(self, node_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Execute one federated training round."""
        self._round_counter += 1
        nodes = node_ids or list(self.trainers.keys())
        
        # Local training
        for node_id in nodes:
            trainer = self.trainers.get(node_id)
            if trainer:
                gradients = trainer.compute_gradients()
                update = ModelUpdate(
                    update_id=f"round{self._round_counter}_{node_id}",
                    node_id=node_id,
                    model_version=self.versioning.get_best_version().version_id if self.versioning.get_best_version() else "v0",
                    gradients=gradients,
                    dataset_size=len(trainer.local_data),
                )
                self.aggregator.receive(update)
        
        # Aggregate
        aggregated = self.aggregator.aggregate_fedavg()
        
        # Update global model
        for grad in aggregated:
            if grad.layer_id in self.global_model:
                self.global_model[grad.layer_id] = [
                    w - 0.01 * g for w, g in zip(self.global_model[grad.layer_id], grad.values)
                ]
        
        # Sync to all trainers
        for trainer in self.trainers.values():
            trainer.model_weights = {k: v.copy() for k, v in self.global_model.items()}
        
        # Create new version
        version = self.versioning.create_version(
            parent=self.versioning.get_best_version().version_id if self.versioning.get_best_version() else "",
            node_ids=nodes,
            accuracy=random.uniform(0.7, 0.95),  # Simulated
            loss=random.uniform(0.05, 0.3),
        )
        
        self.aggregator.clear()
        
        return {
            "round": self._round_counter,
            "version": version.version_id,
            "accuracy": version.accuracy,
            "loss": version.loss,
            "nodes_trained": len(nodes),
        }
    
    def get_global_model(self) -> Dict[str, List[float]]:
        return self.global_model
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "rounds": self._round_counter,
            "nodes": len(self.trainers),
            "versions": len(self.versioning.versions),
            "best_version": self.versioning.get_best_version().version_id if self.versioning.get_best_version() else None,
            "best_accuracy": self.versioning.get_best_version().accuracy if self.versioning.get_best_version() else 0.0,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()
