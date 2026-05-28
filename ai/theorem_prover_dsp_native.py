"""
native_theorem_prover.py — Draft/Sketch/Prove pipeline with planner abstraction.

Architectural patterns extracted from microsoft/Planners-for-Theorem-Proving:
- Planner abstraction separating strategy selection from execution.
- Proof state machine tracking goals, assumptions, and transformations.
- Lemma decomposition via backward-chaining with heuristics.
- Heuristic scoring for rule/axiom selection.
- Iterative deepening / retry loops when proof branches fail.

Pure Python ≥3.9, stdlib only. Callback-based LLM hook if needed.
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

class ProofStatus(Enum):
    UNKNOWN = auto()
    PROVED = auto()
    DISPROVED = auto()
    TIMEOUT = auto()

@dataclass(frozen=True)
class Term:
    """Immutable first-order-ish term."""
    name: str
    args: Tuple["Term", ...] = ()

    def __str__(self) -> str:
        if not self.args:
            return self.name
        return f"{self.name}({', '.join(str(a) for a in self.args)})"

@dataclass
class Goal:
    """A goal to be proved:  assumptions ⊢ conclusion."""
    assumptions: List[Term] = field(default_factory=list)
    conclusion: Term = field(default_factory=lambda: Term("True"))

    def copy(self) -> Goal:
        return Goal(list(self.assumptions), self.conclusion)

@dataclass
class ProofState:
    """Current proof node."""
    goal: Goal
    depth: int = 0
    history: List[str] = field(default_factory=list)
    status: ProofStatus = ProofStatus.UNKNOWN

    def copy(self) -> "ProofState":
        return ProofState(self.goal.copy(), self.depth, list(self.history), self.status)

# ---------------------------------------------------------------------------
# Rules / Axioms
# ---------------------------------------------------------------------------

Rule = Callable[[ProofState], Optional[List[ProofState]]]

class RuleRegistry:
    """Lightweight rule book with heuristic weights."""

    def __init__(self) -> None:
        self._rules: Dict[str, Tuple[float, Rule]] = {}

    def register(self, name: str, weight: float, rule: Rule) -> None:
        self._rules[name] = (weight, rule)

    def candidates(self, state: ProofState) -> List[Tuple[str, float, Rule]]:
        """Return rules that apply, sorted by ascending heuristic cost."""
        applicable: List[Tuple[str, float, Rule]] = []
        for name, (w, rule) in self._rules.items():
            result = rule(state)
            if result is not None:
                applicable.append((name, w, rule))
        applicable.sort(key=lambda t: t[1])
        return applicable

# ---------------------------------------------------------------------------
# Planner abstraction
# ---------------------------------------------------------------------------

PlannerScore = Callable[[ProofState, str, float], float]

class NativePlanner:
    """Selects which rule to try next based on heuristic scoring."""

    def __init__(
        self,
        registry: RuleRegistry,
        score_fn: Optional[PlannerScore] = None,
    ) -> None:
        self.registry = registry
        self.score_fn = score_fn or (lambda _st, _name, w: w)

    def next_moves(self, state: ProofState) -> List[Tuple[str, Rule]]:
        scored: List[Tuple[float, str, Rule]] = []
        for name, weight, rule in self.registry.candidates(state):
            s = self.score_fn(state, name, weight)
            scored.append((s, name, rule))
        scored.sort(key=lambda t: t[0])
        return [(name, rule) for _, name, rule in scored]

# ---------------------------------------------------------------------------
# Draft → Sketch → Prove pipeline
# ---------------------------------------------------------------------------

class NativeTheoremProver:
    """
    Draft/Sketch/Prove pipeline.

    - Draft:  expand goal with available lemmas / axioms (breadth-first outline).
    - Sketch: heuristic search selecting most promising branches.
    - Prove:  deep expansion with backtracking until QED or timeout.
    """

    def __init__(
        self,
        registry: RuleRegistry,
        planner: Optional[NativePlanner] = None,
        max_depth: int = 12,
        max_branching: int = 3,
        llm_fn: Optional[Callable[[str], str]] = None,
    ) -> None:
        self.registry = registry
        self.planner = planner or NativePlanner(registry)
        self.max_depth = max_depth
        self.max_branching = max_branching
        self.llm_fn = llm_fn

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, goal: Goal) -> ProofState:
        """Run the full pipeline and return final state."""
        draft = self._draft(goal)
        sketch = self._sketch(draft)
        proved = self._prove(sketch)
        return proved

    def execute(self, conclusion: str, assumptions: Optional[List[str]] = None) -> ProofState:
        """Convenience: build Goal from strings and run."""
        assms = [self._parse(a) for a in (assumptions or [])]
        concl = self._parse(conclusion)
        return self.run(Goal(assms, concl))

    # ------------------------------------------------------------------
    # Phase 1 — Draft (breadth-first lemma decomposition)
    # ------------------------------------------------------------------

    def _draft(self, root: Goal) -> ProofState:
        """Generate shallow expansion to seed the search space."""
        state = ProofState(root.copy(), depth=0, history=["draft:start"])
        # One-ply expansion
        children = self._expand(state, limit=5)
        if not children:
            return state
        # Return best child by shallow heuristic
        best = min(children, key=lambda s: self._heuristic(s))
        best.history.insert(0, "draft:expanded")
        return best

    # ------------------------------------------------------------------
    # Phase 2 — Sketch (best-first search)
    # ------------------------------------------------------------------

    def _sketch(self, state: ProofState) -> ProofState:
        """Explore promising branches with limited depth."""
        frontier: List[Tuple[float, int, ProofState]] = []
        counter = 0
        heapq.heappush(frontier, (self._heuristic(state), counter, state))
        visited: Set[str] = set()

        while frontier:
            _, _, current = heapq.heappop(frontier)
            sig = self._signature(current)
            if sig in visited:
                continue
            visited.add(sig)

            if self._is_trivial(current):
                current.status = ProofStatus.PROVED
                current.history.append("sketch:trivial")
                return current

            if current.depth >= self.max_depth // 2:
                current.history.append("sketch:depth_cap")
                return current

            children = self._expand(current, limit=self.max_branching)
            for child in children:
                counter += 1
                child.history.append("sketch:branch")
                heapq.heappush(frontier, (self._heuristic(child), counter, child))

        state.status = ProofStatus.TIMEOUT
        state.history.append("sketch:empty_frontier")
        return state

    # ------------------------------------------------------------------
    # Phase 3 — Prove (deep backtracking DFS with iterative deepening)
    # ------------------------------------------------------------------

    def _prove(self, state: ProofState) -> ProofState:
        """Deep deterministic search with backtracking."""
        for limit in range(state.depth, self.max_depth + 1):
            result = self._dfs(state.copy(), limit)
            if result.status == ProofStatus.PROVED:
                return result
        state.status = ProofStatus.TIMEOUT
        state.history.append("prove:timeout")
        return state

    def _dfs(self, state: ProofState, limit: int) -> ProofState:
        if self._is_trivial(state):
            state.status = ProofStatus.PROVED
            state.history.append(f"dfs:proved_at_{state.depth}")
            return state
        if state.depth >= limit:
            state.status = ProofStatus.UNKNOWN
            return state

        moves = self.planner.next_moves(state)
        for name, rule in moves[: self.max_branching]:
            expansions = rule(state)
            if not expansions:
                continue
            for child in expansions:
                child.depth = state.depth + 1
                child.history = list(state.history) + [f"apply:{name}"]
                res = self._dfs(child, limit)
                if res.status == ProofStatus.PROVED:
                    return res
        state.status = ProofStatus.DISPROVED
        return state

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _expand(self, state: ProofState, limit: int) -> List[ProofState]:
        """Shallow expansion of a state."""
        moves = self.planner.next_moves(state)
        children: List[ProofState] = []
        for name, rule in moves[:limit]:
            result = rule(state)
            if result:
                for child in result:
                    child.depth = state.depth + 1
                    child.history = list(state.history) + [f"expand:{name}"]
                    children.append(child)
        return children

    def _heuristic(self, state: ProofState) -> float:
        """Lower is better."""
        # Prefer shallow, fewer assumptions, smaller terms
        return float(state.depth) + len(state.goal.assumptions) * 0.5

    def _is_trivial(self, state: ProofState) -> bool:
        """Trivial = conclusion already in assumptions."""
        return any(self._same(t, state.goal.conclusion) for t in state.goal.assumptions)

    def _same(self, a: Term, b: Term) -> bool:
        return a.name == b.name and len(a.args) == len(b.args) and all(
            self._same(x, y) for x, y in zip(a.args, b.args)
        )

    def _signature(self, state: ProofState) -> str:
        return f"{state.goal.conclusion}:{','.join(str(a) for a in state.goal.assumptions)}"

    def _parse(self, text: str) -> Term:
        """Naïve parser: 'P' → Term('P'); 'P(x,y)' → Term('P', (Term('x'), Term('y')))."""
        text = text.strip()
        if "(" not in text:
            return Term(text)
        name, rest = text.split("(", 1)
        rest = rest.rstrip(")")
        args = [self._parse(a.strip()) for a in rest.split(",")]
        return Term(name.strip(), tuple(args))

# ---------------------------------------------------------------------------
# Built-in example rules
# ---------------------------------------------------------------------------

def build_default_registry() -> RuleRegistry:
    """A tiny rule set demonstrating modus-ponens-like chaining."""
    reg = RuleRegistry()

    def _modus_ponens(state: ProofState) -> Optional[List[ProofState]]:
        g = state.goal
        for a in g.assumptions:
            if a.name == "implies" and len(a.args) == 2:
                if prover._same(a.args[1], g.conclusion):
                    new = g.copy()
                    new.conclusion = a.args[0]
                    return [ProofState(new)]
        return None

    def _and_elim(state: ProofState) -> Optional[List[ProofState]]:
        return None  # trivial case handled by _is_trivial

    def _and_intro(state: ProofState) -> Optional[List[ProofState]]:
        g = state.goal
        if g.conclusion.name == "and" and len(g.conclusion.args) == 2:
            left = g.copy()
            left.conclusion = g.conclusion.args[0]
            right = g.copy()
            right.conclusion = g.conclusion.args[1]
            return [ProofState(left), ProofState(right)]
        return None

    def _llm_lemma(state: ProofState) -> Optional[List[ProofState]]:
        if prover.llm_fn is None:
            return None
        prompt = f"Given assumptions {', '.join(str(a) for a in state.goal.assumptions)} prove {state.goal.conclusion}. Suggest one lemma term."
        response = prover.llm_fn(prompt).strip()
        if response:
            try:
                lemma = prover._parse(response)
                new = state.goal.copy()
                new.assumptions.append(lemma)
                return [ProofState(new)]
            except Exception:
                return None
        return None

    reg.register("modus_ponens", 1.0, _modus_ponens)
    reg.register("and_elim", 2.0, _and_elim)
    reg.register("and_intro", 1.5, _and_intro)
    reg.register("llm_lemma", 5.0, _llm_lemma)
    return reg

# Global helper for closures above
prover: NativeTheoremProver

# ---------------------------------------------------------------------------
# Main demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    reg = build_default_registry()
    prover = NativeTheoremProver(reg, max_depth=8)

    # Demo 1: trivial proof
    g1 = Goal([Term("P")], Term("P"))
    r1 = prover.run(g1)
    print("=== Demo 1: Trivial ===")
    print(f"Status: {r1.status.name}")
    print(f"History: {r1.history}")
    print()

    # Demo 2: modus ponens
    # assumptions: implies(P, Q), P  ⊢ Q
    g2 = Goal(
        [Term("implies", (Term("P"), Term("Q"))), Term("P")],
        Term("Q"),
    )
    r2 = prover.run(g2)
    print("=== Demo 2: Modus Ponens ===")
    print(f"Status: {r2.status.name}")
    print(f"History: {r2.history}")
    print()

    # Demo 3: conjunction introduction
    # assumptions: P, Q  ⊢ and(P, Q)
    g3 = Goal(
        [Term("P"), Term("Q")],
        Term("and", (Term("P"), Term("Q"))),
    )
    r3 = prover.run(g3)
    print("=== Demo 3: Conjunction Intro ===")
    print(f"Status: {r3.status.name}")
    print(f"History: {r3.history}")
    print()

    # Demo 4: LLM-guided lemma (mock)
    def mock_llm(_prompt: str) -> str:
        return "lemma_helper()"

    prover_llm = NativeTheoremProver(reg, llm_fn=mock_llm, max_depth=6)
    g4 = Goal([Term("A")], Term("B"))
    r4 = prover_llm.run(g4)
    print("=== Demo 4: LLM Lemma ===")
    print(f"Status: {r4.status.name}")
    print(f"History: {r4.history}")
    print()

    print("All demos completed.")
