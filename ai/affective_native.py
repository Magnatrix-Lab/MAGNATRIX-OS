#!/usr/bin/env python3
"""Affective Computing — MAGNATRIX-OS ASI Expansion"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

@dataclass
class AffectiveState:
    pleasure: float = 0.0
    arousal: float = 0.0
    dominance: float = 0.0

    def distance(self, other: AffectiveState) -> float:
        return math.sqrt((self.pleasure - other.pleasure)**2 + (self.arousal - other.arousal)**2 + (self.dominance - other.dominance)**2)

    def copy(self) -> AffectiveState:
        return AffectiveState(self.pleasure, self.arousal, self.dominance)

    def to_emotion_label(self) -> str:
        p, a, d = self.pleasure, self.arousal, self.dominance
        if p > 0.5 and a > 0.3: return "joy"
        if p < -0.5 and a > 0.3: return "distress"
        if p < -0.3 and a < -0.3 and d < 0: return "fear"
        if p < -0.5 and a > 0 and d > 0: return "anger"
        if p > 0 and a < -0.3: return "contentment"
        if a > 0.5 and abs(p) < 0.3: return "surprise"
        if p > 0.3 and a > 0 and d > 0: return "pride"
        return "neutral"

@dataclass
class Personality:
    sensitivity: float = 0.5
    resilience: float = 0.5
    optimism: float = 0.5

@dataclass
class EmotionalEvent:
    valence: float = 0.0
    intensity: float = 0.5
    uncertainty: float = 0.0
    agent_id: str = ""

def clamp(v: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))

class EmotionalReaction:
    def __init__(self, personality: Personality) -> None:
        self.personality = personality

    def react(self, event: EmotionalEvent, current: AffectiveState) -> AffectiveState:
        s = self.personality.sensitivity
        delta_p = event.valence * event.intensity * s + self.personality.optimism * 0.1
        delta_a = event.intensity * s + event.uncertainty * 0.5 * s
        delta_d = (event.valence * 0.5 - event.uncertainty * 0.3) * s
        new_state = current.copy()
        new_state.pleasure = clamp(new_state.pleasure + delta_p)
        new_state.arousal = clamp(new_state.arousal + delta_a)
        new_state.dominance = clamp(new_state.dominance + delta_d)
        return new_state

class EmpathySimulator:
    def infer(self, context: Dict[str, Any]) -> AffectiveState:
        valence, arousal, dominance = 0.0, 0.0, 0.0
        if context.get("success", False):
            valence += 0.7; dominance += 0.3
        if context.get("failure", False):
            valence -= 0.6; arousal += 0.2
        if context.get("threat", False):
            arousal += 0.7; valence -= 0.5; dominance -= 0.3
        if context.get("reward", 0) > 0:
            valence += context["reward"] * 0.05
        if context.get("social_support", False):
            valence += 0.3; arousal -= 0.2
        return AffectiveState(clamp(valence), clamp(arousal), clamp(dominance))

    def accuracy(self, inferred: AffectiveState, actual: AffectiveState) -> float:
        dist = inferred.distance(actual)
        return max(0, 1 - dist / 2)

class EmotionRegulator:
    def __init__(self, rate: float = 0.1) -> None:
        self.rate = rate

    def regulate(self, current: AffectiveState, target: AffectiveState) -> AffectiveState:
        result = current.copy()
        result.pleasure += (target.pleasure - current.pleasure) * self.rate
        result.arousal += (target.arousal - current.arousal) * self.rate
        result.dominance += (target.dominance - current.dominance) * self.rate
        return result

    def dampen(self, current: AffectiveState, factor: float = 0.9) -> AffectiveState:
        result = current.copy()
        result.pleasure *= factor
        result.arousal *= factor
        result.dominance *= factor
        return result

class AffectiveNetwork:
    def __init__(self, contagion_rate: float = 0.05) -> None:
        self.agents: Dict[str, AffectiveState] = {}
        self.personalities: Dict[str, Personality] = {}
        self.connections: Dict[str, List[str]] = {}
        self.contagion_rate = contagion_rate

    def add_agent(self, agent_id: str, state: AffectiveState, personality: Personality) -> None:
        self.agents[agent_id] = state
        self.personalities[agent_id] = personality
        self.connections[agent_id] = []

    def connect(self, a: str, b: str) -> None:
        if b not in self.connections.get(a, []):
            self.connections[a].append(b)
        if a not in self.connections.get(b, []):
            self.connections[b].append(a)

    def step(self) -> None:
        deltas: Dict[str, AffectiveState] = {}
        for aid, state in self.agents.items():
            neighbors = self.connections.get(aid, [])
            if not neighbors:
                continue
            avg_p = sum(self.agents[n].pleasure for n in neighbors) / len(neighbors)
            avg_a = sum(self.agents[n].arousal for n in neighbors) / len(neighbors)
            avg_d = sum(self.agents[n].dominance for n in neighbors) / len(neighbors)
            deltas[aid] = AffectiveState(
                (avg_p - state.pleasure) * self.contagion_rate,
                (avg_a - state.arousal) * self.contagion_rate,
                (avg_d - state.dominance) * self.contagion_rate,
            )
        for aid, delta in deltas.items():
            self.agents[aid].pleasure = clamp(self.agents[aid].pleasure + delta.pleasure)
            self.agents[aid].arousal = clamp(self.agents[aid].arousal + delta.arousal)
            self.agents[aid].dominance = clamp(self.agents[aid].dominance + delta.dominance)

    def variance(self) -> float:
        if len(self.agents) < 2:
            return 0.0
        pleasures = [s.pleasure for s in self.agents.values()]
        mean = sum(pleasures) / len(pleasures)
        return sum((p - mean) ** 2 for p in pleasures) / len(pleasures)

def _self_test() -> int:
    passed = 0
    total = 0
    def check(name, condition):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print("  [PASS] " + name)
        else:
            print("  [FAIL] " + name)

    print("=" * 55)
    print("Affective Computing — Self Test")
    print("=" * 55)

    print("\n[1] Positive event -> joy")
    person = Personality(sensitivity=0.7, optimism=0.3)
    reactor = EmotionalReaction(person)
    state = reactor.react(EmotionalEvent(valence=0.9, intensity=0.8), AffectiveState())
    check("Pleasure increased", state.pleasure > 0.5)
    check("Arousal increased", state.arousal > 0.3)
    check("Emotion label is joy", state.to_emotion_label() == "joy")

    print("\n[2] Threat -> fear")
    state2 = reactor.react(EmotionalEvent(valence=-0.5, intensity=0.7, uncertainty=0.8), AffectiveState())
    check("Arousal high under threat", state2.arousal > 0.3)
    check("Dominance drops", state2.dominance < 0)
    check("Emotion is fear/distress", state2.to_emotion_label() in ("fear", "distress"))

    print("\n[3] Empathy inference")
    empathy = EmpathySimulator()
    inferred = empathy.infer({"success": True, "reward": 10})
    check("Success inferred as positive", inferred.pleasure > 0)
    accuracy = empathy.accuracy(inferred, AffectiveState(pleasure=0.8, arousal=0.2))
    check("Empathy accuracy reasonable", accuracy > 0.5)

    print("\n[4] Emotion regulation")
    reg = EmotionRegulator(rate=0.2)
    upset = AffectiveState(pleasure=-0.8, arousal=0.6)
    calm_target = AffectiveState(pleasure=0.0, arousal=-0.2)
    regulated = reg.regulate(upset, calm_target)
    check("Regulation moves toward target", regulated.pleasure > upset.pleasure)
    dampened = reg.dampen(upset, factor=0.5)
    check("Dampen reduces intensity", abs(dampened.pleasure) < abs(upset.pleasure))

    print("\n[5] Emotional contagion")
    net = AffectiveNetwork(contagion_rate=0.1)
    net.add_agent("A", AffectiveState(pleasure=0.8), Personality())
    net.add_agent("B", AffectiveState(pleasure=-0.5), Personality())
    net.connect("A", "B")
    for _ in range(20):
        net.step()
    check("B became more positive", net.agents["B"].pleasure > -0.5)
    check("Variance decreased", net.variance() < 0.5)

    print("\n[6] Personality differences")
    sensitive = Personality(sensitivity=0.9)
    stoic = Personality(sensitivity=0.2)
    r1 = EmotionalReaction(sensitive)
    r2 = EmotionalReaction(stoic)
    ev = EmotionalEvent(valence=0.5, intensity=0.8)
    s1 = r1.react(ev, AffectiveState())
    s2 = r2.react(ev, AffectiveState())
    check("Sensitive reacts stronger", s1.pleasure > s2.pleasure)

    print("\n[7] PAD to emotion labels")
    joy = AffectiveState(0.8, 0.5, 0.3)
    fear = AffectiveState(-0.6, 0.7, -0.4)
    anger = AffectiveState(-0.7, 0.6, 0.8)
    check("Joy label", joy.to_emotion_label() == "joy")
    check("Fear label", fear.to_emotion_label() == "fear")
    check("Anger label", anger.to_emotion_label() == "anger")

    print("\n" + "=" * 55)
    print("PASS: " + str(passed) + "/" + str(total))
    print("=" * 55)
    return 0 if passed == total else 1

if __name__ == "__main__":
    import sys
    sys.exit(_self_test())