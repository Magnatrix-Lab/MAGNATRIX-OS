#!/usr/bin/env python3
"""
world_model.py — Model Dunia Internal MAGNATRIX
Batch Super AI — File 3/3 (Batch Berikutnya)

Model internal dunia untuk prediksi dan simulasi:
- observe_event: update model dengan observasi baru
- predict_state: prediksi state N jam ke depan
- simulate_scenario: simulasi "what-if" dari sekumpulan actions
- detect_anomaly: deteksi jika realita tidak cocok dengan model
- update_from_knowledge_graph: sinkronisasi dengan knowledge graph
"""
import json
import math
import random
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Set


# ── struktur data ────────────────────────────────────────────────────────────

@dataclass
class WorldEvent:
    event_id: str
    timestamp: str
    event_type: str           # market | system | user | agent | external
    source: str               # sumber event
    attributes: Dict[str, float]  # dimensi numerik (price, load, confidence, dll)
    tags: Set[str] = field(default_factory=set)


@dataclass
class StatePrediction:
    prediction_id: str
    horizon_hours: int
    predicted_state: Dict[str, float]
    confidence_interval: Dict[str, Tuple[float, float]]  # key → (low, high)
    confidence_score: float   # 0.0 - 1.0
    generated_at: str


@dataclass
class ScenarioResult:
    scenario_id: str
    actions: List[str]
    final_state: Dict[str, float]
    trajectory: List[Dict[str, float]]  # state per step
    outcome_score: float      # -10 sampai +10 (negatif = buruk, positif = baik)
    risks: List[str]
    opportunities: List[str]


@dataclass
class AnomalyReport:
    anomaly_id: str
    detected_at: str
    expected_state: Dict[str, float]
    actual_state: Dict[str, float]
    deviation_score: float    # 0.0 - 1.0 (semakin tinggi = semakin anomali)
    dimensions_anomalous: List[str]
    severity: str             # low | medium | high | critical


@dataclass
class KnowledgeNode:
    node_id: str
    concept: str
    relations: Dict[str, List[str]]  # relation_type → target_node_ids
    confidence: float
    last_updated: str


# ── model dunia internal ─────────────────────────────────────────────────────

class WorldModel:
    """
    Representasi internal dunia MAGNATRIX.
    Setiap dimensi state di-update via observasi dan bisa diprediksi ke depan.
    """
    
    # Dimensi default yang dipantau
    DEFAULT_DIMENSIONS = {
        "market_volatility": 0.3,
        "system_load": 0.5,
        "user_activity": 0.4,
        "agent_count": 3.0,
        "error_rate": 0.02,
        "sentiment_index": 0.6,
        "security_threat_level": 0.1,
        "resource_utilization": 0.55,
        "knowledge_graph_size": 100.0,
        "constitutional_violation_rate": 0.0,
    }
    
    def __init__(self):
        self.current_state: Dict[str, float] = dict(self.DEFAULT_DIMENSIONS)
        self.state_history: List[Dict[str, float]] = []
        self.events: List[WorldEvent] = []
        self.predictions: List[StatePrediction] = []
        self.anomalies: List[AnomalyReport] = []
        self.knowledge_graph: Dict[str, KnowledgeNode] = {}
        self._history_limit = 1000
    
    def observe_event(self, event: WorldEvent) -> None:
        """Update world model dengan observasi baru."""
        self.events.append(event)
        
        # Update state berdasarkan tipe event
        if event.event_type == "market":
            self.current_state["market_volatility"] = event.attributes.get("volatility", 0.3)
            self.current_state["sentiment_index"] = event.attributes.get("sentiment", 0.6)
        
        elif event.event_type == "system":
            self.current_state["system_load"] = event.attributes.get("load", 0.5)
            self.current_state["error_rate"] = event.attributes.get("error_rate", 0.02)
            self.current_state["resource_utilization"] = event.attributes.get("utilization", 0.55)
        
        elif event.event_type == "user":
            self.current_state["user_activity"] = event.attributes.get("activity", 0.4)
        
        elif event.event_type == "agent":
            self.current_state["agent_count"] = event.attributes.get("count", 3.0)
        
        elif event.event_type == "security":
            self.current_state["security_threat_level"] = event.attributes.get("threat", 0.1)
        
        elif event.event_type == "knowledge":
            self.current_state["knowledge_graph_size"] = event.attributes.get("size", 100.0)
        
        elif event.event_type == "constitutional":
            self.current_state["constitutional_violation_rate"] = event.attributes.get("violation_rate", 0.0)
        
        # Simpan state ke history
        self.state_history.append(dict(self.current_state))
        if len(self.state_history) > self._history_limit:
            self.state_history.pop(0)
    
    def predict_state(self, horizon_hours: int) -> StatePrediction:
        """Prediksi state dunia N jam ke depan menggunakan trend sederhana."""
        if len(self.state_history) < 2:
            # Fallback: asumsi state konstan
            pred = dict(self.current_state)
            ci = {k: (v * 0.8, v * 1.2) for k, v in pred.items()}
            return StatePrediction(
                prediction_id=f"pred-{horizon_hours}h-{self._now()}",
                horizon_hours=horizon_hours,
                predicted_state=pred,
                confidence_interval=ci,
                confidence_score=0.3,
                generated_at=self._now(),
            )
        
        # Hitung trend dari history
        window = min(10, len(self.state_history))
        recent = self.state_history[-window:]
        
        predicted = {}
        confidence_intervals = {}
        
        for dim in self.current_state:
            values = [s[dim] for s in recent]
            avg = sum(values) / len(values)
            
            if len(values) >= 2:
                # Trend linear sederhana
                trend = (values[-1] - values[0]) / (len(values) - 1)
                predicted[dim] = values[-1] + (trend * horizon_hours)
            else:
                predicted[dim] = values[-1]
            
            # Clamp ke range masuk akal
            predicted[dim] = max(0.0, min(1.0, predicted[dim])) if dim != "knowledge_graph_size" else max(0.0, predicted[dim])
            
            # Confidence interval: ±1 std dev
            if len(values) >= 2:
                variance = sum((v - avg) ** 2 for v in values) / len(values)
                std = math.sqrt(variance)
                confidence_intervals[dim] = (
                    max(0.0, predicted[dim] - std),
                    min(1.0, predicted[dim] + std) if dim != "knowledge_graph_size" else predicted[dim] + std,
                )
            else:
                confidence_intervals[dim] = (predicted[dim] * 0.9, predicted[dim] * 1.1)
        
        # Confidence score: semakin panjang history dan stabil, semakin tinggi
        stability = 1.0 - min(1.0, sum(abs(predicted[d] - self.current_state[d]) for d in predicted) / len(predicted))
        confidence = min(1.0, 0.3 + (len(self.state_history) / 100) * 0.5 + stability * 0.2)
        
        prediction = StatePrediction(
            prediction_id=f"pred-{horizon_hours}h-{self._now()}",
            horizon_hours=horizon_hours,
            predicted_state=predicted,
            confidence_interval=confidence_intervals,
            confidence_score=round(confidence, 3),
            generated_at=self._now(),
        )
        self.predictions.append(prediction)
        return prediction
    
    def simulate_scenario(self, actions: List[str], steps: int = 5) -> ScenarioResult:
        """Simulasi "what-if" dari sekumpulan actions."""
        state = dict(self.current_state)
        trajectory = [dict(state)]
        risks = []
        opportunities = []
        
        for step in range(steps):
            for action in actions:
                # Apply action effects
                if action == "scale_agents_up":
                    state["agent_count"] += 2
                    state["system_load"] += 0.15
                    if state["system_load"] > 0.8:
                        risks.append(f"Step {step+1}: System overload risk")
                
                elif action == "scale_agents_down":
                    state["agent_count"] = max(1, state["agent_count"] - 2)
                    state["system_load"] -= 0.1
                    opportunities.append(f"Step {step+1}: Resource freed")
                
                elif action == "tighten_security":
                    state["security_threat_level"] = max(0.0, state["security_threat_level"] - 0.2)
                    state["user_activity"] *= 0.95  # sedikit friction
                
                elif action == "loosen_security":
                    state["security_threat_level"] += 0.15
                    state["user_activity"] *= 1.05
                    risks.append(f"Step {step+1}: Security exposure increased")
                
                elif action == "deploy_trading_strategy":
                    state["market_volatility"] += 0.1
                    state["sentiment_index"] += 0.05
                    opportunities.append(f"Step {step+1}: Trading revenue potential")
                
                elif action == "update_constitution":
                    state["constitutional_violation_rate"] = max(0.0, state["constitutional_violation_rate"] - 0.05)
                    state["knowledge_graph_size"] += 10
                
                elif action == "add_knowledge":
                    state["knowledge_graph_size"] += 25
                
                elif action == "stress_test":
                    state["system_load"] += 0.2
                    state["error_rate"] = min(0.5, state["error_rate"] + 0.05)
                    risks.append(f"Step {step+1}: Errors may cascade")
                
                else:
                    # Unknown action: random micro-effect
                    state["system_load"] += random.uniform(-0.02, 0.02)
            
            # Clamp semua dimensi
            for k in state:
                if k == "knowledge_graph_size" or k == "agent_count":
                    state[k] = max(0.0, state[k])
                else:
                    state[k] = max(0.0, min(1.0, state[k]))
            
            trajectory.append(dict(state))
        
        # Hitung outcome score
        outcome = 0.0
        outcome += (0.6 - state["error_rate"]) * 10  # lower error = better
        outcome += (0.5 - state["security_threat_level"]) * 8
        outcome += (state["sentiment_index"] - 0.5) * 5
        outcome += (state["knowledge_graph_size"] - 100) * 0.02
        outcome -= (state["system_load"] - 0.5) * 5 if state["system_load"] > 0.7 else 0
        
        return ScenarioResult(
            scenario_id=f"scen-{self._now()}",
            actions=actions,
            final_state=state,
            trajectory=trajectory,
            outcome_score=round(outcome, 2),
            risks=risks,
            opportunities=opportunities,
        )
    
    def detect_anomaly(self, observed_state: Dict[str, float]) -> Optional[AnomalyReport]:
        """Deteksi jika realita tidak cocok dengan model."""
        expected = self.predict_state(horizon_hours=0).predicted_state  # current predicted
        deviations = {}
        anomalous_dims = []
        
        for dim, expected_val in expected.items():
            actual_val = observed_state.get(dim, expected_val)
            # Normalized deviation
            if expected_val > 0:
                dev = abs(actual_val - expected_val) / expected_val
            else:
                dev = abs(actual_val - expected_val)
            
            deviations[dim] = dev
            threshold = 0.3 if dim in ["market_volatility", "sentiment_index"] else 0.2
            if dev > threshold:
                anomalous_dims.append(dim)
        
        max_deviation = max(deviations.values()) if deviations else 0.0
        
        if anomalous_dims:
            severity = "low"
            if max_deviation > 0.5:
                severity = "critical"
            elif max_deviation > 0.3:
                severity = "high"
            elif max_deviation > 0.2:
                severity = "medium"
            
            report = AnomalyReport(
                anomaly_id=f"anomaly-{self._now()}",
                detected_at=self._now(),
                expected_state=expected,
                actual_state=observed_state,
                deviation_score=round(max_deviation, 3),
                dimensions_anomalous=anomalous_dims,
                severity=severity,
            )
            self.anomalies.append(report)
            return report
        
        return None
    
    def update_from_knowledge_graph(self, nodes: List[KnowledgeNode]) -> None:
        """Sinkronisasi world model dengan knowledge graph."""
        for node in nodes:
            self.knowledge_graph[node.node_id] = node
        
        # Update dimensi terkait
        self.current_state["knowledge_graph_size"] = float(len(self.knowledge_graph))
        
        # Deteksi knowledge gaps dari relations
        total_relations = sum(len(rels) for node in nodes for rels in node.relations.values())
        if total_relations > 0:
            # Semakin banyak relasi, semakin "connected" knowledge graph
            connectivity = min(1.0, total_relations / (len(nodes) * 3))
            self.current_state["sentiment_index"] = max(self.current_state["sentiment_index"], connectivity * 0.5)
    
    def get_summary(self) -> Dict:
        """Ringkasan state dunia saat ini."""
        return {
            "timestamp": self._now(),
            "current_state": self.current_state,
            "events_observed": len(self.events),
            "predictions_made": len(self.predictions),
            "anomalies_detected": len(self.anomalies),
            "knowledge_nodes": len(self.knowledge_graph),
            "state_history_length": len(self.state_history),
        }
    
    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()


# ── demo ───────────────────────────────────────────────────────────────────

def _make_event(event_type: str, source: str, **attrs) -> WorldEvent:
    return WorldEvent(
        event_id=f"evt-{event_type}-{datetime.now(timezone.utc).timestamp()}",
        timestamp=datetime.now(timezone.utc).isoformat(),
        event_type=event_type,
        source=source,
        attributes=attrs,
    )


if __name__ == "__main__":
    print("=" * 70)
    print("MAGNATRIX World Model — Model Dunia Internal")
    print("=" * 70)
    
    model = WorldModel()
    
    # Demo 1: Observe events
    print("\n[1] OBSERVASI EVENT")
    events = [
        _make_event("market", "trading_engine", volatility=0.45, sentiment=0.72),
        _make_event("system", "monitor", load=0.62, error_rate=0.01, utilization=0.58),
        _make_event("user", "chat", activity=0.55),
        _make_event("agent", "orchestrator", count=5.0),
        _make_event("security", "firewall", threat=0.15),
    ]
    for evt in events:
        model.observe_event(evt)
    print(f"  State updated: {len(events)} events")
    print(f"  Current: {json.dumps(model.current_state, indent=2)[:200]}...")
    
    # Demo 2: Predict future
    print("\n[2] PREDIKSI 6 JAM KE DEPAN")
    pred = model.predict_state(horizon_hours=6)
    print(f"  Confidence: {pred.confidence_score}")
    print(f"  Market volatility: {model.current_state['market_volatility']:.2f} → {pred.predicted_state['market_volatility']:.2f}")
    print(f"  System load: {model.current_state['system_load']:.2f} → {pred.predicted_state['system_load']:.2f}")
    
    # Demo 3: Simulate scenario
    print("\n[3] SIMULASI SCENARIO: scale up + deploy trading")
    scenario = model.simulate_scenario(
        actions=["scale_agents_up", "deploy_trading_strategy"],
        steps=5,
    )
    print(f"  Outcome score: {scenario.outcome_score}")
    print(f"  Risks: {scenario.risks}")
    print(f"  Opportunities: {scenario.opportunities}")
    print(f"  Final agent_count: {scenario.final_state['agent_count']}")
    print(f"  Final system_load: {scenario.final_state['system_load']:.2f}")
    
    # Demo 4: Detect anomaly
    print("\n[4] DETEKSI ANOMALI")
    fake_observation = dict(model.current_state)
    fake_observation["security_threat_level"] = 0.75  # anomaly!
    fake_observation["error_rate"] = 0.25  # anomaly!
    anomaly = model.detect_anomaly(fake_observation)
    if anomaly:
        print(f"  ⚠️  ANOMALI TERDETEKSI!")
        print(f"      Severity: {anomaly.severity}")
        print(f"      Deviation: {anomaly.deviation_score}")
        print(f"      Dimensi anomali: {anomaly.dimensions_anomalous}")
    
    # Demo 5: Knowledge graph sync
    print("\n[5] SINKRONISASI KNOWLEDGE GRAPH")
    kg_nodes = [
        KnowledgeNode("n1", "trading_strategy", {"uses": ["n2"], "depends_on": ["n3"]}, 0.9, model._now()),
        KnowledgeNode("n2", "market_data", {"feeds": ["n1"]}, 0.85, model._now()),
        KnowledgeNode("n3", "risk_model", {"validates": ["n1"]}, 0.8, model._now()),
    ]
    model.update_from_knowledge_graph(kg_nodes)
    print(f"  Knowledge nodes: {len(model.knowledge_graph)}")
    print(f"  Knowledge graph size dim: {model.current_state['knowledge_graph_size']}")
    
    # Demo 6: Summary
    print("\n[6] RINGKASAN MODEL DUNIA")
    print(json.dumps(model.get_summary(), indent=2, default=str))
    
    print("\n" + "=" * 70)
    print("World model selesai.")
    print("=" * 70)
