"""Attention Visualization & Interpretability — Attention maps, saliency, feature attribution, reasoning trace.

Modul ini menyediakan:
- AttentionVisualizer untuk attention heatmap dan pattern analysis
- SaliencyAnalyzer untuk token importance scoring
- FeatureAttribution untuk contribution per input feature
- ReasoningTracer untuk trace reasoning steps dan decision paths
- InterpretabilityReport untuk generate explanation report

Arsitektur: Input → Model → Attention → Visualize → Attribute → Trace → Report
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class VizType(Enum):
    HEATMAP = auto()
    BAR_CHART = auto()
    FLOW_DIAGRAM = auto()
    TOKEN_HIGHLIGHT = auto()


class AttributionMethod(Enum):
    ATTENTION = auto()
    GRADIENT = auto()
    PERTURBATION = auto()
    LIME = auto()


@dataclass
class AttentionHead:
    """Attention pattern for a single head."""
    head_id: str
    layer: int
    head_index: int
    pattern: List[List[float]]  # token x token attention matrix
    tokens: List[str]

    def get_top_attention(self, token_idx: int, top_k: int = 5) -> List[Tuple[int, float]]:
        if token_idx >= len(self.pattern):
            return []
        scores = [(i, self.pattern[token_idx][i]) for i in range(len(self.tokens))]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def get_head_importance(self) -> float:
        if not self.pattern:
            return 0.0
        return sum(sum(row) for row in self.pattern) / (len(self.pattern) ** 2)


@dataclass
class TokenSaliency:
    """Saliency score for a token."""
    token: str
    index: int
    importance: float = 0.0
    attribution: float = 0.0
    entropy: float = 0.0


class AttentionVisualizer:
    """Visualize attention patterns across layers and heads."""

    def __init__(self, num_layers: int = 12, num_heads: int = 12):
        self.num_layers = num_layers
        self.num_heads = num_heads
        self._heads: Dict[str, AttentionHead] = {}

    def add_head(self, head: AttentionHead) -> None:
        self._heads[head.head_id] = head

    def get_layer_average(self, layer: int) -> Optional[List[List[float]]]:
        layer_heads = [h for h in self._heads.values() if h.layer == layer]
        if not layer_heads:
            return None
        n = len(layer_heads[0].tokens)
        avg = [[0.0] * n for _ in range(n)]
        for h in layer_heads:
            for i in range(n):
                for j in range(n):
                    avg[i][j] += h.pattern[i][j] / len(layer_heads)
        return avg

    def get_head_importance_ranking(self) -> List[Tuple[str, float]]:
        ranked = [(h.head_id, h.get_head_importance()) for h in self._heads.values()]
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

    def find_specialized_heads(self, threshold: float = 0.7) -> Dict[str, List[str]]:
        """Find heads that attend to specific patterns (e.g., first token, previous token)."""
        specialized = {"bos": [], "prev": [], "diagonal": [], "global": []}
        for h in self._heads.values():
            n = len(h.tokens)
            if n < 2:
                continue
            # Check if mostly attends to first token
            first_attn = sum(h.pattern[i][0] for i in range(n)) / n
            if first_attn > threshold:
                specialized["bos"].append(h.head_id)
            # Check if attends to previous token
            prev_attn = sum(h.pattern[i][max(0, i-1)] for i in range(1, n)) / (n - 1)
            if prev_attn > threshold:
                specialized["prev"].append(h.head_id)
            # Check diagonal (self-attention)
            diag_attn = sum(h.pattern[i][i] for i in range(n)) / n
            if diag_attn > threshold:
                specialized["diagonal"].append(h.head_id)
            # Check global (uniform attention)
            uniform = 1.0 / n
            global_attn = sum(abs(h.pattern[i][j] - uniform) for i in range(n) for j in range(n)) / (n * n)
            if global_attn < 0.1:
                specialized["global"].append(h.head_id)
        return specialized

    def to_dict(self) -> Dict[str, Any]:
        return {
            "num_layers": self.num_layers,
            "num_heads": self.num_heads,
            "total_heads": len(self._heads),
            "importance_ranking": self.get_head_importance_ranking()[:10],
            "specialized_heads": self.find_specialized_heads(),
        }


class SaliencyAnalyzer:
    """Analyze token importance via gradient-like methods."""

    def __init__(self):
        self._token_saliency: Dict[str, List[TokenSaliency]] = {}

    def analyze(self, tokens: List[str], predictor: Callable[[List[str]], List[float]]) -> List[TokenSaliency]:
        """Analyze saliency by removing each token and measuring output change."""
        baseline = predictor(tokens)
        results = []
        for i, token in enumerate(tokens):
            reduced = tokens[:i] + tokens[i+1:]
            reduced_output = predictor(reduced)
            importance = abs(sum(baseline) - sum(reduced_output)) / max(abs(sum(baseline)), 1e-9)
            results.append(TokenSaliency(
                token=token,
                index=i,
                importance=round(importance, 4)
            ))
        return results

    def get_top_tokens(self, saliency: List[TokenSaliency], top_k: int = 5) -> List[TokenSaliency]:
        sorted_sal = sorted(saliency, key=lambda x: x.importance, reverse=True)
        return sorted_sal[:top_k]

    def highlight(self, text: str, saliency: List[TokenSaliency], threshold: float = 0.3) -> str:
        tokens = text.split()
        parts = []
        for i, token in enumerate(tokens):
            if i < len(saliency) and saliency[i].importance > threshold:
                parts.append(f"[{token}]")
            else:
                parts.append(token)
        return " ".join(parts)


class FeatureAttribution:
    """Attribute output to input features."""

    def __init__(self, method: AttributionMethod = AttributionMethod.ATTENTION):
        self.method = method
        self._attributions: List[Dict[str, Any]] = []

    def attribute(self, inputs: Dict[str, Any], output: Any,
                  predictor: Callable[[Dict[str, Any]], Any]) -> Dict[str, float]:
        """Calculate feature attribution scores."""
        if self.method == AttributionMethod.ATTENTION:
            return self._attention_attribute(inputs, output)
        elif self.method == AttributionMethod.PERTURBATION:
            return self._perturbation_attribute(inputs, output, predictor)
        else:
            return self._default_attribute(inputs)

    def _attention_attribute(self, inputs: Dict[str, Any], output: Any) -> Dict[str, float]:
        # Simulated attention-based attribution
        return {k: len(str(v)) / 100.0 for k, v in inputs.items()}

    def _perturbation_attribute(self, inputs: Dict[str, Any], output: Any,
                                predictor: Callable[[Dict[str, Any]], Any]) -> Dict[str, float]:
        baseline = predictor(inputs)
        scores = {}
        for key in inputs:
            modified = {k: v for k, v in inputs.items()}
            modified[key] = None
            modified_output = predictor(modified)
            scores[key] = abs(float(baseline) - float(modified_output)) if isinstance(baseline, (int, float)) else 0.1
        return scores

    def _default_attribute(self, inputs: Dict[str, Any]) -> Dict[str, float]:
        return {k: 1.0 / len(inputs) for k in inputs}

    def add_record(self, record: Dict[str, Any]) -> None:
        self._attributions.append(record)

    def get_summary(self) -> Dict[str, Any]:
        if not self._attributions:
            return {}
        return {
            "total_records": len(self._attributions),
            "method": self.method.name,
        }


class ReasoningTracer:
    """Trace reasoning steps and decision paths."""

    def __init__(self):
        self._traces: List[Dict[str, Any]] = []
        self._current_trace: Optional[Dict[str, Any]] = None

    def start_trace(self, trace_id: str, query: str) -> None:
        self._current_trace = {
            "trace_id": trace_id,
            "query": query,
            "steps": [],
            "start_time": time.time(),
        }

    def add_step(self, step_name: str, inputs: Dict[str, Any], outputs: Dict[str, Any],
                 decision: str = "") -> None:
        if self._current_trace is None:
            return
        self._current_trace["steps"].append({
            "step": len(self._current_trace["steps"]) + 1,
            "name": step_name,
            "inputs": inputs,
            "outputs": outputs,
            "decision": decision,
            "timestamp": time.time(),
        })

    def end_trace(self, final_output: Any) -> Dict[str, Any]:
        if self._current_trace is None:
            return {}
        self._current_trace["end_time"] = time.time()
        self._current_trace["duration"] = self._current_trace["end_time"] - self._current_trace["start_time"]
        self._current_trace["final_output"] = str(final_output)[:200]
        self._traces.append(self._current_trace)
        trace = self._current_trace
        self._current_trace = None
        return trace

    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        for t in self._traces:
            if t["trace_id"] == trace_id:
                return t
        return None

    def get_all_traces(self) -> List[Dict[str, Any]]:
        return self._traces

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._traces, f, indent=2)


class InterpretabilityReport:
    """Generate comprehensive interpretability report."""

    def __init__(self, visualizer: AttentionVisualizer, saliency: SaliencyAnalyzer,
                 attribution: FeatureAttribution, tracer: ReasoningTracer):
        self.visualizer = visualizer
        self.saliency = saliency
        self.attribution = attribution
        self.tracer = tracer

    def generate(self, output_id: str = "") -> Dict[str, Any]:
        return {
            "output_id": output_id or str(uuid.uuid4())[:12],
            "generated_at": time.time(),
            "attention": self.visualizer.to_dict(),
            "attribution": self.attribution.get_summary(),
            "traces": len(self.tracer.get_all_traces()),
            "latest_trace": self.tracer.get_all_traces()[-1] if self.tracer.get_all_traces() else None,
        }

    def export_markdown(self, path: str, output_id: str = "") -> None:
        report = self.generate(output_id)
        lines = [
            f"# Interpretability Report: {report['output_id']}",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(report['generated_at']))}",
            "",
            "## Attention Analysis",
            f"- Total heads: {report['attention']['total_heads']}",
            f"- Layers: {report['attention']['num_layers']}",
            f"- Heads per layer: {report['attention']['num_heads']}",
            "",
            "### Specialized Heads",
        ]
        for stype, heads in report['attention']['specialized_heads'].items():
            lines.append(f"- {stype}: {len(heads)} heads")
        lines.extend([
            "",
            "## Attribution",
            f"- Method: {report['attribution'].get('method', 'N/A')}",
            f"- Records: {report['attribution'].get('total_records', 0)}",
            "",
            f"## Traces: {report['traces']}",
        ])
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))


class InterpretabilityEngine:
    """End-to-end interpretability engine."""

    def __init__(self, num_layers: int = 12, num_heads: int = 12):
        self.visualizer = AttentionVisualizer(num_layers, num_heads)
        self.saliency = SaliencyAnalyzer()
        self.attribution = FeatureAttribution()
        self.tracer = ReasoningTracer()
        self.reporter = InterpretabilityReport(self.visualizer, self.saliency, self.attribution, self.tracer)

    def trace(self, query: str, steps: List[Tuple[str, Dict[str, Any], Dict[str, Any], str]]) -> Dict[str, Any]:
        trace_id = str(uuid.uuid4())[:12]
        self.tracer.start_trace(trace_id, query)
        for step_name, inputs, outputs, decision in steps:
            self.tracer.add_step(step_name, inputs, outputs, decision)
        return self.tracer.end_trace("completed")

    def analyze_tokens(self, tokens: List[str], predictor: Callable[[List[str]], List[float]]) -> List[TokenSaliency]:
        return self.saliency.analyze(tokens, predictor)

    def add_attention_head(self, head: AttentionHead) -> None:
        self.visualizer.add_head(head)

    def get_report(self, output_id: str = "") -> Dict[str, Any]:
        return self.reporter.generate(output_id)

    def export(self, json_path: str, md_path: str) -> None:
        self.reporter.export_markdown(md_path)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("ATTENTION VISUALIZATION & INTERPRETABILITY DEMO")
    print("=" * 70)

    engine = InterpretabilityEngine(num_layers=2, num_heads=4)

    # 1. Simulate attention heads
    print("\n[1] Attention Heads Analysis")
    tokens = ["The", "cat", "sat", "on", "the", "mat"]
    for layer in range(2):
        for head in range(4):
            # Generate synthetic attention pattern
            n = len(tokens)
            pattern = [[0.0] * n for _ in range(n)]
            for i in range(n):
                for j in range(n):
                    if head == 0:  # BOS attention
                        pattern[i][j] = 0.5 if j == 0 else 0.1
                    elif head == 1:  # Previous token
                        pattern[i][j] = 0.7 if j == max(0, i-1) else 0.06
                    elif head == 2:  # Diagonal
                        pattern[i][j] = 0.8 if i == j else 0.04
                    else:  # Global
                        pattern[i][j] = 1.0 / n
            h = AttentionHead(
                head_id=f"L{layer}H{head}",
                layer=layer,
                head_index=head,
                pattern=pattern,
                tokens=tokens
            )
            engine.add_attention_head(h)
    print(f"  Total heads: {len(engine.visualizer._heads)}")
    ranking = engine.visualizer.get_head_importance_ranking()
    print(f"  Top 3 heads by importance: {ranking[:3]}")

    # 2. Specialized heads
    print("\n[2] Specialized Heads")
    specialized = engine.visualizer.find_specialized_heads(threshold=0.5)
    for stype, heads in specialized.items():
        print(f"  {stype}: {len(heads)} heads")

    # 3. Layer average
    print("\n[3] Layer Average Attention")
    avg = engine.visualizer.get_layer_average(0)
    if avg:
        print(f"  Layer 0 average shape: {len(avg)}x{len(avg[0]) if avg else 0}")

    # 4. Saliency analysis
    print("\n[4] Token Saliency Analysis")
    tokens = ["Explain", "how", "photosynthesis", "works"]
    predictor = lambda toks: [len(t) * 0.1 for t in toks]
    saliency = engine.analyze_tokens(tokens, predictor)
    for s in saliency:
        print(f"  [{s.token}] importance={s.importance:.3f}")
    top = engine.saliency.get_top_tokens(saliency, 2)
    print(f"  Top tokens: {[t.token for t in top]}")

    # 5. Highlight
    print("\n[5] Text Highlighting")
    text = "The quick brown fox jumps"
    tokens = text.split()
    saliency = engine.analyze_tokens(tokens, predictor)
    highlighted = engine.saliency.highlight(text, saliency, threshold=0.15)
    print(f"  Original: {text}")
    print(f"  Highlighted: {highlighted}")

    # 6. Feature attribution
    print("\n[6] Feature Attribution")
    inputs = {"topic": "AI", "length": 100, "style": "technical"}
    scores = engine.attribution.attribute(inputs, "output", lambda x: sum(len(str(v)) for v in x.values()))
    print(f"  Attribution scores: {scores}")

    # 7. Reasoning trace
    print("\n[7] Reasoning Trace")
    trace = engine.trace("What is 2+2?", [
        ("parse", {"query": "What is 2+2?"}, {"tokens": ["2", "+", "2"]}, "arithmetic"),
        ("compute", {"expression": "2+2"}, {"result": 4}, "addition"),
        ("format", {"result": 4}, {"output": "The answer is 4"}, "present"),
    ])
    print(f"  Trace ID: {trace['trace_id']}")
    print(f"  Steps: {len(trace['steps'])}")
    print(f"  Duration: {trace['duration']:.4f}s")
    for step in trace['steps']:
        print(f"    {step['step']}. {step['name']} -> {step['decision']}")

    # 8. Report
    print("\n[8] Interpretability Report")
    report = engine.get_report()
    print(f"  Report ID: {report['output_id']}")
    print(f"  Traces: {report['traces']}")
    print(f"  Attention heads: {report['attention']['total_heads']}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
