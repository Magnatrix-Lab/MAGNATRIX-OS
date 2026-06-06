#!/usr/bin/env python3
"""
Multi-Agent Collaboration for MAGNATRIX-OS
Collaborative framework where 9 agents work together, share strengths,
debate, and synthesize results. Enables cross-agent expertise pooling,
iterative refinement, and consensus building.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import json
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class CollaborationMode(enum.Enum):
    DEBATE = "debate"       # Agents debate and converge on best answer
    PIPELINE = "pipeline"   # Sequential handoff: A -> B -> C
    ENSEMBLE = "ensemble"   # All agents respond, majority vote
    SPECIALIST = "specialist" # Route to best agent per sub-task
    SYNTHESIS = "synthesis" # All contribute, one synthesizes final
    ADVERSARIAL = "adversarial" # Proposer + Critic + Refiner


class AgentRole(enum.Enum):
    PROPOSER = "proposer"   # Creates initial solution
    CRITIC = "critic"       # Reviews and finds flaws
    REFINER = "refiner"     # Improves based on feedback
    SYNTHESIZER = "synthesizer" # Combines multiple outputs
    VERIFIER = "verifier"   # Validates correctness
    SPECIALIST = "specialist" # Domain expert


@dataclasses.dataclass
class CollaborationRound:
    round_num: int
    agent_id: str
    role: AgentRole
    input_context: str
    output: str
    reasoning: str
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "round": self.round_num,
            "agent": self.agent_id,
            "role": self.role.value,
            "output": self.output[:200] + "..." if len(self.output) > 200 else self.output,
            "reasoning": self.reasoning[:200] + "..." if len(self.reasoning) > 200 else self.reasoning,
            "timestamp": self.timestamp,
        }


@dataclasses.dataclass
class CollaborationResult:
    query: str
    mode: CollaborationMode
    rounds: List[CollaborationRound]
    final_answer: str
    confidence: float
    contributing_agents: List[str]
    latency_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "mode": self.mode.value,
            "rounds": len(self.rounds),
            "final_answer": self.final_answer[:300] + "..." if len(self.final_answer) > 300 else self.final_answer,
            "confidence": self.confidence,
            "contributing_agents": self.contributing_agents,
            "latency_ms": self.latency_ms,
        }


class MultiAgentCollaboration:
    """Collaborative framework for multiple agents working together."""

    # Agent strength mapping — what each agent excels at
    STRENGTHS: Dict[str, List[str]] = {
        "hermes": ["reasoning", "explanation", "general_knowledge", "multi_turn", "summarization"],
        "openclaw": ["code_review", "refactoring", "architecture", "static_analysis", "code_quality"],
        "kimi_claw": ["long_context", "document_processing", "cross_reference", "summarization", "analysis"],
        "autoclaw": ["workflow", "automation", "planning", "tool_orchestration", "execution"],
        "opencode": ["code_generation", "testing", "documentation", "multi_language", "examples"],
        "codex": ["algorithm", "system_design", "api_design", "advanced_coding", "complexity_analysis"],
        "antigravity": ["research", "adversarial_analysis", "creative_thinking", "unconventional", "deep_dive"],
        "kimi_code": ["chinese_code", "local_stack", "framework_support", "regional_tech", "context_aware"],
        "claude_code": ["secure_coding", "ethical_ai", "safety_patterns", "responsible_ai", "review"],
    }

    # Role assignment — which agent is best for each role
    ROLE_ASSIGNMENTS: Dict[AgentRole, List[str]] = {
        AgentRole.PROPOSER: ["codex", "opencode", "hermes"],
        AgentRole.CRITIC: ["openclaw", "claude_code", "antigravity"],
        AgentRole.REFINER: ["kimi_claw", "kimi_code", "codex"],
        AgentRole.SYNTHESIZER: ["hermes", "kimi_claw", "claude_code"],
        AgentRole.VERIFIER: ["claude_code", "openclaw", "hermes"],
        AgentRole.SPECIALIST: ["antigravity", "autoclaw", "kimi_code"],
    }

    def __init__(self, connector: Any) -> None:
        self.connector = connector
        self._history: List[CollaborationResult] = []
        self._strength_match_threshold = 0.3

    # ------------------------------------------------------------------
    # Strength matching
    # ------------------------------------------------------------------

    def _match_strengths(self, query: str) -> Dict[str, float]:
        """Score each agent based on how well their strengths match the query."""
        query_lower = query.lower()
        scores = {}
        for agent_id, strengths in self.STRENGTHS.items():
            score = 0.0
            for strength in strengths:
                strength_words = strength.replace("_", " ").split()
                for word in strength_words:
                    if word in query_lower:
                        score += 1.0
            # Normalize by number of strengths
            scores[agent_id] = score / max(len(strengths), 1)
        return scores

    def _select_for_role(self, role: AgentRole, used: Set[str]) -> Optional[str]:
        """Select best available agent for a role."""
        candidates = self.ROLE_ASSIGNMENTS.get(role, [])
        for aid in candidates:
            if aid not in used:
                return aid
        # Fallback: any unused agent
        for aid in self.STRENGTHS:
            if aid not in used:
                return aid
        return None

    def _get_agent_response(self, agent_id: str, prompt: str) -> str:
        """Get response from an agent via connector."""
        if hasattr(self.connector, 'send'):
            resp = self.connector.send(agent_id, prompt)
            return resp.text if hasattr(resp, 'text') else str(resp)
        return f"[Mock response from {agent_id}]"

    # ------------------------------------------------------------------
    # Collaboration modes
    # ------------------------------------------------------------------

    def collaborate(self, query: str, mode: CollaborationMode = CollaborationMode.SYNTHESIS, max_rounds: int = 5) -> CollaborationResult:
        start = time.perf_counter()
        rounds = []
        used_agents: Set[str] = set()

        if mode == CollaborationMode.DEBATE:
            final_answer, confidence = self._debate(query, rounds, used_agents, max_rounds)
        elif mode == CollaborationMode.PIPELINE:
            final_answer, confidence = self._pipeline(query, rounds, used_agents, max_rounds)
        elif mode == CollaborationMode.ENSEMBLE:
            final_answer, confidence = self._ensemble(query, rounds, used_agents)
        elif mode == CollaborationMode.SPECIALIST:
            final_answer, confidence = self._specialist(query, rounds, used_agents)
        elif mode == CollaborationMode.ADVERSARIAL:
            final_answer, confidence = self._adversarial(query, rounds, used_agents, max_rounds)
        else:  # SYNTHESIS
            final_answer, confidence = self._synthesis(query, rounds, used_agents, max_rounds)

        latency = (time.perf_counter() - start) * 1000
        result = CollaborationResult(
            query=query,
            mode=mode,
            rounds=rounds,
            final_answer=final_answer,
            confidence=confidence,
            contributing_agents=list(used_agents),
            latency_ms=latency,
        )
        self._history.append(result)
        return result

    def _debate(self, query: str, rounds: List[CollaborationRound], used: Set[str], max_rounds: int) -> Tuple[str, float]:
        """Debate mode: Proposer -> Critic -> Refiner -> Verifier (repeat)."""
        context = query
        round_num = 1
        for _ in range(max_rounds):
            # Proposer
            proposer = self._select_for_role(AgentRole.PROPOSER, used)
            if not proposer:
                break
            used.add(proposer)
            proposal = self._get_agent_response(proposer, f"Propose a solution to: {context}")
            rounds.append(CollaborationRound(round_num, proposer, AgentRole.PROPOSER, context, proposal, "Initial proposal", time.time()))
            round_num += 1

            # Critic
            critic = self._select_for_role(AgentRole.CRITIC, used)
            if not critic:
                break
            used.add(critic)
            critique = self._get_agent_response(critic, f"Critique this proposal. Find flaws and suggest improvements: {proposal}")
            rounds.append(CollaborationRound(round_num, critic, AgentRole.CRITIC, proposal, critique, "Critical review", time.time()))
            round_num += 1

            # Refiner
            refiner = self._select_for_role(AgentRole.REFINER, used)
            if not refiner:
                break
            used.add(refiner)
            refined = self._get_agent_response(refiner, f"Refine the proposal based on critique. Proposal: {proposal}\n\nCritique: {critique}")
            rounds.append(CollaborationRound(round_num, refiner, AgentRole.REFINER, critique, refined, "Refined solution", time.time()))
            round_num += 1

            context = refined

        # Verifier final
        verifier = self._select_for_role(AgentRole.VERIFIER, used)
        if verifier:
            used.add(verifier)
            final_verification = self._get_agent_response(verifier, f"Verify and finalize this solution: {context}")
            rounds.append(CollaborationRound(round_num, verifier, AgentRole.VERIFIER, context, final_verification, "Final verification", time.time()))
            return final_verification, 0.85

        return context, 0.70

    def _pipeline(self, query: str, rounds: List[CollaborationRound], used: Set[str], max_rounds: int) -> Tuple[str, float]:
        """Pipeline: each agent adds their expertise to the output."""
        context = query
        round_num = 1
        # Determine pipeline order based on strength matching
        scores = self._match_strengths(query)
        ordered = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:max_rounds]
        for agent_id in ordered:
            used.add(agent_id)
            prompt = f"Apply your expertise ({', '.join(self.STRENGTHS.get(agent_id, []))}) to improve: {context}"
            output = self._get_agent_response(agent_id, prompt)
            rounds.append(CollaborationRound(
                round_num, agent_id, AgentRole.SPECIALIST,
                context, output, f"Applied {self.STRENGTHS.get(agent_id, [])[0] if self.STRENGTHS.get(agent_id) else 'expertise'}",
                time.time()
            ))
            context = output
            round_num += 1
        return context, 0.75 + (0.02 * len(ordered))

    def _ensemble(self, query: str, rounds: List[CollaborationRound], used: Set[str]) -> Tuple[str, float]:
        """Ensemble: all agents respond, pick the best."""
        responses = {}
        for agent_id in list(self.STRENGTHS.keys())[:5]:  # Limit to 5 for speed
            used.add(agent_id)
            output = self._get_agent_response(agent_id, query)
            responses[agent_id] = output
            rounds.append(CollaborationRound(
                len(rounds) + 1, agent_id, AgentRole.SPECIALIST,
                query, output, "Ensemble contribution", time.time()
            ))
        # Synthesizer picks best
        synthesizer = self._select_for_role(AgentRole.SYNTHESIZER, used)
        if synthesizer:
            used.add(synthesizer)
            all_resp = "\n\n".join(f"[{k}] {v}" for k, v in responses.items())
            final = self._get_agent_response(synthesizer, f"Select the best answer from these options:\n\n{all_resp}")
            rounds.append(CollaborationRound(
                len(rounds) + 1, synthesizer, AgentRole.SYNTHESIZER,
                all_resp, final, "Selected best from ensemble", time.time()
            ))
            return final, 0.80
        # Fallback: return longest response (proxy for quality)
        best = max(responses.items(), key=lambda x: len(x[1]))
        return best[1], 0.65

    def _specialist(self, query: str, rounds: List[CollaborationRound], used: Set[str]) -> Tuple[str, float]:
        """Specialist: route to the single best agent."""
        scores = self._match_strengths(query)
        best_agent = max(scores.keys(), key=lambda x: scores[x])
        used.add(best_agent)
        output = self._get_agent_response(best_agent, query)
        rounds.append(CollaborationRound(
            1, best_agent, AgentRole.SPECIALIST,
            query, output, f"Best match for query (score: {scores[best_agent]:.2f})", time.time()
        ))
        return output, min(0.50 + scores[best_agent] * 2, 0.95)

    def _adversarial(self, query: str, rounds: List[CollaborationRound], used: Set[str], max_rounds: int) -> Tuple[str, float]:
        """Adversarial: Proposer -> Critic -> Refiner (iterate)."""
        context = query
        round_num = 1
        for _ in range(max_rounds // 3):
            # Proposer
            proposer = self._select_for_role(AgentRole.PROPOSER, used)
            if not proposer:
                break
            used.add(proposer)
            proposal = self._get_agent_response(proposer, f"Propose: {context}")
            rounds.append(CollaborationRound(round_num, proposer, AgentRole.PROPOSER, context, proposal, "Proposed solution", time.time()))
            round_num += 1

            # Critic
            critic = self._select_for_role(AgentRole.CRITIC, used)
            if not critic:
                break
            used.add(critic)
            critique = self._get_agent_response(critic, f"Critique harshly. Find ALL flaws: {proposal}")
            rounds.append(CollaborationRound(round_num, critic, AgentRole.CRITIC, proposal, critique, "Harsh critique", time.time()))
            round_num += 1

            # Refiner
            refiner = self._select_for_role(AgentRole.REFINER, used)
            if not refiner:
                break
            used.add(refiner)
            refined = self._get_agent_response(refiner, f"Address ALL critiques and produce improved version.\n\nProposal: {proposal}\n\nCritique: {critique}")
            rounds.append(CollaborationRound(round_num, refiner, AgentRole.REFINER, critique, refined, "Addressed critiques", time.time()))
            round_num += 1

            context = refined

        return context, 0.88

    def _synthesis(self, query: str, rounds: List[CollaborationRound], used: Set[str], max_rounds: int) -> Tuple[str, float]:
        """Synthesis: gather from multiple agents, synthesize into one answer."""
        # Gather from 3-5 agents
        scores = self._match_strengths(query)
        top_agents = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:min(5, max_rounds)]
        contributions = {}
        round_num = 1
        for agent_id in top_agents:
            used.add(agent_id)
            output = self._get_agent_response(agent_id, f"Using your expertise, answer this question: {query}")
            contributions[agent_id] = output
            rounds.append(CollaborationRound(
                round_num, agent_id, AgentRole.SPECIALIST,
                query, output, f"Expertise: {', '.join(self.STRENGTHS.get(agent_id, [])[:3])}",
                time.time()
            ))
            round_num += 1

        # Synthesizer combines all
        synthesizer = self._select_for_role(AgentRole.SYNTHESIZER, used)
        if synthesizer:
            used.add(synthesizer)
            all_contrib = "\n\n---\n\n".join(f"[{k}] {v}" for k, v in contributions.items())
            final = self._get_agent_response(synthesizer, f"Synthesize a unified, comprehensive answer from these expert contributions:\n\n{all_contrib}")
            rounds.append(CollaborationRound(
                round_num, synthesizer, AgentRole.SYNTHESIZER,
                all_contrib, final, "Synthesized unified answer", time.time()
            ))
            return final, 0.90

        # Fallback: concatenate
        return "\n\n".join(contributions.values()), 0.60

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_history(self, limit: int = 100) -> List[CollaborationResult]:
        return self._history[-limit:]

    def get_strengths(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        if agent_id:
            return {agent_id: self.STRENGTHS.get(agent_id, [])}
        return dict(self.STRENGTHS)

    def stats(self) -> Dict[str, Any]:
        by_mode = {}
        for r in self._history:
            by_mode[r.mode.value] = by_mode.get(r.mode.value, 0) + 1
        return {
            "total_collaborations": len(self._history),
            "by_mode": by_mode,
            "avg_rounds": sum(len(r.rounds) for r in self._history) / max(1, len(self._history)),
            "avg_confidence": sum(r.confidence for r in self._history) / max(1, len(self._history)),
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    # Mock connector for demo
    class MockConnector:
        def send(self, agent_id: str, prompt: str):
            class MockResp:
                text = f"[{agent_id}] Response based on: {prompt[:50]}..."
            return MockResp()

    collab = MultiAgentCollaboration(MockConnector())
    print("=== Multi-Agent Collaboration Demo ===\n")
    print("Agent strengths:")
    for aid, strengths in collab.get_strengths().items():
        print(f"  {aid}: {', '.join(strengths[:3])}")

    query = "Design a secure authentication system for a web application"

    print(f"\nQuery: {query}")
    for mode in [CollaborationMode.SPECIALIST, CollaborationMode.SYNTHESIS, CollaborationMode.DEBATE]:
        print(f"\n--- {mode.value.upper()} ---")
        result = collab.collaborate(query, mode=mode, max_rounds=4)
        print(f"  Rounds: {len(result.rounds)}")
        print(f"  Agents: {result.contributing_agents}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Final: {result.final_answer[:100]}...")
        print(f"  Round details:")
        for r in result.rounds:
            print(f"    Round {r.round_num}: {r.agent_id} as {r.role.value} -> {r.output[:60]}...")

    print(f"\nStats: {collab.stats()}")


if __name__ == "__main__":
    _demo()
