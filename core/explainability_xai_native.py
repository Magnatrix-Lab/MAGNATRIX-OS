#!/usr/bin/env python3
"""
Explainability / XAI for MAGNATRIX-OS
====================================
Decision tracing, attribution mapping, reasoning chain, confidence
visualization. Understand why agents make decisions. Pure stdlib.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations
import json, math, re, time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
from collections import OrderedDict


@dataclass
class DecisionStep:
    """A single step in a decision chain."""
    step_id: str
    module_name: str
    action: str
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    reasoning: str = ""
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AttributionWeight:
    """Weight attribution for a feature/input."""
    feature_name: str
    weight: float
    normalized_weight: float = 0.0
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ReasoningChain:
    """Traces the chain of reasoning leading to a decision."""
    
    def __init__(self, chain_id: str = "") -> None:
        self.chain_id = chain_id or f"chain_{int(time.time())}"
        self.steps: OrderedDict[str, DecisionStep] = OrderedDict()
        self._step_counter = 0
    
    def add_step(self, module_name: str, action: str, input_data: Dict[str, Any], output_data: Dict[str, Any], confidence: float = 0.0, reasoning: str = "") -> str:
        self._step_counter += 1
        step_id = f"{self.chain_id}_step_{self._step_counter}"
        step = DecisionStep(
            step_id=step_id,
            module_name=module_name,
            action=action,
            input_data=input_data,
            output_data=output_data,
            confidence=confidence,
            reasoning=reasoning,
        )
        self.steps[step_id] = step
        return step_id
    
    def get_chain(self) -> List[DecisionStep]:
        return list(self.steps.values())
    
    def get_final_decision(self) -> Optional[DecisionStep]:
        if not self.steps:
            return None
        return list(self.steps.values())[-1]
    
    def explain(self) -> str:
        """Generate human-readable explanation."""
        lines = [f"Decision Chain: {self.chain_id}", "=" * 50]
        for i, step in enumerate(self.steps.values(), 1):
            lines.append(f"\nStep {i}: {step.module_name}.{step.action}")
            lines.append(f"  Confidence: {step.confidence:.2%}")
            if step.reasoning:
                lines.append(f"  Reasoning: {step.reasoning}")
            lines.append(f"  Input: {json.dumps(step.input_data, default=str)[:100]}")
            lines.append(f"  Output: {json.dumps(step.output_data, default=str)[:100]}")
        final = self.get_final_decision()
        if final:
            lines.append(f"\nFinal Decision: {final.action} (confidence: {final.confidence:.2%})")
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "steps": [s.to_dict() for s in self.steps.values()],
            "final_confidence": self.get_final_decision().confidence if self.get_final_decision() else 0.0,
        }


class AttributionMapper:
    """Maps attribution weights to inputs."""
    
    def __init__(self) -> None:
        self.attributions: Dict[str, List[AttributionWeight]] = {}
    
    def compute_attribution(self, decision_id: str, inputs: Dict[str, float], output_delta: float) -> List[AttributionWeight]:
        """Compute attribution weights using simple gradient approximation."""
        weights = []
        total = sum(abs(v) for v in inputs.values()) if inputs else 0
        for feature_name, value in inputs.items():
            weight = value * output_delta
            normalized = abs(weight) / total if total > 0 else 0
            weights.append(AttributionWeight(
                feature_name=feature_name,
                weight=weight,
                normalized_weight=normalized,
                description=f"Input {feature_name} contributed {normalized:.2%}",
            ))
        weights.sort(key=lambda a: abs(a.normalized_weight), reverse=True)
        self.attributions[decision_id] = weights
        return weights
    
    def get_top_features(self, decision_id: str, top_k: int = 5) -> List[AttributionWeight]:
        weights = self.attributions.get(decision_id, [])
        return weights[:top_k]
    
    def explain_attribution(self, decision_id: str) -> str:
        weights = self.attributions.get(decision_id, [])
        if not weights:
            return "No attribution data available."
        lines = [f"Attribution Analysis for Decision: {decision_id}", "=" * 50]
        for i, w in enumerate(weights[:10], 1):
            direction = "↑" if w.weight > 0 else "↓"
            lines.append(f"{i}. {w.feature_name}: {abs(w.normalized_weight):.2%} {direction}")
        return "\n".join(lines)


class ConfidenceVisualizer:
    """Visualizes confidence levels across decisions."""
    
    def __init__(self) -> None:
        self.confidence_history: List[Tuple[float, float]] = []  # (timestamp, confidence)
    
    def record(self, confidence: float) -> None:
        self.confidence_history.append((time.time(), confidence))
    
    def get_confidence_trend(self, window: int = 10) -> Dict[str, Any]:
        if not self.confidence_history:
            return {"avg": 0, "min": 0, "max": 0, "trend": "flat"}
        recent = self.confidence_history[-window:]
        confs = [c for _, c in recent]
        avg = sum(confs) / len(confs)
        trend = "rising" if len(confs) > 1 and confs[-1] > confs[0] else "falling" if len(confs) > 1 and confs[-1] < confs[0] else "flat"
        return {
            "avg": round(avg, 3),
            "min": round(min(confs), 3),
            "max": round(max(confs), 3),
            "trend": trend,
            "samples": len(confs),
        }
    
    def ascii_chart(self, width: int = 40, height: int = 10) -> str:
        if not self.confidence_history:
            return "No confidence data."
        data = [c for _, c in self.confidence_history[-width:]]
        if not data:
            return "No data in window."
        min_val = min(data)
        max_val = max(data)
        range_val = max_val - min_val if max_val != min_val else 1
        lines = ["Confidence Trend"]
        lines.append("-" * width)
        for h in range(height, 0, -1):
            threshold = min_val + (h - 1) / height * range_val
            row = ""
            for val in data:
                row += "█" if val >= threshold else " "
            lines.append(row)
        lines.append("-" * width)
        return "\n".join(lines)


class CounterfactualExplainer:
    """Explains what would change the decision."""
    
    def __init__(self) -> None:
        self.counterfactuals: Dict[str, List[Dict[str, Any]]] = {}
    
    def generate(self, decision_id: str, inputs: Dict[str, float], decision_fn: callable, threshold: float = 0.5) -> List[Dict[str, Any]]:
        """Generate counterfactual explanations."""
        original = decision_fn(inputs)
        alternatives = []
        for feature_name, value in inputs.items():
            # Try changing this feature
            modified = inputs.copy()
            modified[feature_name] = value * 1.5  # Perturb by 50%
            new_result = decision_fn(modified)
            if new_result != original:
                alternatives.append({
                    "feature": feature_name,
                    "original_value": value,
                    "changed_value": modified[feature_name],
                    "original_decision": original,
                    "new_decision": new_result,
                    "explanation": f"Changing {feature_name} from {value:.3f} to {modified[feature_name]:.3f} would change the decision.",
                })
        self.counterfactuals[decision_id] = alternatives
        return alternatives
    
    def explain(self, decision_id: str) -> str:
        alts = self.counterfactuals.get(decision_id, [])
        if not alts:
            return "No counterfactual explanations found."
        lines = [f"Counterfactual Explanations for {decision_id}", "=" * 50]
        for alt in alts[:5]:
            lines.append(f"\n{alt['explanation']}")
        return "\n".join(lines)


class ExplainabilityEngine:
    """Top-level XAI engine for MAGNATRIX-OS."""
    
    def __init__(self, repo_root: str = "") -> None:
        self.repo_root = repo_root
        self.chains: Dict[str, ReasoningChain] = {}
        self.attribution = AttributionMapper()
        self.confidence_viz = ConfidenceVisualizer()
        self.counterfactual = CounterfactualExplainer()
        self._chain_counter = 0
    
    def start_trace(self, trace_id: str = "") -> str:
        chain_id = trace_id or f"trace_{int(time.time())}_{self._chain_counter}"
        self._chain_counter += 1
        self.chains[chain_id] = ReasoningChain(chain_id)
        return chain_id
    
    def record_step(self, trace_id: str, module_name: str, action: str, input_data: Dict[str, Any], output_data: Dict[str, Any], confidence: float = 0.0, reasoning: str = "") -> None:
        chain = self.chains.get(trace_id)
        if chain:
            chain.add_step(module_name, action, input_data, output_data, confidence, reasoning)
            self.confidence_viz.record(confidence)
    
    def explain_decision(self, trace_id: str) -> str:
        chain = self.chains.get(trace_id)
        if not chain:
            return f"Trace {trace_id} not found."
        return chain.explain()
    
    def attribute(self, trace_id: str, inputs: Dict[str, float], output_delta: float) -> List[AttributionWeight]:
        return self.attribution.compute_attribution(trace_id, inputs, output_delta)
    
    def counterfactual_explain(self, trace_id: str, inputs: Dict[str, float], decision_fn: callable) -> List[Dict[str, Any]]:
        return self.counterfactual.generate(trace_id, inputs, decision_fn)
    
    def get_confidence_chart(self) -> str:
        return self.confidence_viz.ascii_chart()
    
    def get_confidence_trend(self) -> Dict[str, Any]:
        return self.confidence_viz.get_confidence_trend()
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_traces": len(self.chains),
            "total_steps": sum(len(c.steps) for c in self.chains.values()),
            "confidence_trend": self.confidence_viz.get_confidence_trend(),
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()
