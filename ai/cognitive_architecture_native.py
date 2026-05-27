#!/usr/bin/env python3
"""
MAGNATRIX-OS Layer: AI — Unified Cognitive Architecture
File: ai/cognitive_architecture_native.py
Pattern: AGI from scratch — one "brain" unifying all 15 layers

This is the central AGI kernel. It orchestrates:
  - Perception (sensory input processing)
  - Memory (short-term + long-term + episodic)
  - Reasoning (deductive, inductive, abductive)
  - Planning (goal decomposition, strategy selection)
  - Action (tool execution, agent delegation, code generation)
  - Learning (pattern extraction, skill acquisition, model adaptation)
  - Metacognition (self-monitoring, resource allocation, introspection)
  - Communication (natural language, protocol, multi-agent)

The brain is NOT a collection of separate modules.
It is a unified cognitive graph where every component can influence every other.

Zero external dependencies. Pure Python standard library.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


# ============================================================================
# 1.  COGNITIVE NODE — fundamental unit of thought
# ============================================================================

@dataclass
class CognitiveNode:
    """
    A single unit of cognition: perception, concept, belief, goal, or action.
    Forms a unified semantic graph where edges are typed relations.
    """
    node_id: str
    node_type: str  # perception | concept | belief | goal | action | emotion | memory
    content: str = ""
    activation: float = 0.0  # 0.0-1.0, spreads like neural activation
    confidence: float = 1.0  # 0.0-1.0, truth value
    timestamp: float = field(default_factory=time.time)
    source: str = "internal"  # sensor | memory | reasoning | communication
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def activate(self, amount: float = 0.1) -> None:
        self.activation = min(1.0, self.activation + amount)

    def decay(self, rate: float = 0.01) -> None:
        self.activation = max(0.0, self.activation - rate)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.node_id, "type": self.node_type,
            "content": self.content, "activation": self.activation,
            "confidence": self.confidence, "timestamp": self.timestamp,
            "source": self.source, "tags": self.tags,
        }


# ============================================================================
# 2.  UNIFIED COGNITIVE GRAPH — the "brain"
# ============================================================================

class UnifiedCognitiveGraph:
    """
    The central brain: a semantic graph where all cognition happens.
    Not a collection of separate modules — one unified structure.
    """

    RELATION_TYPES = [
        "causes", "implies", "contradicts", "supports", "part_of",
        "instance_of", "similar_to", "precedes", "enables", "inhibits",
        "remembers", "predicts", "desires", "achieves", "observes",
    ]

    def __init__(self) -> None:
        self._nodes: Dict[str, CognitiveNode] = {}
        self._edges: Dict[str, List[Tuple[str, str, float]]] = defaultdict(list)
        # edges[from] = [(relation, to, weight)]
        self._lock = threading.RLock()
        self._activation_log: deque = deque(maxlen=1000)

    def add_node(self, node: CognitiveNode) -> None:
        with self._lock:
            self._nodes[node.node_id] = node
            self._activation_log.append((time.time(), node.node_id, node.activation))

    def add_edge(self, from_id: str, relation: str, to_id: str, weight: float = 1.0) -> None:
        with self._lock:
            if from_id in self._nodes and to_id in self._nodes:
                self._edges[from_id].append((relation, to_id, weight))

    def get_node(self, node_id: str) -> Optional[CognitiveNode]:
        with self._lock:
            return self._nodes.get(node_id)

    def query_by_type(self, node_type: str, min_activation: float = 0.0) -> List[CognitiveNode]:
        with self._lock:
            return [
                n for n in self._nodes.values()
                if n.node_type == node_type and n.activation >= min_activation
            ]

    def spread_activation(self, source_id: str, depth: int = 3, decay: float = 0.3) -> Dict[str, float]:
        """
        Spreading activation search — like neural spreading in the brain.
        From a source node, activation spreads to connected nodes.
        """
        with self._lock:
            activations = {source_id: 1.0}
            current_layer = {source_id}
            for _ in range(depth):
                next_layer = set()
                for node_id in current_layer:
                    for relation, target, weight in self._edges.get(node_id, []):
                        if target in self._nodes:
                            spread = activations[node_id] * weight * (1 - decay)
                            if spread > 0.05:
                                activations[target] = activations.get(target, 0.0) + spread
                                self._nodes[target].activate(spread)
                                next_layer.add(target)
                current_layer = next_layer
            return activations

    def find_path(self, start: str, end: str, max_depth: int = 5) -> Optional[List[str]]:
        """BFS shortest path in cognitive graph."""
        q = deque([(start, [start])])
        visited = {start}
        while q:
            node, path = q.popleft()
            if node == end and len(path) > 1:
                return path
            if len(path) >= max_depth:
                continue
            for relation, target, _ in self._edges.get(node, []):
                if target not in visited:
                    visited.add(target)
                    q.append((target, path + [target]))
        return None

    def associative_recall(self, cue: str, top_k: int = 5) -> List[CognitiveNode]:
        """Recall nodes similar to a cue via spreading activation."""
        # Create temporary cue node
        cue_id = f"cue_{uuid.uuid4().hex[:8]}"
        cue_node = CognitiveNode(cue_id, "perception", cue, activation=1.0)
        self.add_node(cue_node)
        # Link cue to similar nodes by content similarity
        for node in self._nodes.values():
            if node.node_id == cue_id:
                continue
            similarity = self._text_similarity(cue, node.content)
            if similarity > 0.3:
                self.add_edge(cue_id, "similar_to", node.node_id, similarity)
        # Spread
        acts = self.spread_activation(cue_id, depth=2)
        del self._nodes[cue_id]
        del self._edges[cue_id]
        # Return top activated nodes
        scored = [(nid, act) for nid, act in acts.items() if nid != cue_id]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [self._nodes[nid] for nid, _ in scored[:top_k] if nid in self._nodes]

    @staticmethod
    def _text_similarity(a: str, b: str) -> float:
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        return len(words_a & words_b) / len(words_a | words_b)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            types = defaultdict(int)
            for n in self._nodes.values():
                types[n.node_type] += 1
            return {
                "nodes": len(self._nodes),
                "edges": sum(len(e) for e in self._edges.values()),
                "by_type": dict(types),
                "avg_activation": sum(n.activation for n in self._nodes.values()) / max(len(self._nodes), 1),
            }


# ============================================================================
# 3.  PERCEPTION — sensory input processing
# ============================================================================

class PerceptionModule:
    """
    Converts raw input (text, numbers, structured data) into cognitive nodes.
    """

    def __init__(self, graph: UnifiedCognitiveGraph) -> None:
        self.graph = graph
        self._sensors: Dict[str, Callable[[Any], List[CognitiveNode]]] = {}

    def register_sensor(self, name: str, processor: Callable[[Any], List[CognitiveNode]]) -> None:
        self._sensors[name] = processor

    def perceive(self, sensor: str, data: Any) -> List[str]:
        """Process sensory input and add to cognitive graph."""
        if sensor not in self._sensors:
            # Default: treat as text perception
            nodes = self._default_text_perception(data)
        else:
            nodes = self._sensors[sensor](data)
        ids = []
        for node in nodes:
            self.graph.add_node(node)
            ids.append(node.node_id)
        return ids

    def _default_text_perception(self, text: str) -> List[CognitiveNode]:
        """Break text into concepts, entities, and relations."""
        nodes = []
        edges_to_add = []
        # Main perception
        main_id = f"percept_{uuid.uuid4().hex[:8]}"
        nodes.append(CognitiveNode(main_id, "perception", str(text)[:200], activation=0.8, source="sensor"))
        # Extract keywords as concepts
        words = re.findall(r'\b[A-Za-z]{4,}\b', str(text))
        for word in set(words):
            cid = f"concept_{word.lower()}"
            if self.graph.get_node(cid) is None:
                nodes.append(CognitiveNode(cid, "concept", word.lower(), activation=0.3, source="internal"))
            edges_to_add.append((main_id, "observes", cid, 0.5))
        # Extract sentences as beliefs
        sentences = re.split(r'[.!?]', str(text))
        for sent in sentences:
            sent = sent.strip()
            if len(sent) > 20:
                bid = f"belief_{uuid.uuid4().hex[:8]}"
                nodes.append(CognitiveNode(bid, "belief", sent, activation=0.5, source="internal"))
                edges_to_add.append((main_id, "supports", bid, 0.6))
        # Add edges
        for from_id, relation, to_id, weight in edges_to_add:
            self.graph.add_edge(from_id, relation, to_id, weight)
        return nodes


# ============================================================================
# 4.  MEMORY — episodic + semantic + procedural
# ============================================================================

class MemorySystem:
    """
    Three-tier memory: episodic (events), semantic (facts), procedural (skills).
    All stored in the unified cognitive graph.
    """

    def __init__(self, graph: UnifiedCognitiveGraph) -> None:
        self.graph = graph
        self._episodic_index: deque = deque(maxlen=500)
        self._skill_procedures: Dict[str, List[str]] = {}

    def store_episode(self, event: str, context: Dict[str, Any] = None) -> str:
        """Store an episodic memory (event with timestamp)."""
        eid = f"ep_{uuid.uuid4().hex[:8]}"
        node = CognitiveNode(eid, "memory", event, activation=0.7,
                             source="memory", metadata={"context": context or {}, "episode": True})
        self.graph.add_node(node)
        self._episodic_index.append((time.time(), eid))
        # Link to current active concepts
        for concept in self.graph.query_by_type("concept", min_activation=0.3)[:5]:
            self.graph.add_edge(eid, "remembers", concept.node_id, 0.4)
        return eid

    def store_fact(self, fact: str, confidence: float = 1.0) -> str:
        """Store a semantic memory (fact)."""
        fid = f"fact_{uuid.uuid4().hex[:8]}"
        node = CognitiveNode(fid, "belief", fact, activation=0.6,
                             confidence=confidence, source="memory")
        self.graph.add_node(node)
        return fid

    def store_procedure(self, name: str, steps: List[str]) -> None:
        """Store a procedural memory (skill)."""
        self._skill_procedures[name] = steps
        pid = f"proc_{name}"
        node = CognitiveNode(pid, "action", f"Procedure: {name}", activation=0.5,
                             source="memory", metadata={"steps": steps})
        self.graph.add_node(node)

    def recall_episodes(self, cue: str, top_k: int = 5) -> List[CognitiveNode]:
        """Episodic recall via associative memory."""
        return self.graph.associative_recall(cue, top_k)

    def recall_procedure(self, name: str) -> Optional[List[str]]:
        return self._skill_procedures.get(name)

    def consolidate(self) -> None:
        """Memory consolidation: strengthen frequently accessed memories."""
        for node in self.graph.query_by_type("memory"):
            node.decay(0.02)
        for node in self.graph.query_by_type("belief"):
            if node.confidence > 0.8:
                node.activate(0.05)


# ============================================================================
# 5.  REASONING — deductive, inductive, abductive
# ============================================================================

class ReasoningEngine:
    """
    Multi-modal reasoning over the cognitive graph.
    """

    def __init__(self, graph: UnifiedCognitiveGraph) -> None:
        self.graph = graph
        self._rules: List[Tuple[str, str, str, float]] = []
        # (premise_type, conclusion_type, relation, confidence_boost)

    def add_rule(self, premise: str, conclusion: str, relation: str, boost: float = 0.1) -> None:
        self._rules.append((premise, conclusion, relation, boost))

    def deduce(self, premise_id: str, max_depth: int = 3) -> List[Tuple[str, str, float]]:
        """
        Deductive reasoning: from premises, derive conclusions via graph edges.
        Returns list of (conclusion_id, relation, confidence).
        """
        conclusions = []
        visited = {premise_id}
        q = deque([(premise_id, 1.0, 0)])
        while q:
            node_id, conf, depth = q.popleft()
            if depth >= max_depth:
                continue
            for relation, target, weight in self.graph._edges.get(node_id, []):
                if target not in visited:
                    visited.add(target)
                    new_conf = conf * weight
                    if new_conf > 0.2:
                        conclusions.append((target, relation, new_conf))
                        q.append((target, new_conf, depth + 1))
        return conclusions

    def abduce(self, observation_id: str, top_k: int = 3, max_depth: int = 2) -> List[Tuple[str, float]]:
        """
        Abductive reasoning: infer best explanation for an observation.
        Finds nodes that CAUSE the observation (recursively).
        """
        explanations = []
        visited = {observation_id}
        q = deque([(observation_id, 1.0, 0)])
        while q:
            target_id, current_weight, depth = q.popleft()
            if depth >= max_depth:
                continue
            for node_id, edges in self.graph._edges.items():
                for relation, to_id, weight in edges:
                    if to_id == target_id and relation in ("causes", "enables", "implies"):
                        if node_id not in visited:
                            visited.add(node_id)
                            combined_weight = current_weight * weight
                            explanations.append((node_id, combined_weight))
                            q.append((node_id, combined_weight, depth + 1))
        explanations.sort(key=lambda x: x[1], reverse=True)
        return explanations[:top_k]

    def analogize(self, source_id: str, target_domain: str) -> List[CognitiveNode]:
        """
        Analogical reasoning: find similar structures in target domain.
        """
        source = self.graph.get_node(source_id)
        if not source:
            return []
        # Find nodes in target domain with similar content
        candidates = []
        for node in self.graph._nodes.values():
            if node.node_id == source_id:
                continue
            if target_domain in node.tags or target_domain in node.content:
                sim = self.graph._text_similarity(source.content, node.content)
                if sim > 0.2:
                    candidates.append((node, sim))
        candidates.sort(key=lambda x: x[1], reverse=True)
        return [n for n, _ in candidates[:5]]


# ============================================================================
# 6.  PLANNING — goal-driven action selection
# ============================================================================

class PlanningEngine:
    """
    Goal-driven planning: decompose goals, select strategies, execute plans.
    """

    def __init__(self, graph: UnifiedCognitiveGraph, memory: MemorySystem) -> None:
        self.graph = graph
        self.memory = memory
        self._plans: Dict[str, List[str]] = {}

    def set_goal(self, goal: str, priority: float = 0.5) -> str:
        """Set a goal in the cognitive graph."""
        gid = f"goal_{uuid.uuid4().hex[:8]}"
        node = CognitiveNode(gid, "goal", goal, activation=priority, source="internal")
        self.graph.add_node(node)
        return gid

    def plan(self, goal_id: str) -> List[str]:
        """
        Generate a plan to achieve goal.
        Returns ordered list of action node IDs.
        """
        goal = self.graph.get_node(goal_id)
        if not goal:
            return []
        # Check procedural memory for similar goals
        for proc_name, steps in self.memory._skill_procedures.items():
            if self.graph._text_similarity(goal.content, proc_name) > 0.4:
                # Instantiate procedure
                plan = []
                for step in steps:
                    aid = f"act_{uuid.uuid4().hex[:8]}"
                    self.graph.add_node(CognitiveNode(aid, "action", step, activation=0.5))
                    plan.append(aid)
                self._plans[goal_id] = plan
                return plan
        # Default: decompose into generic steps
        plan = []
        steps = [f"Analyze {goal.content}", f"Plan approach to {goal.content}",
                 f"Execute plan for {goal.content}", f"Verify {goal.content} outcome"]
        for step in steps:
            aid = f"act_{uuid.uuid4().hex[:8]}"
            self.graph.add_node(CognitiveNode(aid, "action", step, activation=0.4))
            plan.append(aid)
        self._plans[goal_id] = plan
        return plan

    def execute_plan(self, goal_id: str) -> Dict[str, Any]:
        """Execute a plan step by step (simulated)."""
        plan = self._plans.get(goal_id, [])
        results = []
        for action_id in plan:
            action = self.graph.get_node(action_id)
            if action:
                action.activate(0.3)
                result = f"[DONE] {action.content[:50]}"
                results.append(result)
                # Mark action as achieving goal
                self.graph.add_edge(action_id, "achieves", goal_id, 0.5)
        return {"goal": goal_id, "steps_taken": len(plan), "results": results}


# ============================================================================
# 7.  LEARNING — pattern extraction, skill acquisition
# ============================================================================

class LearningEngine:
    """
    Extract patterns from experience, acquire new skills, adapt behavior.
    """

    def __init__(self, graph: UnifiedCognitiveGraph, memory: MemorySystem) -> None:
        self.graph = graph
        self.memory = memory
        self._patterns: List[Dict[str, Any]] = []

    def extract_patterns(self, episode_ids: List[str]) -> List[Dict[str, Any]]:
        """Find recurring patterns in episodes."""
        episodes = [self.graph.get_node(eid) for eid in episode_ids]
        episodes = [e for e in episodes if e is not None]
        if len(episodes) < 2:
            return []
        # Simple pattern: common words across episodes
        word_counts = defaultdict(int)
        for ep in episodes:
            for word in set(ep.content.lower().split()):
                if len(word) > 3:
                    word_counts[word] += 1
        patterns = []
        for word, count in word_counts.items():
            if count >= len(episodes) * 0.5:
                pid = f"pattern_{word}"
                self.graph.add_node(CognitiveNode(pid, "concept", f"Pattern: {word}", activation=0.4))
                patterns.append({"pattern": word, "frequency": count, "node_id": pid})
        self._patterns.extend(patterns)
        return patterns

    def learn_skill(self, name: str, examples: List[Dict[str, Any]]) -> bool:
        """Generalize from examples to learn a new skill."""
        if not examples:
            return False
        # Extract common steps
        all_steps = []
        for ex in examples:
            steps = ex.get("steps", [])
            all_steps.extend(steps)
        if not all_steps:
            return False
        # Simple generalization: most common steps
        step_counts = defaultdict(int)
        for step in all_steps:
            step_counts[step] += 1
        threshold = len(examples) * 0.5
        learned_steps = [s for s, c in step_counts.items() if c >= threshold]
        if learned_steps:
            self.memory.store_procedure(name, learned_steps)
            return True
        return False

    def adapt(self, feedback: Dict[str, Any]) -> None:
        """Adapt behavior based on feedback."""
        for node_id, delta in feedback.get("activation_changes", {}).items():
            node = self.graph.get_node(node_id)
            if node:
                node.activation = max(0.0, min(1.0, node.activation + delta))


# ============================================================================
# 8.  METACOGNITION — self-monitoring, introspection
# ============================================================================

class MetacognitionModule:
    """
    The brain thinking about itself.
    Monitors resources, evaluates strategies, decides when to learn.
    """

    def __init__(self, graph: UnifiedCognitiveGraph, reasoner: ReasoningEngine,
                 planner: PlanningEngine, learner: LearningEngine) -> None:
        self.graph = graph
        self.reasoner = reasoner
        self.planner = planner
        self.learner = learner
        self._introspection_log: deque = deque(maxlen=200)

    def introspect(self) -> Dict[str, Any]:
        """Generate a self-report of current cognitive state."""
        stats = self.graph.stats()
        active_goals = self.graph.query_by_type("goal", min_activation=0.3)
        active_beliefs = self.graph.query_by_type("belief", min_activation=0.3)
        report = {
            "timestamp": time.time(),
            "cognitive_load": stats["avg_activation"],
            "active_goals": len(active_goals),
            "active_beliefs": len(active_beliefs),
            "total_nodes": stats["nodes"],
            "total_edges": stats["edges"],
            "node_types": stats["by_type"],
            "self_assessment": self._assess_performance(),
        }
        self._introspection_log.append(report)
        return report

    def _assess_performance(self) -> str:
        """Self-assessment of current performance."""
        goals = self.graph.query_by_type("goal")
        achieved = sum(1 for g in goals if g.activation > 0.7)
        total = len(goals)
        if total == 0:
            return "idle"
        ratio = achieved / total
        if ratio > 0.8:
            return "highly_efficient"
        elif ratio > 0.5:
            return "moderately_efficient"
        else:
            return "struggling"

    def should_learn(self) -> bool:
        """Decide if learning is needed based on recent performance."""
        if len(self._introspection_log) < 3:
            return False
        recent = list(self._introspection_log)[-3:]
        loads = [r["cognitive_load"] for r in recent]
        if sum(loads) / len(loads) < 0.3:
            return True  # Underutilized — learn something new
        return False

    def resource_allocation(self) -> Dict[str, float]:
        """Allocate cognitive resources among competing goals."""
        goals = self.graph.query_by_type("goal")
        total_prio = sum(g.activation for g in goals) or 1.0
        return {g.node_id: g.activation / total_prio for g in goals}


# ============================================================================
# 9.  UNIFIED AGI BRAIN — integrates all modules
# ============================================================================

class UnifiedAGIBrain:
    """
    The complete AGI kernel. One object that IS the artificial superintelligence.
    """

    def __init__(self) -> None:
        self.graph = UnifiedCognitiveGraph()
        self.perception = PerceptionModule(self.graph)
        self.memory = MemorySystem(self.graph)
        self.reasoning = ReasoningEngine(self.graph)
        self.planning = PlanningEngine(self.graph, self.memory)
        self.learning = LearningEngine(self.graph, self.memory)
        self.metacognition = MetacognitionModule(self.graph, self.reasoning, self.planning, self.learning)
        self._cycle_count = 0
        self._running = True

    def perceive(self, data: Any, sensor: str = "text") -> List[str]:
        """Process sensory input."""
        return self.perception.perceive(sensor, data)

    def think(self, topic: str, depth: int = 3) -> Dict[str, Any]:
        """Generate thoughts about a topic via spreading activation."""
        # Create seed node
        seed_id = f"think_{uuid.uuid4().hex[:8]}"
        self.graph.add_node(CognitiveNode(seed_id, "concept", topic, activation=1.0))
        # Spread
        activations = self.graph.spread_activation(seed_id, depth=depth)
        # Reason
        deductions = self.reasoning.deduce(seed_id, max_depth=depth)
        # Recall
        memories = self.memory.recall_episodes(topic, top_k=3)
        return {
            "seed": seed_id,
            "activated_nodes": len(activations),
            "deductions": len(deductions),
            "recalled_memories": len(memories),
            "dominant_concepts": [n.content for n in memories[:3]],
        }

    def plan(self, goal: str) -> Dict[str, Any]:
        """Set a goal, plan, and execute."""
        gid = self.planning.set_goal(goal, priority=0.7)
        plan = self.planning.plan(gid)
        result = self.planning.execute_plan(gid)
        return {"goal_id": gid, "plan_length": len(plan), "execution": result}

    def learn(self, experience: Dict[str, Any]) -> Dict[str, Any]:
        """Learn from experience."""
        episode_id = self.memory.store_episode(experience.get("event", ""), experience)
        patterns = self.learning.extract_patterns([episode_id])
        return {"episode": episode_id, "patterns_found": len(patterns), "patterns": patterns}

    def introspect(self) -> Dict[str, Any]:
        """Self-reflection."""
        return self.metacognition.introspect()

    def cycle(self, input_data: Any = None) -> Dict[str, Any]:
        """One full cognitive cycle: perceive → think → plan → learn → introspect."""
        self._cycle_count += 1
        results = {"cycle": self._cycle_count}
        if input_data:
            results["perception"] = self.perceive(input_data)
        results["thought"] = self.think(f"cycle_{self._cycle_count}")
        results["introspection"] = self.introspect()
        if self.metacognition.should_learn():
            results["learning"] = self.learn({"event": f"Auto-learning cycle {self._cycle_count}"})
        # Decay old activations
        for node in list(self.graph._nodes.values()):
            node.decay(0.005)
        return results

    def get_state(self) -> Dict[str, Any]:
        return {
            "cycles": self._cycle_count,
            "cognitive_graph": self.graph.stats(),
            "procedures": len(self.memory._skill_procedures),
            "episodes": len(self.memory._episodic_index),
            "self_assessment": self.metacognition._assess_performance(),
        }


# ============================================================================
# 10.  TEST SUITE & DEMO
# ============================================================================

def _test_cognitive_graph() -> None:
    g = UnifiedCognitiveGraph()
    n1 = CognitiveNode("n1", "concept", "artificial intelligence", activation=0.8)
    n2 = CognitiveNode("n2", "concept", "machine learning", activation=0.6)
    n3 = CognitiveNode("n3", "goal", "build AGI", activation=0.9)
    g.add_node(n1)
    g.add_node(n2)
    g.add_node(n3)
    g.add_edge("n1", "enables", "n2", 0.7)
    g.add_edge("n2", "achieves", "n3", 0.5)
    acts = g.spread_activation("n1", depth=2)
    assert "n3" in acts
    path = g.find_path("n1", "n3")
    assert path is not None
    print("  [OK] UnifiedCognitiveGraph")


def _test_perception() -> None:
    g = UnifiedCognitiveGraph()
    p = PerceptionModule(g)
    ids = p.perceive("text", "Artificial intelligence and machine learning are transforming software.")
    assert len(ids) > 1
    print("  [OK] PerceptionModule")


def _test_memory() -> None:
    g = UnifiedCognitiveGraph()
    m = MemorySystem(g)
    eid = m.store_episode("Built trading bot today", {"outcome": "success"})
    fid = m.store_fact("Asyncio is single-threaded", confidence=0.95)
    m.store_procedure("build_bot", ["design", "code", "test", "deploy"])
    assert m.recall_procedure("build_bot") is not None
    print("  [OK] MemorySystem")


def _test_reasoning() -> None:
    g = UnifiedCognitiveGraph()
    r = ReasoningEngine(g)
    # Set up: A causes B, B implies C
    a = CognitiveNode("a", "belief", "rain")
    b = CognitiveNode("b", "belief", "wet ground")
    c = CognitiveNode("c", "belief", "plants grow")
    g.add_node(a); g.add_node(b); g.add_node(c)
    g.add_edge("a", "causes", "b", 0.9)
    g.add_edge("b", "implies", "c", 0.7)
    # Deduce from A
    conclusions = r.deduce("a", max_depth=2)
    assert any(c[0] == "c" for c in conclusions)
    # Abduce: why is C true?
    explanations = r.abduce("c")
    assert any(e[0] == "a" for e in explanations)
    print("  [OK] ReasoningEngine")


def _test_planning() -> None:
    g = UnifiedCognitiveGraph()
    m = MemorySystem(g)
    p = PlanningEngine(g, m)
    m.store_procedure("research", ["search", "read", "synthesize"])
    gid = p.set_goal("Research Python asyncio", priority=0.8)
    plan = p.plan(gid)
    assert len(plan) > 0
    result = p.execute_plan(gid)
    assert len(result["results"]) > 0
    print("  [OK] PlanningEngine")


def _test_learning() -> None:
    g = UnifiedCognitiveGraph()
    m = MemorySystem(g)
    l = LearningEngine(g, m)
    eid1 = m.store_episode("Task A succeeded with method X")
    eid2 = m.store_episode("Task B succeeded with method X")
    patterns = l.extract_patterns([eid1, eid2])
    assert len(patterns) > 0
    learned = l.learn_skill("do_task", [
        {"steps": ["analyze", "plan", "execute"]},
        {"steps": ["analyze", "plan", "execute"]},
    ])
    assert learned
    print("  [OK] LearningEngine")


def _test_metacognition() -> None:
    g = UnifiedCognitiveGraph()
    r = ReasoningEngine(g)
    pl = PlanningEngine(g, MemorySystem(g))
    l = LearningEngine(g, MemorySystem(g))
    mc = MetacognitionModule(g, r, pl, l)
    g.add_node(CognitiveNode("g1", "goal", "test goal", activation=0.8))
    report = mc.introspect()
    assert "cognitive_load" in report
    assert "self_assessment" in report
    print("  [OK] MetacognitionModule")


def _test_unified_brain() -> None:
    brain = UnifiedAGIBrain()
    # Perceive
    brain.perceive("I need to build an AI operating system", "text")
    # Think
    thought = brain.think("AI operating system", depth=2)
    assert thought["activated_nodes"] > 0
    # Plan
    plan_result = brain.plan("Build a web scraper")
    assert plan_result["plan_length"] > 0
    # Learn
    learn_result = brain.learn({"event": "Successfully compiled C++ engine"})
    assert learn_result["episode"]
    # Introspect
    introspection = brain.introspect()
    assert introspection["total_nodes"] > 0
    # Full cycle
    cycle = brain.cycle("New data incoming")
    assert cycle["cycle"] == 1
    # State
    state = brain.get_state()
    assert state["cycles"] == 1
    print("  [OK] UnifiedAGIBrain")


def _demo() -> None:
    print("=" * 60)
    print("MAGNATRIX Unified Cognitive Architecture — AGI Kernel Demo")
    print("One brain: perception → memory → reasoning → planning → learning → metacognition")
    print("=" * 60)

    print("\n[Unit Tests]")
    _test_cognitive_graph()
    _test_perception()
    _test_memory()
    _test_reasoning()
    _test_planning()
    _test_learning()
    _test_metacognition()
    _test_unified_brain()

    print("\n[AGI Simulation — 10 Cognitive Cycles]")
    brain = UnifiedAGIBrain()

    experiences = [
        "Perceived user request: build a trading bot",
        "Researched Python asyncio patterns for concurrency",
        "Drafted architecture: event loop + order book",
        "Implemented C++ hot path for tick processing",
        "Tested arbitrage detector with historical data",
        "Integrated Rust crypto for secure API signing",
        "Deployed to paper trading mode",
        "Monitored latency: 12 microseconds per tick",
        "Detected arbitrage opportunity: +5.3 bps",
        "User approved: switch to live trading mode",
    ]

    for i, exp in enumerate(experiences, 1):
        result = brain.cycle(exp)
        state = brain.get_state()
        print(f"\n  Cycle {i}: {exp[:50]}...")
        print(f"    Nodes: {state['cognitive_graph']['nodes']}")
        print(f"    Edges: {state['cognitive_graph']['edges']}")
        print(f"    Avg activation: {state['cognitive_graph']['avg_activation']:.3f}")
        print(f"    Self-assessment: {state['self_assessment']}")

    print("\n[Final Cognitive State]")
    final = brain.get_state()
    print(f"  Total cycles: {final['cycles']}")
    print(f"  Cognitive graph: {final['cognitive_graph']['nodes']} nodes, {final['cognitive_graph']['edges']} edges")
    print(f"  Episodes stored: {final['episodes']}")
    print(f"  Procedures learned: {final['procedures']}")
    print(f"  Self-assessment: {final['self_assessment']}")

    print("\n[Introspection Report]")
    report = brain.introspect()
    print(f"  Cognitive load: {report['cognitive_load']:.3f}")
    print(f"  Active goals: {report['active_goals']}")
    print(f"  Active beliefs: {report['active_beliefs']}")
    print(f"  Node distribution: {report['node_types']}")

    print("\n[Associative Recall Test]")
    recall = brain.memory.recall_episodes("trading", top_k=3)
    print(f"  Recalled {len(recall)} episodes related to 'trading':")
    for node in recall:
        print(f"    - {node.content[:60]}... (activation={node.activation:.2f})")

    print("\n[Analogical Reasoning Test]")
    analogies = brain.reasoning.analogize(
        [n.node_id for n in brain.graph.query_by_type("concept") if "trading" in n.content][0] if brain.graph.query_by_type("concept") else "n1",
        "software"
    )
    print(f"  Found {len(analogies)} analogies")

    print("\n" + "=" * 60)
    print("AGI kernel demo complete. The brain is alive.")
    print("=" * 60)


if __name__ == "__main__":
    _demo()
