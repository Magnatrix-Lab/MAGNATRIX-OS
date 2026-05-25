#!/usr/bin/env python3
"""
theorem_prover_native.py — MAGNATRIX-OS AI Layer
Pure-Python symbolic theorem prover with tactic engine, tree search, and heuristic scoring.
No external dependencies. Runnable standalone.

Architecture:
  BaseLayer   — Expressions, Formulas, Unification, Substitution
  CoreEngine  — TacticEngine, ProofState, SearchEngine (BFS/DFS/Best-First)
  Features    — PatternLibrary, AxiomSet, GoalReducer, ProofPrinter, HeuristicScorer
  Kernel      — TheoremProverKernel bridge to MAGNATRIX Layer 9 (AI/Reasoning)

Influences: BFS-Prover (length-normalized best-first search), Proverbot9001 (neural tactic
prediction + depth-first search), AlphaProof (MCTS + PUCT for theorem proving), LeanDojo
(gym-like environment for proof assistants).
"""

from __future__ import annotations

import ast
import heapq
import inspect
import json
import os
import re
import sys
import textwrap
import time
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

# ═══════════════════════════════════════════════════════════════════════════════
# BASELAYER — Expressions, Formulas, Unification, Substitution
# ═══════════════════════════════════════════════════════════════════════════════

class ExprType(Enum):
    """Classification of expression nodes."""
    VAR = auto()      # Variable: x, y, P, Q
    CONST = auto()    # Constant: 0, 1, true, false
    FUNC = auto()     # Function application: f(t1, t2, ...)
    PRED = auto()     # Predicate: P(t1, t2)
    FORALL = auto()   # Universal quantifier
    EXISTS = auto()   # Existential quantifier
    NOT = auto()      # Negation
    AND = auto()      # Conjunction
    OR = auto()       # Disjunction
    IMPLIES = auto()  # Implication
    IFF = auto()      # Biconditional
    EQ = auto()       # Equality


@dataclass(frozen=True)
class Expr:
    """
    Immutable symbolic expression node.
    Pure functional: all operations return new Expr instances.
    """
    kind: ExprType
    name: str = ""                # For VAR, CONST, FUNC, PRED
    args: Tuple[Expr, ...] = ()   # For FUNC, PRED, and logical connectives
    var: Optional[str] = None     # For FORALL, EXISTS (bound variable)
    body: Optional[Expr] = None  # For FORALL, EXISTS (body expression)

    # ── Constructors ─────────────────────────────────────────────────────────

    @staticmethod
    def var(name: str) -> Expr:
        return Expr(ExprType.VAR, name=name)

    @staticmethod
    def const(name: str) -> Expr:
        return Expr(ExprType.CONST, name=name)

    @staticmethod
    def func(name: str, *args: Expr) -> Expr:
        return Expr(ExprType.FUNC, name=name, args=args)

    @staticmethod
    def pred(name: str, *args: Expr) -> Expr:
        return Expr(ExprType.PRED, name=name, args=args)

    @staticmethod
    def forall(var_name: str, body: Expr) -> Expr:
        return Expr(ExprType.FORALL, var=var_name, body=body)

    @staticmethod
    def exists(var_name: str, body: Expr) -> Expr:
        return Expr(ExprType.EXISTS, var=var_name, body=body)

    @staticmethod
    def not_(e: Expr) -> Expr:
        return Expr(ExprType.NOT, args=(e,))

    @staticmethod
    def and_(a: Expr, b: Expr) -> Expr:
        return Expr(ExprType.AND, args=(a, b))

    @staticmethod
    def or_(a: Expr, b: Expr) -> Expr:
        return Expr(ExprType.OR, args=(a, b))

    @staticmethod
    def implies(a: Expr, b: Expr) -> Expr:
        return Expr(ExprType.IMPLIES, args=(a, b))

    @staticmethod
    def iff(a: Expr, b: Expr) -> Expr:
        return Expr(ExprType.IFF, args=(a, b))

    @staticmethod
    def eq(a: Expr, b: Expr) -> Expr:
        return Expr(ExprType.EQ, args=(a, b))

    # ── Traversal ──────────────────────────────────────────────────────────

    def vars(self) -> Set[str]:
        """All free variable names appearing in this expression."""
        result: Set[str] = set()
        if self.kind == ExprType.VAR:
            result.add(self.name)
        elif self.kind in (ExprType.FORALL, ExprType.EXISTS):
            if self.body:
                body_vars = self.body.vars()
                body_vars.discard(self.var or "")
                result.update(body_vars)
        elif self.args:
            for arg in self.args:
                result.update(arg.vars())
        return result

    def subst(self, mapping: Dict[str, Expr]) -> Expr:
        """Apply substitution mapping to this expression."""
        if self.kind == ExprType.VAR and self.name in mapping:
            return mapping[self.name]
        if self.kind in (ExprType.FORALL, ExprType.EXISTS):
            if self.body is None:
                return self
            new_mapping = {k: v for k, v in mapping.items() if k != self.var}
            return Expr(
                kind=self.kind,
                var=self.var,
                body=self.body.subst(new_mapping),
            )
        if self.args:
            new_args = tuple(arg.subst(mapping) for arg in self.args)
            return Expr(kind=self.kind, name=self.name, args=new_args)
        return self

    def __str__(self) -> str:
        if self.kind == ExprType.VAR:
            return self.name
        if self.kind == ExprType.CONST:
            return self.name
        if self.kind in (ExprType.FUNC, ExprType.PRED):
            inner = ", ".join(str(a) for a in self.args)
            return f"{self.name}({inner})"
        if self.kind == ExprType.FORALL:
            return f"∀{self.var}. {self.body}"
        if self.kind == ExprType.EXISTS:
            return f"∃{self.var}. {self.body}"
        if self.kind == ExprType.NOT:
            return f"¬{self.args[0]}"
        if self.kind == ExprType.AND:
            return f"({self.args[0]} ∧ {self.args[1]})"
        if self.kind == ExprType.OR:
            return f"({self.args[0]} ∨ {self.args[1]})"
        if self.kind == ExprType.IMPLIES:
            return f"({self.args[0]} → {self.args[1]})"
        if self.kind == ExprType.IFF:
            return f"({self.args[0]} ↔ {self.args[1]})"
        if self.kind == ExprType.EQ:
            return f"({self.args[0]} = {self.args[1]})"
        return "<?>"

    def __repr__(self) -> str:
        return str(self)


# ── Formula / Sequent helpers ──────────────────────────────────────────────

Formula = Expr  # alias for clarity in proof contexts


@dataclass
class Sequent:
    """
    A sequent: hypotheses ⊢ goal
    Standard natural deduction style.
    """
    hypotheses: List[Formula] = field(default_factory=list)
    goal: Optional[Formula] = None
    label: str = ""  # Optional human-readable label

    def __str__(self) -> str:
        lhs = ", ".join(str(h) for h in self.hypotheses) if self.hypotheses else "∅"
        rhs = str(self.goal) if self.goal else "?"
        return f"[{self.label}] {lhs} ⊢ {rhs}"


# ── Unification Engine ─────────────────────────────────────────────────────

class UnificationError(Exception):
    """Raised when two expressions cannot be unified."""
    pass


class Unifier:
    """
    Robinson-style first-order unification.
    Returns a substitution mapping or raises UnificationError.
    """

    @staticmethod
    def unify(a: Expr, b: Expr) -> Dict[str, Expr]:
        subst: Dict[str, Expr] = {}
        Unifier._unify(a, b, subst)
        return subst

    @staticmethod
    def _unify(a: Expr, b: Expr, subst: Dict[str, Expr]) -> None:
        a = Unifier._apply_partial(a, subst)
        b = Unifier._apply_partial(b, subst)

        if a.kind == ExprType.VAR and a.name not in subst:
            if Unifier._occurs_check(a.name, b):
                raise UnificationError(f"Occurs check failed: {a.name} in {b}")
            subst[a.name] = b
            return

        if b.kind == ExprType.VAR and b.name not in subst:
            if Unifier._occurs_check(b.name, a):
                raise UnificationError(f"Occurs check failed: {b.name} in {a}")
            subst[b.name] = a
            return

        if a.kind != b.kind:
            raise UnificationError(f"Kind mismatch: {a.kind} vs {b.kind}")

        if a.kind in (ExprType.VAR, ExprType.CONST):
            if a.name != b.name:
                raise UnificationError(f"Name mismatch: {a.name} vs {b.name}")
            return

        if a.kind in (ExprType.FORALL, ExprType.EXISTS):
            if a.var != b.var:
                raise UnificationError(f"Bound var mismatch: {a.var} vs {b.var}")
            Unifier._unify(a.body or Expr.const(""), b.body or Expr.const(""), subst)
            return

        if a.name != b.name:
            raise UnificationError(f"Name mismatch: {a.name} vs {b.name}")

        if len(a.args) != len(b.args):
            raise UnificationError(f"Arity mismatch: {len(a.args)} vs {len(b.args)}")

        for arg_a, arg_b in zip(a.args, b.args):
            Unifier._unify(arg_a, arg_b, subst)

    @staticmethod
    def _apply_partial(e: Expr, subst: Dict[str, Expr]) -> Expr:
        if e.kind == ExprType.VAR and e.name in subst:
            return subst[e.name]
        return e

    @staticmethod
    def _occurs_check(var_name: str, expr: Expr) -> bool:
        if expr.kind == ExprType.VAR:
            return expr.name == var_name
        if expr.kind in (ExprType.FORALL, ExprType.EXISTS):
            if expr.var == var_name:
                return False  # bound, not free
            return Unifier._occurs_check(var_name, expr.body or Expr.const(""))
        return any(Unifier._occurs_check(var_name, arg) for arg in expr.args)


# ═══════════════════════════════════════════════════════════════════════════════
# COREENGINE — TacticEngine, ProofState, SearchEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TacticResult(Enum):
    """Outcome of applying a tactic to a proof state."""
    SUCCESS = auto()      # Tactic applied, new state(s) produced
    COMPLETE = auto()     # Proof finished
    FAILURE = auto()      # Tactic invalid for this state
    TIMEOUT = auto()      # Tactic application timed out


@dataclass
class Tactic:
    """
    A tactic is a named transformation rule applied to a sequent.
    name: tactic identifier (e.g., "intro", "apply", "rewrite")
    args: tactic-specific arguments (e.g., lemma name, variable name)
    score: model-assigned probability (0-1), used by search to rank tactics
    """
    name: str
    args: Tuple[Any, ...] = ()
    score: float = 0.5

    def __str__(self) -> str:
        if self.args:
            return f"{self.name}({', '.join(str(a) for a in self.args)})"
        return self.name


@dataclass
class ProofState:
    """
    A single node in the proof tree.
    Represents one or more sequents (subgoals) that need to be proved.
    """
    goals: List[Sequent] = field(default_factory=list)
    history: List[Tactic] = field(default_factory=list)  # tactics applied so far
    depth: int = 0
    score: float = 0.0  # accumulated score for search ranking
    status: TacticResult = TacticResult.SUCCESS
    parent: Optional[ProofState] = None
    node_id: int = 0

    _node_counter: int = field(default=0, repr=False, compare=False)

    def is_complete(self) -> bool:
        return len(self.goals) == 0

    def copy(self) -> ProofState:
        return ProofState(
            goals=[Sequent(list(g.hypotheses), g.goal, g.label) for g in self.goals],
            history=list(self.history),
            depth=self.depth,
            score=self.score,
            status=self.status,
            parent=self,
            node_id=self.node_id,
        )

    def __hash__(self) -> int:
        return self.node_id


class TacticEngine:
    """
    Core tactic application engine.
    Implements a library of basic tactics inspired by Coq/Lean/Isabelle.
    """

    def __init__(self):
        self._tactics: Dict[str, Callable] = {
            "intro": self._tactic_intro,
            "apply": self._tactic_apply,
            "rewrite": self._tactic_rewrite,
            "split": self._tactic_split,
            "left": self._tactic_left,
            "right": self._tactic_right,
            "exact": self._tactic_exact,
            "trivial": self._tactic_trivial,
            "assumption": self._tactic_assumption,
            "destruct": self._tactic_destruct,
            "induction": self._tactic_induction,
            "simpl": self._tactic_simpl,
            "reflexivity": self._tactic_reflexivity,
            "symmetry": self._tactic_symmetry,
            "transitivity": self._tactic_transitivity,
            "contradiction": self._tactic_contradiction,
            "unfold": self._tactic_unfold,
            "fold": self._tactic_fold,
            "cut": self._tactic_cut,
            "generalize": self._tactic_generalize,
            "clear": self._tactic_clear,
            "rename": self._tactic_rename,
            "sorry": self._tactic_sorry,
            "qed": self._tactic_qed,
        }

    def apply(self, state: ProofState, tactic: Tactic, axioms: AxiomSet) -> List[ProofState]:
        """
        Apply a tactic to the current proof state.
        Returns list of new proof states (may be empty on failure, single on success,
        multiple on branching tactics like split/destruct).
        """
        if not state.goals:
            return []

        handler = self._tactics.get(tactic.name)
        if handler is None:
            return []

        try:
            result = handler(state, tactic, axioms)
            for r in result:
                r.history.append(tactic)
                r.depth = state.depth + 1
                r.node_id = state.node_id + 1
                if r.is_complete():
                    r.status = TacticResult.COMPLETE
            return result
        except Exception:
            return []

    # ── Individual Tactic Implementations ──────────────────────────────────

    def _tactic_intro(self, state: ProofState, tactic: Tactic, axioms: AxiomSet) -> List[ProofState]:
        """intro x — introduce a variable/assumption for implication, forall, or negation."""
        if not state.goals:
            return []
        goal = state.goals[0]
        rest = state.goals[1:]

        var_name = tactic.args[0] if tactic.args else "x"

        # Introduce forall
        if goal.goal and goal.goal.kind == ExprType.FORALL:
            bound = goal.goal.var or var_name
            body = goal.goal.body or Expr.const("true")
            new_goal = Sequent(goal.hypotheses + [Expr.var(bound)], body, f"intro-{bound}")
            new_state = state.copy()
            new_state.goals = [new_goal] + rest
            return [new_state]

        # Introduce implication
        if goal.goal and goal.goal.kind == ExprType.IMPLIES:
            antecedent = goal.goal.args[0]
            consequent = goal.goal.args[1]
            new_goal = Sequent(goal.hypotheses + [antecedent], consequent, "intro-imp")
            new_state = state.copy()
            new_state.goals = [new_goal] + rest
            return [new_state]

        # Introduce negation: goal ¬A  =>  assume A, prove contradiction (false)
        if goal.goal and goal.goal.kind == ExprType.NOT:
            negated = goal.goal.args[0]
            new_goal = Sequent(goal.hypotheses + [negated], Expr.const("false"), "intro-neg")
            new_state = state.copy()
            new_state.goals = [new_goal] + rest
            return [new_state]

        return []

    def _tactic_apply(self, state: ProofState, tactic: Tactic, axioms: AxiomSet) -> List[ProofState]:
        """apply H — apply a hypothesis/lemma that matches the goal."""
        if not state.goals or not tactic.args:
            return []
        goal = state.goals[0]
        rest = state.goals[1:]
        lemma_name = tactic.args[0]

        # Search in hypotheses
        for hyp in goal.hypotheses:
            if hyp.kind == ExprType.IMPLIES and hyp.args[1] == goal.goal:
                # H : A -> B, goal B → new goal A
                new_goal = Sequent(goal.hypotheses, hyp.args[0], "apply-hyp")
                new_state = state.copy()
                new_state.goals = [new_goal] + rest
                return [new_state]

        # Search in axioms
        for axiom in axioms.axioms:
            if axiom.conclusion == goal.goal:
                new_goals = [
                    Sequent(goal.hypotheses, prem, f"apply-axiom-{lemma_name}-{i}")
                    for i, prem in enumerate(axiom.premises)
                ]
                new_state = state.copy()
                new_state.goals = new_goals + rest
                return [new_state]

            # Try unification for pattern matching
            try:
                subst = Unifier.unify(axiom.conclusion, goal.goal or Expr.const(""))
                new_goals = [
                    Sequent(goal.hypotheses, prem.subst(subst), f"apply-unif-{i}")
                    for i, prem in enumerate(axiom.premises)
                ]
                new_state = state.copy()
                new_state.goals = new_goals + rest
                return [new_state]
            except UnificationError:
                continue

        return []

    def _tactic_rewrite(self, state: ProofState, tactic: Tactic, axioms: AxiomSet) -> List[ProofState]:
        """rewrite H — rewrite goal using an equality hypothesis."""
        if not state.goals or not tactic.args:
            return []
        goal = state.goals[0]
        rest = state.goals[1:]
        eq_name = tactic.args[0]

        for hyp in goal.hypotheses:
            if hyp.kind == ExprType.EQ:
                lhs, rhs = hyp.args
                new_goal_expr = _rewrite_expr(goal.goal or Expr.const(""), lhs, rhs)
                new_goal = Sequent(goal.hypotheses, new_goal_expr, "rewrite")
                new_state = state.copy()
                new_state.goals = [new_goal] + rest
                return [new_state]

        return []

    def _tactic_split(self, state: ProofState, tactic: Tactic, axioms: AxiomSet) -> List[ProofState]:
        """split — split conjunction goal into two subgoals."""
        if not state.goals:
            return []
        goal = state.goals[0]
        rest = state.goals[1:]

        if goal.goal and goal.goal.kind == ExprType.AND:
            left = goal.goal.args[0]
            right = goal.goal.args[1]
            g1 = Sequent(goal.hypotheses, left, "split-left")
            g2 = Sequent(goal.hypotheses, right, "split-right")
            new_state = state.copy()
            new_state.goals = [g1, g2] + rest
            return [new_state]

        if goal.goal and goal.goal.kind == ExprType.IFF:
            fwd = Expr.implies(goal.goal.args[0], goal.goal.args[1])
            bwd = Expr.implies(goal.goal.args[1], goal.goal.args[0])
            g1 = Sequent(goal.hypotheses, fwd, "split-iff-fwd")
            g2 = Sequent(goal.hypotheses, bwd, "split-iff-bwd")
            new_state = state.copy()
            new_state.goals = [g1, g2] + rest
            return [new_state]

        return []

    def _tactic_left(self, state: ProofState, tactic: Tactic, axioms: AxiomSet) -> List[ProofState]:
        """left — prove left side of disjunction."""
        if not state.goals:
            return []
        goal = state.goals[0]
        rest = state.goals[1:]
        if goal.goal and goal.goal.kind == ExprType.OR:
            new_goal = Sequent(goal.hypotheses, goal.goal.args[0], "left")
            new_state = state.copy()
            new_state.goals = [new_goal] + rest
            return [new_state]
        return []

    def _tactic_right(self, state: ProofState, tactic: Tactic, axioms: AxiomSet) -> List[ProofState]:
        """right — prove right side of disjunction."""
        if not state.goals:
            return []
        goal = state.goals[0]
        rest = state.goals[1:]
        if goal.goal and goal.goal.kind == ExprType.OR:
            new_goal = Sequent(goal.hypotheses, goal.goal.args[1], "right")
            new_state = state.copy()
            new_state.goals = [new_goal] + rest
            return [new_state]
        return []

    def _tactic_exact(self, state: ProofState, tactic: Tactic, axioms: AxiomSet) -> List[ProofState]:
        """exact H — goal is exactly hypothesis H."""
        if not state.goals or not tactic.args:
            return []
        goal = state.goals[0]
        rest = state.goals[1:]
        hyp_name = tactic.args[0]

        for hyp in goal.hypotheses:
            if hyp == goal.goal:
                new_state = state.copy()
                new_state.goals = rest
                return [new_state]
        return []

    def _tactic_trivial(self, state: ProofState, tactic: Tactic, axioms: AxiomSet) -> List[ProofState]:
        """trivial — goal is trivially true (true, or provable by simple steps)."""
        if not state.goals:
            return []
        goal = state.goals[0]
        rest = state.goals[1:]

        if goal.goal and goal.goal.kind == ExprType.CONST and goal.goal.name == "true":
            new_state = state.copy()
            new_state.goals = rest
            return [new_state]

        return []

    def _tactic_assumption(self, state: ProofState, tactic: Tactic, axioms: AxiomSet) -> List[ProofState]:
        """assumption — goal is in hypotheses."""
        if not state.goals:
            return []
        goal = state.goals[0]
        rest = state.goals[1:]

        for hyp in goal.hypotheses:
            if hyp == goal.goal:
                new_state = state.copy()
                new_state.goals = rest
                return [new_state]
        return []

    def _tactic_destruct(self, state: ProofState, tactic: Tactic, axioms: AxiomSet) -> List[ProofState]:
        """destruct H — case analysis on a hypothesis."""
        if not state.goals or not tactic.args:
            return []
        goal = state.goals[0]
        rest = state.goals[1:]
        hyp_name = tactic.args[0]

        for i, hyp in enumerate(goal.hypotheses):
            if hyp.kind == ExprType.AND:
                new_hyps = list(goal.hypotheses)
                new_hyps[i:i+1] = [hyp.args[0], hyp.args[1]]
                new_goal = Sequent(new_hyps, goal.goal, "destruct-and")
                new_state = state.copy()
                new_state.goals = [new_goal] + rest
                return [new_state]

            if hyp.kind == ExprType.OR:
                g1 = Sequent(goal.hypotheses[:i] + goal.hypotheses[i+1:] + [hyp.args[0]], goal.goal, "destruct-or-l")
                g2 = Sequent(goal.hypotheses[:i] + goal.hypotheses[i+1:] + [hyp.args[1]], goal.goal, "destruct-or-r")
                new_state = state.copy()
                new_state.goals = [g1, g2] + rest
                return [new_state]

        return []

    def _tactic_induction(self, state: ProofState, tactic: Tactic, axioms: AxiomSet) -> List[ProofState]:
        """induction x — induction on variable x."""
        if not state.goals or not tactic.args:
            return []
        goal = state.goals[0]
        rest = state.goals[1:]
        var_name = tactic.args[0]

        # Base case: substitute variable with 0
        base_goal = Sequent(
            goal.hypotheses,
            (goal.goal or Expr.const("")).subst({var_name: Expr.const("0")}),
            "induction-base"
        )
        # Inductive step: substitute with succ(n), add IH
        ih = (goal.goal or Expr.const("")).subst({var_name: Expr.var("n")})
        step_goal = Sequent(
            goal.hypotheses + [ih],
            (goal.goal or Expr.const("")).subst({var_name: Expr.func("succ", Expr.var("n"))}),
            "induction-step"
        )
        new_state = state.copy()
        new_state.goals = [base_goal, step_goal] + rest
        return [new_state]

    def _tactic_simpl(self, state: ProofState, tactic: Tactic, axioms: AxiomSet) -> List[ProofState]:
        """simpl — simplify the goal using known rewrite rules."""
        if not state.goals:
            return []
        goal = state.goals[0]
        rest = state.goals[1:]
        simplified = _simplify(goal.goal or Expr.const(""))
        new_goal = Sequent(goal.hypotheses, simplified, "simpl")
        new_state = state.copy()
        new_state.goals = [new_goal] + rest
        return [new_state]

    def _tactic_reflexivity(self, state: ProofState, tactic: Tactic, axioms: AxiomSet) -> List[ProofState]:
        """reflexivity — goal is of the form t = t."""
        if not state.goals:
            return []
        goal = state.goals[0]
        rest = state.goals[1:]
        if goal.goal and goal.goal.kind == ExprType.EQ:
            if goal.goal.args[0] == goal.goal.args[1]:
                new_state = state.copy()
                new_state.goals = rest
                return [new_state]
        return []

    def _tactic_symmetry(self, state: ProofState, tactic: Tactic, axioms: AxiomSet) -> List[ProofState]:
        """symmetry — swap sides of an equality goal."""
        if not state.goals:
            return []
        goal = state.goals[0]
        rest = state.goals[1:]
        if goal.goal and goal.goal.kind == ExprType.EQ:
            new_goal = Sequent(goal.hypotheses, Expr.eq(goal.goal.args[1], goal.goal.args[0]), "symmetry")
            new_state = state.copy()
            new_state.goals = [new_goal] + rest
            return [new_state]
        return []

    def _tactic_transitivity(self, state: ProofState, tactic: Tactic, axioms: AxiomSet) -> List[ProofState]:
        """transitivity t — transitivity step with intermediate term t."""
        if not state.goals or not tactic.args:
            return []
        goal = state.goals[0]
        rest = state.goals[1:]
        if goal.goal and goal.goal.kind == ExprType.EQ:
            mid = tactic.args[0] if isinstance(tactic.args[0], Expr) else Expr.const(str(tactic.args[0]))
            g1 = Sequent(goal.hypotheses, Expr.eq(goal.goal.args[0], mid), "trans-l")
            g2 = Sequent(goal.hypotheses, Expr.eq(mid, goal.goal.args[1]), "trans-r")
            new_state = state.copy()
            new_state.goals = [g1, g2] + rest
            return [new_state]
        return []

    def _tactic_contradiction(self, state: ProofState, tactic: Tactic, axioms: AxiomSet) -> List[ProofState]:
        """contradiction — derive contradiction from hypotheses or false goal."""
        if not state.goals:
            return []
        goal = state.goals[0]
        rest = state.goals[1:]

        # Goal is false with any hypothesis → contradiction
        if goal.goal and goal.goal.kind == ExprType.CONST and goal.goal.name == "false":
            new_state = state.copy()
            new_state.goals = rest
            return [new_state]

        # Classical contradiction: H and ¬H both in hypotheses
        for hyp in goal.hypotheses:
            if hyp.kind == ExprType.NOT:
                negated = hyp.args[0]
                for other in goal.hypotheses:
                    if other == negated:
                        new_state = state.copy()
                        new_state.goals = rest
                        return [new_state]
            # Also check if some hypothesis is negated by another
            for other in goal.hypotheses:
                if other.kind == ExprType.NOT and other.args[0] == hyp:
                    new_state = state.copy()
                    new_state.goals = rest
                    return [new_state]

        return []

    def _tactic_unfold(self, state: ProofState, tactic: Tactic, axioms: AxiomSet) -> List[ProofState]:
        """unfold def — expand a definition."""
        if not state.goals or not tactic.args:
            return []
        goal = state.goals[0]
        rest = state.goals[1:]
        def_name = tactic.args[0]
        definition = axioms.definitions.get(def_name)
        if definition and goal.goal:
            unfolded = _unfold_in_expr(goal.goal, def_name, definition)
            new_goal = Sequent(goal.hypotheses, unfolded, f"unfold-{def_name}")
            new_state = state.copy()
            new_state.goals = [new_goal] + rest
            return [new_state]
        return []

    def _tactic_fold(self, state: ProofState, tactic: Tactic, axioms: AxiomSet) -> List[ProofState]:
        """fold def — fold a definition."""
        if not state.goals or not tactic.args:
            return []
        goal = state.goals[0]
        rest = state.goals[1:]
        def_name = tactic.args[0]
        definition = axioms.definitions.get(def_name)
        if definition and goal.goal:
            folded = _fold_in_expr(goal.goal, def_name, definition)
            new_goal = Sequent(goal.hypotheses, folded, f"fold-{def_name}")
            new_state = state.copy()
            new_state.goals = [new_goal] + rest
            return [new_state]
        return []

    def _tactic_cut(self, state: ProofState, tactic: Tactic, axioms: AxiomSet) -> List[ProofState]:
        """cut A — introduce intermediate lemma A."""
        if not state.goals or not tactic.args:
            return []
        goal = state.goals[0]
        rest = state.goals[1:]
        lemma = tactic.args[0] if isinstance(tactic.args[0], Expr) else Expr.const(str(tactic.args[0]))
        g1 = Sequent(goal.hypotheses, lemma, "cut-lemma")
        g2 = Sequent(goal.hypotheses + [lemma], goal.goal, "cut-use")
        new_state = state.copy()
        new_state.goals = [g1, g2] + rest
        return [new_state]

    def _tactic_generalize(self, state: ProofState, tactic: Tactic, axioms: AxiomSet) -> List[ProofState]:
        """generalize x — generalize a variable."""
        if not state.goals or not tactic.args:
            return []
        goal = state.goals[0]
        rest = state.goals[1:]
        var_name = tactic.args[0]
        if goal.goal:
            new_goal_expr = Expr.forall(var_name, goal.goal)
            new_goal = Sequent(goal.hypotheses, new_goal_expr, "generalize")
            new_state = state.copy()
            new_state.goals = [new_goal] + rest
            return [new_state]
        return []

    def _tactic_clear(self, state: ProofState, tactic: Tactic, axioms: AxiomSet) -> List[ProofState]:
        """clear H — remove hypothesis H."""
        if not state.goals or not tactic.args:
            return []
        goal = state.goals[0]
        rest = state.goals[1:]
        hyp_name = tactic.args[0]
        new_hyps = [h for h in goal.hypotheses if not (h.kind == ExprType.VAR and h.name == hyp_name)]
        new_goal = Sequent(new_hyps, goal.goal, "clear")
        new_state = state.copy()
        new_state.goals = [new_goal] + rest
        return [new_state]

    def _tactic_rename(self, state: ProofState, tactic: Tactic, axioms: AxiomSet) -> List[ProofState]:
        """rename x into y — rename a variable."""
        if not state.goals or len(tactic.args) < 2:
            return []
        goal = state.goals[0]
        rest = state.goals[1:]
        old_name = tactic.args[0]
        new_name = tactic.args[1]
        mapping = {old_name: Expr.var(new_name)}
        new_hyps = [h.subst(mapping) for h in goal.hypotheses]
        new_goal_expr = (goal.goal or Expr.const("")).subst(mapping)
        new_goal = Sequent(new_hyps, new_goal_expr, "rename")
        new_state = state.copy()
        new_state.goals = [new_goal] + rest
        return [new_state]

    def _tactic_sorry(self, state: ProofState, tactic: Tactic, axioms: AxiomSet) -> List[ProofState]:
        """sorry — admit the current goal (mask it as proved without actual proof)."""
        if not state.goals:
            return []
        rest = state.goals[1:]
        new_state = state.copy()
        new_state.goals = rest
        return [new_state]

    def _tactic_qed(self, state: ProofState, tactic: Tactic, axioms: AxiomSet) -> List[ProofState]:
        """qed — finish proof if all goals are discharged."""
        if not state.goals:
            return [state.copy()]
        return []


# ── Helper functions for tactic engine ─────────────────────────────────────

def _rewrite_expr(expr: Expr, old: Expr, new: Expr) -> Expr:
    if expr == old:
        return new
    if expr.kind in (ExprType.FORALL, ExprType.EXISTS):
        return Expr(kind=expr.kind, var=expr.var, body=_rewrite_expr(expr.body or Expr.const(""), old, new))
    if expr.args:
        return Expr(kind=expr.kind, name=expr.name,
                    args=tuple(_rewrite_expr(a, old, new) for a in expr.args))
    return expr


def _simplify(expr: Expr) -> Expr:
    """Basic simplification: not(not(P)) -> P, P and true -> P, etc."""
    if expr.kind == ExprType.NOT and expr.args[0].kind == ExprType.NOT:
        return _simplify(expr.args[0].args[0])
    if expr.kind == ExprType.AND:
        a, b = _simplify(expr.args[0]), _simplify(expr.args[1])
        if a.kind == ExprType.CONST and a.name == "true":
            return b
        if b.kind == ExprType.CONST and b.name == "true":
            return a
        if a == b:
            return a
        return Expr.and_(a, b)
    if expr.kind == ExprType.OR:
        a, b = _simplify(expr.args[0]), _simplify(expr.args[1])
        if a.kind == ExprType.CONST and a.name == "false":
            return b
        if b.kind == ExprType.CONST and b.name == "false":
            return a
        return Expr.or_(a, b)
    if expr.kind == ExprType.IMPLIES:
        a, b = _simplify(expr.args[0]), _simplify(expr.args[1])
        if a.kind == ExprType.CONST and a.name == "true":
            return b
        if b.kind == ExprType.CONST and b.name == "true":
            return Expr.const("true")
        return Expr.implies(a, b)
    if expr.args:
        return Expr(kind=expr.kind, name=expr.name,
                    args=tuple(_simplify(a) for a in expr.args))
    return expr


def _unfold_in_expr(expr: Expr, name: str, definition: Expr) -> Expr:
    if expr.kind == ExprType.VAR and expr.name == name:
        return definition
    if expr.kind in (ExprType.FORALL, ExprType.EXISTS):
        return Expr(kind=expr.kind, var=expr.var,
                    body=_unfold_in_expr(expr.body or Expr.const(""), name, definition))
    if expr.args:
        return Expr(kind=expr.kind, name=expr.name,
                    args=tuple(_unfold_in_expr(a, name, definition) for a in expr.args))
    return expr


def _fold_in_expr(expr: Expr, name: str, definition: Expr) -> Expr:
    if expr == definition:
        return Expr.var(name)
    if expr.kind in (ExprType.FORALL, ExprType.EXISTS):
        return Expr(kind=expr.kind, var=expr.var,
                    body=_fold_in_expr(expr.body or Expr.const(""), name, definition))
    if expr.args:
        return Expr(kind=expr.kind, name=expr.name,
                    args=tuple(_fold_in_expr(a, name, definition) for a in expr.args))
    return expr


# ── AxiomSet ───────────────────────────────────────────────────────────────

@dataclass
class Axiom:
    """An inference rule or axiom: premises ⊢ conclusion."""
    name: str
    premises: List[Expr] = field(default_factory=list)
    conclusion: Expr = Expr.const("true")
    parameters: List[str] = field(default_factory=list)  # For parametric axioms

    def instantiate(self, subst: Dict[str, Expr]) -> Axiom:
        return Axiom(
            name=self.name,
            premises=[p.subst(subst) for p in self.premises],
            conclusion=self.conclusion.subst(subst),
            parameters=self.parameters,
        )


@dataclass
class AxiomSet:
    """Collection of axioms, definitions, and rewrite rules."""
    axioms: List[Axiom] = field(default_factory=list)
    definitions: Dict[str, Expr] = field(default_factory=dict)
    rewrite_rules: List[Tuple[Expr, Expr]] = field(default_factory=list)

    def add_axiom(self, axiom: Axiom) -> None:
        self.axioms.append(axiom)

    def add_definition(self, name: str, definition: Expr) -> None:
        self.definitions[name] = definition

    def add_rewrite(self, lhs: Expr, rhs: Expr) -> None:
        self.rewrite_rules.append((lhs, rhs))


# ═══════════════════════════════════════════════════════════════════════════════
# COREENGINE — SearchEngine (BFS / DFS / Best-First / MCTS-inspired)
# ═══════════════════════════════════════════════════════════════════════════════

class SearchStrategy(Enum):
    BFS = auto()
    DFS = auto()
    BEST_FIRST = auto()
    MCTS = auto()


@dataclass
class SearchNode:
    """A node in the search tree, wrapping a ProofState with scoring metadata."""
    state: ProofState
    priority: float = 0.0
    visit_count: int = 0
    value_estimate: float = 0.0
    prior_prob: float = 1.0
    parent: Optional[SearchNode] = None
    children: List[SearchNode] = field(default_factory=list)

    def __lt__(self, other: SearchNode) -> bool:
        # For min-heap: lower priority = better (explored first)
        return self.priority < other.priority


class SearchEngine:
    """
    Tree search engine for theorem proving.
    Supports BFS, DFS, Best-First Search (length-normalized), and MCTS-inspired PUCT.
    """

    def __init__(
        self,
        strategy: SearchStrategy = SearchStrategy.BEST_FIRST,
        max_depth: int = 50,
        max_nodes: int = 10_000,
        expansion_width: int = 5,
        length_norm_alpha: float = 0.5,
        puct_c: float = 2.0,
    ):
        self.strategy = strategy
        self.max_depth = max_depth
        self.max_nodes = max_nodes
        self.expansion_width = expansion_width
        self.length_norm_alpha = length_norm_alpha
        self.puct_c = puct_c
        self.tactic_engine = TacticEngine()
        self.heuristic = HeuristicScorer()

    def search(
        self,
        initial_state: ProofState,
        axioms: AxiomSet,
        tactic_generator: Callable[[ProofState, AxiomSet], List[Tactic]],
        timeout_seconds: float = 60.0,
    ) -> Optional[ProofState]:
        """
        Search for a complete proof starting from initial_state.
        Returns the completed ProofState with full history, or None if no proof found.
        """
        start_time = time.time()
        nodes_expanded = 0

        # Initialize search
        root = SearchNode(state=initial_state, priority=0.0)
        
        if self.strategy == SearchStrategy.BFS:
            queue: List[SearchNode] = [root]
        elif self.strategy == SearchStrategy.DFS:
            stack: List[SearchNode] = [root]
        elif self.strategy == SearchStrategy.BEST_FIRST:
            heap: List[Tuple[float, int, SearchNode]] = [(0.0, 0, root)]
            heap_counter = 1
        elif self.strategy == SearchStrategy.MCTS:
            mcts_queue: List[SearchNode] = [root]

        visited: Set[int] = set()

        while True:
            if time.time() - start_time > timeout_seconds:
                break
            if nodes_expanded >= self.max_nodes:
                break

            # ── Pop next node ──────────────────────────────────────────────
            if self.strategy == SearchStrategy.BFS:
                if not queue:
                    break
                current = queue.pop(0)
            elif self.strategy == SearchStrategy.DFS:
                if not stack:
                    break
                current = stack.pop()
            elif self.strategy == SearchStrategy.BEST_FIRST:
                if not heap:
                    break
                _, _, current = heapq.heappop(heap)
            elif self.strategy == SearchStrategy.MCTS:
                if not mcts_queue:
                    break
                # Selection: PUCT formula
                current = self._mcts_select(mcts_queue)
            else:
                break

            if current.state.is_complete():
                return current.state

            state_hash = hash(str(current.state.goals))
            if state_hash in visited:
                continue
            visited.add(state_hash)

            nodes_expanded += 1
            current.visit_count += 1

            # ── Generate tactics ───────────────────────────────────────────
            tactics = tactic_generator(current.state, axioms)
            # Sort by score, take top expansion_width
            tactics = sorted(tactics, key=lambda t: t.score, reverse=True)[:self.expansion_width]

            # ── Expand node ──────────────────────────────────────────────
            for tactic in tactics:
                results = self.tactic_engine.apply(current.state, tactic, axioms)
                for result in results:
                    if result.is_complete():
                        return result

                    if result.depth > self.max_depth:
                        continue

                    child = SearchNode(
                        state=result,
                        parent=current,
                        prior_prob=tactic.score,
                    )
                    current.children.append(child)

                    # Compute priority based on strategy
                    if self.strategy == SearchStrategy.BFS:
                        child.priority = result.depth
                        queue.append(child)
                    elif self.strategy == SearchStrategy.DFS:
                        child.priority = -result.depth
                        stack.append(child)
                    elif self.strategy == SearchStrategy.BEST_FIRST:
                        child.priority = self._best_first_score(result, tactic.score)
                        heapq.heappush(heap, (child.priority, heap_counter, child))
                        heap_counter += 1
                    elif self.strategy == SearchStrategy.MCTS:
                        child.value_estimate = self.heuristic.evaluate(result)
                        mcts_queue.append(child)

        return None

    def _best_first_score(self, state: ProofState, tactic_prob: float) -> float:
        """
        Length-normalized best-first score (BFS-Prover heuristic).
        Lower score = better priority (min-heap).
        score(s_L) = -sum(log p(a_t | s_t)) / L^alpha
        """
        if state.depth == 0:
            return 0.0
        log_probs = sum(max(-5.0, min(0.0, -tactic_prob)) for _ in range(state.depth))
        # We approximate since we don't have per-step probs stored
        # Use a heuristic mix: accumulated score + depth penalty
        norm = state.depth ** self.length_norm_alpha
        heuristic = self.heuristic.evaluate(state)
        return -(log_probs / norm + heuristic * 0.5)

    def _mcts_select(self, nodes: List[SearchNode]) -> SearchNode:
        """Select node using PUCT formula (AlphaProof style)."""
        if not nodes:
            raise ValueError("Empty MCTS queue")
        
        total_visits = sum(n.visit_count for n in nodes) + 1
        
        best_node = nodes[0]
        best_score = float('-inf')
        
        for node in nodes:
            if node.visit_count == 0:
                # Unvisited nodes get high exploration bonus
                score = float('inf')
            else:
                exploitation = node.value_estimate / node.visit_count
                exploration = self.puct_c * node.prior_prob * (total_visits ** 0.5) / (1 + node.visit_count)
                score = exploitation + exploration
            
            if score > best_score:
                best_score = score
                best_node = node
        
        return best_node


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURES — PatternLibrary, GoalReducer, ProofPrinter, HeuristicScorer
# ═══════════════════════════════════════════════════════════════════════════════

class PatternLibrary:
    """
    Library of common proof patterns and their recommended tactic sequences.
    Inspired by Proverbot9001's pattern-based prediction.
    """

    PATTERNS: List[Dict[str, Any]] = [
        {
            "name": "implication_chain",
            "match": lambda g: g and g.kind == ExprType.IMPLIES,
            "tactics": [Tactic("intro", ()), Tactic("apply", ("H",)), Tactic("assumption", ())],
            "priority": 1.0,
        },
        {
            "name": "conjunction_goal",
            "match": lambda g: g and g.kind == ExprType.AND,
            "tactics": [Tactic("split", ()), Tactic("trivial", ()), Tactic("trivial", ())],
            "priority": 0.9,
        },
        {
            "name": "disjunction_left",
            "match": lambda g: g and g.kind == ExprType.OR,
            "tactics": [Tactic("left", ()), Tactic("trivial", ())],
            "priority": 0.7,
        },
        {
            "name": "universal_quantifier",
            "match": lambda g: g and g.kind == ExprType.FORALL,
            "tactics": [Tactic("intro", ("x",))],
            "priority": 0.95,
        },
        {
            "name": "reflexive_equality",
            "match": lambda g: g and g.kind == ExprType.EQ and g.args[0] == g.args[1],
            "tactics": [Tactic("reflexivity", ())],
            "priority": 1.0,
        },
        {
            "name": "assumption_available",
            "match": lambda g, hyps=None: any(h == g for h in (hyps or [])),
            "tactics": [Tactic("assumption", ())],
            "priority": 1.0,
        },
        {
            "name": "negation_goal",
            "match": lambda g: g and g.kind == ExprType.NOT,
            "tactics": [Tactic("intro", ("H",)), Tactic("contradiction", ())],
            "priority": 0.8,
        },
        {
            "name": "biconditional",
            "match": lambda g: g and g.kind == ExprType.IFF,
            "tactics": [Tactic("split", ()), Tactic("intro", ()), Tactic("intro", ())],
            "priority": 0.85,
        },
        {
            "name": "exists_goal",
            "match": lambda g: g and g.kind == ExprType.EXISTS,
            "tactics": [Tactic("exact", ("witness",))],
            "priority": 0.6,
        },
        {
            "name": "goal_false",
            "match": lambda g, hyps=None: g and g.kind == ExprType.CONST and g.name == "false",
            "tactics": [Tactic("contradiction", ())],
            "priority": 1.0,
        },
        {
            "name": "simplifiable",
            "match": lambda g: g and _can_simplify(g),
            "tactics": [Tactic("simpl", ())],
            "priority": 0.75,
        },
    ]

    def match_goal(self, goal: Optional[Expr], hypotheses: List[Expr]) -> List[Tactic]:
        """Match goal against patterns and return suggested tactics."""
        results: List[Tactic] = []
        for pattern in self.PATTERNS:
            match_fn = pattern["match"]
            try:
                if len(inspect.signature(match_fn).parameters) == 1:
                    matched = match_fn(goal)
                else:
                    matched = match_fn(goal, hypotheses)
            except Exception:
                matched = False
            
            if matched:
                for t in pattern["tactics"]:
                    scored = Tactic(t.name, t.args, score=pattern["priority"])
                    results.append(scored)
        return results


class GoalReducer:
    """Advanced goal reduction engine for compound expressions."""

    @staticmethod
    def reduce(expr: Expr) -> Optional[Expr]:
        """Apply structural reductions to simplify complex expressions."""
        if expr.kind == ExprType.IMPLIES and expr.args[0].kind == ExprType.AND:
            # (A ∧ B) → C  =>  A → (B → C)
            a, b = expr.args[0].args
            c = expr.args[1]
            return Expr.implies(a, Expr.implies(b, c))
        
        if expr.kind == ExprType.IMPLIES and expr.args[1].kind == ExprType.AND:
            # A → (B ∧ C)  =>  (A → B) ∧ (A → C)
            a, bc = expr.args
            b, c = bc.args
            return Expr.and_(Expr.implies(a, b), Expr.implies(a, c))
        
        if expr.kind == ExprType.NOT and expr.args[0].kind == ExprType.AND:
            # ¬(A ∧ B)  =>  ¬A ∨ ¬B  (De Morgan)
            a, b = expr.args[0].args
            return Expr.or_(Expr.not_(a), Expr.not_(b))
        
        if expr.kind == ExprType.NOT and expr.args[0].kind == ExprType.OR:
            # ¬(A ∨ B)  =>  ¬A ∧ ¬B  (De Morgan)
            a, b = expr.args[0].args
            return Expr.and_(Expr.not_(a), Expr.not_(b))
        
        if expr.kind == ExprType.NOT and expr.args[0].kind == ExprType.IMPLIES:
            # ¬(A → B)  =>  A ∧ ¬B
            a, b = expr.args[0].args
            return Expr.and_(a, Expr.not_(b))
        
        return None


class ProofPrinter:
    """Pretty-print proofs in a human-readable format."""

    @staticmethod
    def print_proof(state: ProofState, indent: int = 0) -> str:
        if not state.history:
            return "  " * indent + "(no tactics applied)"
        
        lines: List[str] = []
        for i, tactic in enumerate(state.history):
            lines.append("  " * indent + f"{i+1}. {tactic}")
        return "\n".join(lines)

    @staticmethod
    def print_tree(node: SearchNode, depth: int = 0, max_depth: int = 10) -> str:
        if depth > max_depth:
            return "  " * depth + "..."
        
        status = "✓" if node.state.is_complete() else "○"
        lines = ["  " * depth + f"{status} depth={node.state.depth} score={node.state.score:.3f} goals={len(node.state.goals)}"]
        for child in node.children:
            lines.append(ProofPrinter.print_tree(child, depth + 1, max_depth))
        return "\n".join(lines)

    @staticmethod
    def print_sequent(sequent: Sequent) -> str:
        return str(sequent)


class HeuristicScorer:
    """
    Heuristic evaluation of proof states.
    Inspired by AlphaProof's value estimation and rlCoP's evaluation heuristic.
    """

    def evaluate(self, state: ProofState) -> float:
        """Return a heuristic value estimate in [0, 1]. Higher = more promising."""
        if state.is_complete():
            return 1.0
        
        if not state.goals:
            return 1.0
        
        goal = state.goals[0]
        score = 0.5
        
        # Fewer goals is better
        score -= len(state.goals) * 0.05
        
        # More hypotheses available = more resources
        score += len(goal.hypotheses) * 0.02
        
        # Goal complexity penalty
        if goal.goal:
            complexity = self._expr_complexity(goal.goal)
            score -= complexity * 0.01
            
            # Prefer certain goal shapes
            if goal.goal.kind == ExprType.CONST and goal.goal.name == "true":
                score += 0.3
            if goal.goal.kind == ExprType.EQ:
                score += 0.1
            if any(h == goal.goal for h in goal.hypotheses):
                score += 0.4  # assumption available
        
        # Depth penalty (prefer shorter proofs)
        score -= state.depth * 0.005
        
        return max(0.0, min(1.0, score))

    @staticmethod
    def _expr_complexity(expr: Expr) -> int:
        if not expr.args:
            return 1
        return 1 + sum(HeuristicScorer._expr_complexity(a) for a in expr.args)


# ── Tactic Generator ───────────────────────────────────────────────────────

class TacticGenerator:
    """
    Generates candidate tactics for a given proof state.
    Combines pattern matching, axiom-driven suggestions, and basic heuristics.
    Inspired by Proverbot9001's prediction architecture.
    """

    def __init__(self):
        self.patterns = PatternLibrary()
        self.reducer = GoalReducer()

    def generate(self, state: ProofState, axioms: AxiomSet) -> List[Tactic]:
        if not state.goals:
            return []
        
        goal = state.goals[0]
        tactics: List[Tactic] = []
        
        # 1. Pattern-based tactics
        pattern_tactics = self.patterns.match_goal(goal.goal, goal.hypotheses)
        tactics.extend(pattern_tactics)
        
        # 2. Try goal reduction
        if goal.goal:
            reduced = self.reducer.reduce(goal.goal)
            if reduced:
                # Suggest simplification if reducible
                tactics.append(Tactic("simpl", (), score=0.6))
        
        # 3. Axiom-driven tactics
        for axiom in axioms.axioms:
            # Suggest applying axioms that might unify with goal
            try:
                Unifier.unify(axiom.conclusion, goal.goal or Expr.const(""))
                tactics.append(Tactic("apply", (axiom.name,), score=0.5))
            except UnificationError:
                pass
        
        # 4. Hypothesis-driven tactics
        for i, hyp in enumerate(goal.hypotheses):
            if hyp.kind == ExprType.IMPLIES:
                # Can apply this hypothesis
                tactics.append(Tactic("apply", (f"H{i}",), score=0.45))
            if hyp.kind == ExprType.EQ:
                # Can rewrite with this hypothesis
                tactics.append(Tactic("rewrite", (f"H{i}",), score=0.4))
            if hyp.kind == ExprType.AND:
                # Can destruct this hypothesis
                tactics.append(Tactic("destruct", (f"H{i}",), score=0.35))
        
        # 5. Structural tactics based on goal shape
        if goal.goal:
            if goal.goal.kind == ExprType.IMPLIES:
                tactics.append(Tactic("intro", (), score=0.7))
            if goal.goal.kind == ExprType.FORALL:
                tactics.append(Tactic("intro", (goal.goal.var or "x",), score=0.75))
            if goal.goal.kind == ExprType.EXISTS:
                tactics.append(Tactic("exact", ("witness",), score=0.5))
            if goal.goal.kind == ExprType.OR:
                tactics.append(Tactic("left", (), score=0.5))
                tactics.append(Tactic("right", (), score=0.5))
        
        # 6. Terminal tactics (high priority, low branching)
        tactics.append(Tactic("trivial", (), score=0.3))
        tactics.append(Tactic("reflexivity", (), score=0.35))
        tactics.append(Tactic("assumption", (), score=0.8))
        tactics.append(Tactic("contradiction", (), score=0.85))
        
        # Deduplicate and sort
        seen: Set[str] = set()
        unique: List[Tactic] = []
        for t in tactics:
            key = str(t)
            if key not in seen:
                seen.add(key)
                unique.append(t)
        
        return sorted(unique, key=lambda t: t.score, reverse=True)


# ═══════════════════════════════════════════════════════════════════════════════
# DRAFT / SKETCH / PROVE PATTERN (DSP-Plus inspired)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TheoremStatement:
    """A theorem to be proved: hypotheses ⊢ conclusion."""
    name: str = ""
    hypotheses: List[Expr] = field(default_factory=list)
    conclusion: Expr = Expr.const("true")

    def __str__(self) -> str:
        hyps = ", ".join(str(h) for h in self.hypotheses) if self.hypotheses else "∅"
        return f"Theorem {self.name}: {hyps} ⊢ {self.conclusion}"


@dataclass
class ProofSketch:
    """Draft-phase output: a high-level proof plan with key formulas and hints."""
    theorem: TheoremStatement
    steps: List[str] = field(default_factory=list)  # Human-readable plan steps
    key_formulas: List[Expr] = field(default_factory=list)
    estimated_tactics: List[str] = field(default_factory=list)

    def to_lines(self) -> List[str]:
        lines = [f"# Proof Sketch for {self.theorem.name}"]
        for i, step in enumerate(self.steps, 1):
            lines.append(f"{i}. {step}")
        for f in self.key_formulas:
            lines.append(f"# key: {f}")
        return lines


@dataclass
class Subgoal:
    """Structured subgoal from sketch formalization."""
    label: str
    hypotheses: List[Expr]
    goal: Expr
    hints: List[str] = field(default_factory=list)  # e.g., ["prove_with [h2]"]
    admitted: bool = False  # Set to True if masked with sorry

    def to_sequent(self) -> Sequent:
        return Sequent(self.hypotheses, self.goal, self.label)


class DraftEngine:
    """
    Draft Phase: generates a concise proof sketch from a theorem statement.
    Inspired by DSP-Plus: reasoning model generates key formulas and a plan.
    """

    def generate_sketch(self, theorem: TheoremStatement) -> ProofSketch:
        """Generate a high-level proof sketch for the given theorem."""
        steps: List[str] = []
        formulas: List[Expr] = []
        tactics: List[str] = []

        goal = theorem.conclusion

        # Analyze goal shape and suggest draft steps
        if goal.kind == ExprType.IMPLIES:
            steps.append("Introduce the antecedent as a hypothesis.")
            steps.append("Prove the consequent from the new context.")
            tactics.extend(["intro", "assumption", "apply"])
            formulas.append(goal.args[0])
            formulas.append(goal.args[1])

        elif goal.kind == ExprType.AND:
            steps.append("Prove the left conjunct.")
            steps.append("Prove the right conjunct.")
            tactics.extend(["split", "trivial", "assumption"])
            formulas.extend(goal.args)

        elif goal.kind == ExprType.OR:
            steps.append("Choose one side and prove it.")
            tactics.extend(["left", "right", "assumption"])
            formulas.extend(goal.args)

        elif goal.kind == ExprType.FORALL:
            steps.append(f"Introduce an arbitrary {goal.var}.")
            steps.append("Prove the body for that variable.")
            tactics.extend(["intro", "reflexivity", "simpl"])
            if goal.body:
                formulas.append(goal.body)

        elif goal.kind == ExprType.EXISTS:
            steps.append("Provide a witness for the existential.")
            tactics.extend(["exact", "apply"])
            if goal.body:
                formulas.append(goal.body)

        elif goal.kind == ExprType.EQ:
            steps.append("Show both sides are equal.")
            tactics.extend(["reflexivity", "rewrite", "transitivity"])
            formulas.extend(goal.args)

        elif goal.kind == ExprType.IFF:
            steps.append("Prove both directions of the iff.")
            tactics.extend(["split", "intro", "assumption"])

        elif goal.kind == ExprType.NOT:
            steps.append("Assume the negated formula and derive a contradiction.")
            tactics.extend(["intro", "contradiction"])
            formulas.append(goal.args[0])

        else:
            steps.append("Apply available hypotheses or axioms to close the goal.")
            tactics.extend(["assumption", "apply", "trivial"])

        # Add hypotheses as available resources
        for hyp in theorem.hypotheses:
            formulas.append(hyp)

        return ProofSketch(
            theorem=theorem,
            steps=steps,
            key_formulas=formulas,
            estimated_tactics=tactics,
        )


class SketchEngine:
    """
    Sketch Phase: converts a proof sketch into structured subgoals with hints.
    Autoformalization: sketch → list of Subgoal objects.
    """

    def formalize(self, sketch: ProofSketch) -> List[Subgoal]:
        """Convert a proof sketch into structured subgoals."""
        subgoals: List[Subgoal] = []
        goal = sketch.theorem.conclusion
        hyps = list(sketch.theorem.hypotheses)

        if goal.kind == ExprType.IMPLIES:
            # Subgoal 1: introduce antecedent, prove consequent
            subgoals.append(Subgoal(
                label="intro-imp",
                hypotheses=hyps + [goal.args[0]],
                goal=goal.args[1],
                hints=["intro", f"prove_with [{goal.args[0]}]"],
            ))

        elif goal.kind == ExprType.AND:
            for i, conjunct in enumerate(goal.args):
                subgoals.append(Subgoal(
                    label=f"conjunct-{i}",
                    hypotheses=hyps,
                    goal=conjunct,
                    hints=["split", "trivial"],
                ))

        elif goal.kind == ExprType.OR:
            # Try left first, then right as fallback
            subgoals.append(Subgoal(
                label="disj-left",
                hypotheses=hyps,
                goal=goal.args[0],
                hints=["left", "assumption"],
            ))
            subgoals.append(Subgoal(
                label="disj-right",
                hypotheses=hyps,
                goal=goal.args[1],
                hints=["right", "assumption"],
            ))

        elif goal.kind == ExprType.FORALL:
            bound = goal.var or "x"
            body = goal.body or Expr.const("true")
            subgoals.append(Subgoal(
                label=f"forall-{bound}",
                hypotheses=hyps + [Expr.var(bound)],
                goal=body,
                hints=["intro", "reflexivity"],
            ))

        elif goal.kind == ExprType.EXISTS:
            body = goal.body or Expr.const("true")
            subgoals.append(Subgoal(
                label="exists-witness",
                hypotheses=hyps,
                goal=body,
                hints=["exact", "apply"],
            ))

        elif goal.kind == ExprType.IFF:
            subgoals.append(Subgoal(
                label="iff-fwd",
                hypotheses=hyps,
                goal=Expr.implies(goal.args[0], goal.args[1]),
                hints=["split", "intro"],
            ))
            subgoals.append(Subgoal(
                label="iff-bwd",
                hypotheses=hyps,
                goal=Expr.implies(goal.args[1], goal.args[0]),
                hints=["split", "intro"],
            ))

        elif goal.kind == ExprType.NOT:
            subgoals.append(Subgoal(
                label="neg-contra",
                hypotheses=hyps + [goal.args[0]],
                goal=Expr.const("false"),
                hints=["intro", "contradiction"],
            ))

        else:
            # Atomic goal — single subgoal
            subgoals.append(Subgoal(
                label="main",
                hypotheses=hyps,
                goal=goal,
                hints=["assumption", "apply", "trivial"],
            ))

        return subgoals


class ErrorMasker:
    """
    Error Line Masking: when a tactic application fails, mask the line
    with `sorry` or comment it out, preserving valid structure.
    """

    @staticmethod
    def mask_invalid(proof_state: ProofState, tactic: Tactic) -> ProofState:
        """Replace the failed tactic's effect with `sorry` in the proof state."""
        new_state = proof_state.copy()
        # Mark the current goal as admitted
        if new_state.goals:
            sg = new_state.goals[0]
            # Create a new subgoal that is admitted
            admitted = Subgoal(
                label=f"{sg.label}-sorry",
                hypotheses=sg.hypotheses,
                goal=sg.goal or Expr.const("true"),
                hints=["sorry"],
                admitted=True,
            )
            # Replace current goal with admitted version
            new_state.goals[0] = admitted.to_sequent()
            # Append sorry to history
            new_state.history.append(Tactic("sorry", (f"failed: {tactic}",), score=0.0))
        return new_state

    @staticmethod
    def mask_all_remaining(state: ProofState) -> ProofState:
        """Mask all remaining goals with sorry — emergency bailout."""
        new_state = state.copy()
        new_state.goals = []
        for g in state.goals:
            new_state.history.append(Tactic("sorry", (str(g),), score=0.0))
        return new_state

    @staticmethod
    def is_admitted(state: ProofState) -> bool:
        """Check if any step in the history is a sorry."""
        return any(t.name == "sorry" for t in state.history)


class MockLLM:
    """
    Mock LLM interface for tactic prediction.
    Simulates a language model that predicts tactics from proof state.
    In production, this would call an actual LLM API.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.call_count = 0

    def predict_tactic(self, state: ProofState, axioms: AxiomSet) -> List[Tactic]:
        """
        Predict a ranked list of tactics for the current proof state.
        Returns tactics with confidence scores.
        """
        self.call_count += 1
        # Use the built-in TacticGenerator as the "model"
        gen = TacticGenerator()
        tactics = gen.generate(state, axioms)
        # Add a small random perturbation to simulate model uncertainty
        for t in tactics:
            # Deterministic perturbation based on call count
            noise = ((self.call_count * 7 + hash(t.name) * 13) % 100) / 1000.0
            t.score = max(0.0, min(1.0, t.score + noise - 0.05))
        return tactics

    def generate_sketch_text(self, theorem: TheoremStatement) -> str:
        """Generate a textual proof sketch (like a mini reasoning trace)."""
        lines = [f"To prove {theorem.conclusion}:"]
        goal = theorem.conclusion
        if goal.kind == ExprType.IMPLIES:
            lines.append(f"  1. Assume {goal.args[0]}.")
            lines.append(f"  2. Show {goal.args[1]} follows.")
        elif goal.kind == ExprType.AND:
            lines.append(f"  1. Prove {goal.args[0]}.")
            lines.append(f"  2. Prove {goal.args[1]}.")
        elif goal.kind == ExprType.FORALL:
            lines.append(f"  1. Take arbitrary {goal.var}.")
            lines.append(f"  2. Show {goal.body}.")
        elif goal.kind == ExprType.EQ:
            lines.append(f"  1. Simplify both sides.")
            lines.append(f"  2. Check they are equal.")
        else:
            lines.append("  1. Search for applicable lemma or hypothesis.")
        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        return {"calls": self.call_count, "seed": self.seed}


class DraftSketchProver:
    """
    End-to-end Draft/Sketch/Prove pipeline.
    Orchestrates: DraftEngine → SketchEngine → StepProver + TreeSearch.
    """

    def __init__(self, config: Optional[ProverConfig] = None):
        self.config = config or ProverConfig()
        self.draft = DraftEngine()
        self.sketch = SketchEngine()
        self.masker = ErrorMasker()
        self.llm = MockLLM()
        self.kernel = TheoremProverKernel(self.config)

    def draft_sketch_prove(
        self,
        theorem: TheoremStatement,
        axioms: Optional[AxiomSet] = None,
    ) -> Dict[str, Any]:
        """
        Full pipeline: draft a sketch, formalize to subgoals,
        then prove each subgoal with tree search.
        """
        start = time.time()
        axs = axioms or AxiomSet()
        verbose = self.config.verbose

        # ── PHASE 1: DRAFT ───────────────────────────────────────────────
        if verbose:
            print(f"\n[DRAFT] Generating proof sketch for {theorem.name}...")
        proof_sketch = self.draft.generate_sketch(theorem)
        if verbose:
            for line in proof_sketch.to_lines():
                print(f"  {line}")

        # Mock LLM textual sketch
        llm_text = self.llm.generate_sketch_text(theorem)
        if verbose:
            print(f"\n[LLM Sketch]\n{llm_text}")

        # ── PHASE 2: SKETCH ──────────────────────────────────────────────
        if verbose:
            print(f"\n[SKETCH] Formalizing into subgoals...")
        subgoals = self.sketch.formalize(proof_sketch)
        if verbose:
            for sg in subgoals:
                print(f"  • [{sg.label}] {sg.hypotheses} ⊢ {sg.goal}  hints={sg.hints}")

        # ── PHASE 3: PROVE ─────────────────────────────────────────────────
        if verbose:
            print(f"\n[PROVE] Running step prover + tree search...")

        all_proofs: List[ProofState] = []
        any_admitted = False

        for sg in subgoals:
            result = self.kernel.prove(sg.goal, hypotheses=sg.hypotheses, axioms=axs)
            if result.success:
                all_proofs.append(result.proof)
                if verbose:
                    print(f"  ✓ [{sg.label}] proved in {result.tactics_used} tactics")
            else:
                # Try with LLM-guided tactic prediction instead of default generator
                initial = ProofState(
                    goals=[sg.to_sequent()],
                    history=[],
                    depth=0,
                    score=0.0,
                )
                llm_tactics = self.llm.predict_tactic(initial, axs)
                for tactic in llm_tactics[:3]:
                    te = TacticEngine()
                    results = te.apply(initial, tactic, axs)
                    for r in results:
                        if r.is_complete():
                            all_proofs.append(r)
                            if verbose:
                                print(f"  ✓ [{sg.label}] proved via LLM tactic {tactic}")
                            break
                    else:
                        continue
                    break
                else:
                    # Mask with sorry
                    any_admitted = True
                    masked = self.masker.mask_invalid(initial, Tactic("unknown"))
                    all_proofs.append(masked)
                    if verbose:
                        print(f"  ⚠ [{sg.label}] admitted with sorry")

        elapsed = time.time() - start

        # Combine all proof histories
        combined_history: List[Tactic] = []
        for p in all_proofs:
            combined_history.extend(p.history)

        success = not any_admitted and len(all_proofs) == len(subgoals)

        return {
            "theorem": str(theorem),
            "phases": ["draft", "sketch", "prove"],
            "sketch_lines": proof_sketch.to_lines(),
            "subgoals_count": len(subgoals),
            "proved_count": sum(1 for p in all_proofs if not any(t.name == "sorry" for t in p.history)),
            "admitted_count": sum(1 for p in all_proofs if any(t.name == "sorry" for t in p.history)),
            "success": success,
            "total_tactics": len(combined_history),
            "time_taken": elapsed,
            "proof_steps": [str(t) for t in combined_history],
            "llm_calls": self.llm.call_count,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# KERNEL — TheoremProverKernel (MAGNATRIX Layer 9 Bridge)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ProverConfig:
    """Configuration for the theorem prover kernel."""
    strategy: SearchStrategy = SearchStrategy.BEST_FIRST
    max_depth: int = 50
    max_nodes: int = 10_000
    expansion_width: int = 5
    length_norm_alpha: float = 0.5
    timeout_seconds: float = 60.0
    verbose: bool = False


@dataclass
class ProverResult:
    """Result of a theorem proving attempt."""
    success: bool
    proof: Optional[ProofState] = None
    tactics_used: int = 0
    nodes_explored: int = 0
    time_taken: float = 0.0
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "tactics_used": self.tactics_used,
            "nodes_explored": self.nodes_explored,
            "time_taken": self.time_taken,
            "error_message": self.error_message,
            "proof_steps": [str(t) for t in (self.proof.history if self.proof else [])],
        }


class TheoremProverKernel:
    """
    MAGNATRIX-OS AI Layer Kernel for Theorem Proving.
    Bridges symbolic logic engine to the broader MAGNATRIX ecosystem.
    """

    def __init__(self, config: Optional[ProverConfig] = None):
        self.config = config or ProverConfig()
        self.engine = SearchEngine(
            strategy=self.config.strategy,
            max_depth=self.config.max_depth,
            max_nodes=self.config.max_nodes,
            expansion_width=self.config.expansion_width,
            length_norm_alpha=self.config.length_norm_alpha,
        )
        self.generator = TacticGenerator()
        self.printer = ProofPrinter()
        self.heuristic = HeuristicScorer()
        self.axioms: AxiomSet = AxiomSet()
        self._layer_id: str = "MAGNATRIX-AI-9"
        self._version: str = "1.0.0-native"

    # ── Public API ─────────────────────────────────────────────────────────

    def prove(
        self,
        goal: Expr,
        hypotheses: Optional[List[Expr]] = None,
        axioms: Optional[AxiomSet] = None,
    ) -> ProverResult:
        """
        Attempt to prove a theorem: hypotheses ⊢ goal.
        """
        start = time.time()
        hyps = hypotheses or []
        axs = axioms or self.axioms

        initial_state = ProofState(
            goals=[Sequent(hyps, goal, "main")],
            history=[],
            depth=0,
            score=0.0,
        )

        if self.config.verbose:
            print(f"[Prover] Goal: {goal}")
            print(f"[Prover] Hypotheses: {hyps}")
            print(f"[Prover] Strategy: {self.config.strategy.name}")

        proof = self.engine.search(
            initial_state,
            axs,
            self.generator.generate,
            timeout_seconds=self.config.timeout_seconds,
        )

        elapsed = time.time() - start

        if proof:
            return ProverResult(
                success=True,
                proof=proof,
                tactics_used=len(proof.history),
                nodes_explored=proof.node_id,
                time_taken=elapsed,
            )
        else:
            return ProverResult(
                success=False,
                tactics_used=0,
                nodes_explored=0,
                time_taken=elapsed,
                error_message="Proof search exhausted without finding a proof.",
            )

    def verify_proof(self, state: ProofState) -> bool:
        """Verify that a proof state is complete and valid."""
        return state.is_complete() and all(
            t.name in self.engine.tactic_engine._tactics
            for t in state.history
        )

    def print_proof(self, result: ProverResult) -> str:
        if result.proof:
            return self.printer.print_proof(result.proof)
        return "No proof found."

    def add_axiom(self, axiom: Axiom) -> None:
        self.axioms.add_axiom(axiom)

    def add_definition(self, name: str, definition: Expr) -> None:
        self.axioms.add_definition(name, definition)

    # ── MAGNATRIX Bridge ───────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        return {
            "layer": self._layer_id,
            "version": self._version,
            "strategy": self.config.strategy.name,
            "axioms_loaded": len(self.axioms.axioms),
            "definitions_loaded": len(self.axioms.definitions),
        }

    def handle_event(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle events from MAGNATRIX orchestrator."""
        if event_type == "prove":
            goal_str = payload.get("goal", "")
            # Parse goal from string (basic)
            goal = self._parse_expr(goal_str)
            result = self.prove(goal)
            return result.to_dict()
        
        if event_type == "status":
            return self.get_status()
        
        if event_type == "load_axioms":
            axioms_data = payload.get("axioms", [])
            for ax_data in axioms_data:
                axiom = Axiom(
                    name=ax_data.get("name", "unnamed"),
                    conclusion=self._parse_expr(ax_data.get("conclusion", "")),
                )
                self.add_axiom(axiom)
            return {"loaded": len(axioms_data)}

        if event_type == "draft_sketch_prove":
            # Full pipeline: draft → sketch → prove
            name = payload.get("name", "unnamed")
            goal_str = payload.get("goal", "")
            hyps_strs = payload.get("hypotheses", [])
            goal = self._parse_expr(goal_str)
            hyps = [self._parse_expr(h) for h in hyps_strs]
            theorem = TheoremStatement(name=name, hypotheses=hyps, conclusion=goal)
            pipeline = DraftSketchProver(self.config)
            return pipeline.draft_sketch_prove(theorem, self.axioms)
        
        return {"error": f"Unknown event type: {event_type}"}

    @staticmethod
    def _parse_expr(s: str) -> Expr:
        """Basic parser for expressions from strings."""
        s = s.strip()
        if not s:
            return Expr.const("true")
        
        # Handle simple variables and constants
        if s.isalnum() and s.islower():
            return Expr.var(s)
        if s in ("true", "false", "0", "1"):
            return Expr.const(s)
        
        # Handle simple implications: A -> B
        if "->" in s:
            parts = s.split("->", 1)
            return Expr.implies(
                TheoremProverKernel._parse_expr(parts[0]),
                TheoremProverKernel._parse_expr(parts[1]),
            )
        
        # Handle conjunction: A /\ B
        if "/\\" in s or "and" in s.lower():
            parts = s.replace("/\\", " AND ").split(" AND ", 1)
            return Expr.and_(
                TheoremProverKernel._parse_expr(parts[0]),
                TheoremProverKernel._parse_expr(parts[1]),
            )
        
        # Handle disjunction: A \/ B
        if "\\/" in s or "or" in s.lower():
            parts = s.replace("\\/", " OR ").split(" OR ", 1)
            return Expr.or_(
                TheoremProverKernel._parse_expr(parts[0]),
                TheoremProverKernel._parse_expr(parts[1]),
            )
        
        # Handle equality: A = B
        if "=" in s and "!=" not in s and "=>" not in s:
            parts = s.split("=", 1)
            return Expr.eq(
                TheoremProverKernel._parse_expr(parts[0]),
                TheoremProverKernel._parse_expr(parts[1]),
            )
        
        return Expr.const(s)


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO / SELF-TEST SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════════

def _demo_identity():
    """Prove: A → A"""
    print("\n" + "=" * 60)
    print("DEMO 1: Identity — Prove A → A")
    print("=" * 60)
    
    A = Expr.var("A")
    goal = Expr.implies(A, A)
    
    kernel = TheoremProverKernel(ProverConfig(verbose=True))
    result = kernel.prove(goal)
    
    print(f"\nResult: {'✓ PROVED' if result.success else '✗ FAILED'}")
    print(f"Tactics: {result.tactics_used}")
    print(f"Time: {result.time_taken:.4f}s")
    print("\nProof:")
    print(kernel.print_proof(result))
    return result.success


def _demo_modus_ponens():
    """Prove: A ∧ (A → B) → B"""
    print("\n" + "=" * 60)
    print("DEMO 2: Modus Ponens — Prove A ∧ (A → B) → B")
    print("=" * 60)
    
    A, B = Expr.var("A"), Expr.var("B")
    goal = Expr.implies(Expr.and_(A, Expr.implies(A, B)), B)
    
    kernel = TheoremProverKernel(ProverConfig(verbose=True))
    result = kernel.prove(goal)
    
    print(f"\nResult: {'✓ PROVED' if result.success else '✗ FAILED'}")
    print(f"Tactics: {result.tactics_used}")
    print(f"Time: {result.time_taken:.4f}s")
    print("\nProof:")
    print(kernel.print_proof(result))
    return result.success


def _demo_conjunction():
    """Prove: A → (B → (A ∧ B))"""
    print("\n" + "=" * 60)
    print("DEMO 3: Conjunction Introduction — Prove A → (B → (A ∧ B))")
    print("=" * 60)
    
    A, B = Expr.var("A"), Expr.var("B")
    goal = Expr.implies(A, Expr.implies(B, Expr.and_(A, B)))
    
    kernel = TheoremProverKernel(ProverConfig(verbose=True))
    result = kernel.prove(goal)
    
    print(f"\nResult: {'✓ PROVED' if result.success else '✗ FAILED'}")
    print(f"Tactics: {result.tactics_used}")
    print(f"Time: {result.time_taken:.4f}s")
    print("\nProof:")
    print(kernel.print_proof(result))
    return result.success


def _demo_reflexivity():
    """Prove: ∀x. x = x"""
    print("\n" + "=" * 60)
    print("DEMO 4: Reflexivity — Prove ∀x. x = x")
    print("=" * 60)
    
    x = Expr.var("x")
    goal = Expr.forall("x", Expr.eq(x, x))
    
    kernel = TheoremProverKernel(ProverConfig(verbose=True))
    result = kernel.prove(goal)
    
    print(f"\nResult: {'✓ PROVED' if result.success else '✗ FAILED'}")
    print(f"Tactics: {result.tactics_used}")
    print(f"Time: {result.time_taken:.4f}s")
    print("\nProof:")
    print(kernel.print_proof(result))
    return result.success


def _demo_transitivity():
    """Prove: (a = b ∧ b = c) → a = c  (with hypotheses)"""
    print("\n" + "=" * 60)
    print("DEMO 5: Transitivity — Prove (a = b ∧ b = c) → a = c")
    print("=" * 60)
    
    a, b, c = Expr.var("a"), Expr.var("b"), Expr.var("c")
    goal = Expr.implies(Expr.and_(Expr.eq(a, b), Expr.eq(b, c)), Expr.eq(a, c))
    
    kernel = TheoremProverKernel(ProverConfig(verbose=True))
    result = kernel.prove(goal)
    
    print(f"\nResult: {'✓ PROVED' if result.success else '✗ FAILED'}")
    print(f"Tactics: {result.tactics_used}")
    print(f"Time: {result.time_taken:.4f}s")
    print("\nProof:")
    print(kernel.print_proof(result))
    return result.success


def _demo_negation():
    """Prove: A → ¬¬A"""
    print("\n" + "=" * 60)
    print("DEMO 6: Double Negation — Prove A → ¬¬A")
    print("=" * 60)
    
    A = Expr.var("A")
    goal = Expr.implies(A, Expr.not_(Expr.not_(A)))
    
    kernel = TheoremProverKernel(ProverConfig(verbose=True))
    result = kernel.prove(goal)
    
    print(f"\nResult: {'✓ PROVED' if result.success else '✗ FAILED'}")
    print(f"Tactics: {result.tactics_used}")
    print(f"Time: {result.time_taken:.4f}s")
    print("\nProof:")
    print(kernel.print_proof(result))
    return result.success


def _demo_biconditional():
    """Prove: A ↔ A"""
    print("\n" + "=" * 60)
    print("DEMO 7: Biconditional Identity — Prove A ↔ A")
    print("=" * 60)
    
    A = Expr.var("A")
    goal = Expr.iff(A, A)
    
    kernel = TheoremProverKernel(ProverConfig(verbose=True))
    result = kernel.prove(goal)
    
    print(f"\nResult: {'✓ PROVED' if result.success else '✗ FAILED'}")
    print(f"Tactics: {result.tactics_used}")
    print(f"Time: {result.time_taken:.4f}s")
    print("\nProof:")
    print(kernel.print_proof(result))
    return result.success


def _demo_disjunction():
    """Prove: A → A ∨ B"""
    print("\n" + "=" * 60)
    print("DEMO 8: Disjunction Intro Left — Prove A → (A ∨ B)")
    print("=" * 60)
    
    A, B = Expr.var("A"), Expr.var("B")
    goal = Expr.implies(A, Expr.or_(A, B))
    
    kernel = TheoremProverKernel(ProverConfig(verbose=True))
    result = kernel.prove(goal)
    
    print(f"\nResult: {'✓ PROVED' if result.success else '✗ FAILED'}")
    print(f"Tactics: {result.tactics_used}")
    print(f"Time: {result.time_taken:.4f}s")
    print("\nProof:")
    print(kernel.print_proof(result))
    return result.success


def _demo_axiom_driven():
    """Prove using axioms: from (P → Q) and P, prove Q"""
    print("\n" + "=" * 60)
    print("DEMO 9: Axiom-Driven — From P→Q and P, prove Q")
    print("=" * 60)
    
    P, Q = Expr.var("P"), Expr.var("Q")
    hypotheses = [Expr.implies(P, Q), P]
    goal = Q
    
    kernel = TheoremProverKernel(ProverConfig(verbose=True))
    result = kernel.prove(goal, hypotheses=hypotheses)
    
    print(f"\nResult: {'✓ PROVED' if result.success else '✗ FAILED'}")
    print(f"Tactics: {result.tactics_used}")
    print(f"Time: {result.time_taken:.4f}s")
    print("\nProof:")
    print(kernel.print_proof(result))
    return result.success


def _demo_kernel_status():
    """Show kernel status and event handling."""
    print("\n" + "=" * 60)
    print("DEMO 10: Kernel Status & Event Bridge")
    print("=" * 60)
    
    kernel = TheoremProverKernel()
    
    # Status
    status = kernel.get_status()
    print(f"\nKernel Status:")
    for k, v in status.items():
        print(f"  {k}: {v}")
    
    # Event: prove
    event_result = kernel.handle_event("prove", {"goal": "A -> A"})
    print(f"\nEvent 'prove' result:")
    print(f"  success: {event_result.get('success')}")
    print(f"  tactics_used: {event_result.get('tactics_used')}")
    print(f"  proof_steps: {event_result.get('proof_steps', [])}")
    
    return True


def _demo_draft_sketch_prove():
    """Demo the full Draft/Sketch/Prove pipeline."""
    print("\n" + "=" * 60)
    print("DEMO 11: Draft/Sketch/Prove Pipeline — A → (A ∧ A)")
    print("=" * 60)
    
    A = Expr.var("A")
    theorem = TheoremStatement(
        name="idempotent_and",
        hypotheses=[],
        conclusion=Expr.implies(A, Expr.and_(A, A)),
    )
    
    pipeline = DraftSketchProver(ProverConfig(verbose=True))
    result = pipeline.draft_sketch_prove(theorem)
    
    print(f"\nPipeline Result:")
    print(f"  success: {result['success']}")
    print(f"  subgoals: {result['subgoals_count']}")
    print(f"  proved: {result['proved_count']}")
    print(f"  admitted: {result['admitted_count']}")
    print(f"  total_tactics: {result['total_tactics']}")
    print(f"  time: {result['time_taken']:.4f}s")
    print(f"  llm_calls: {result['llm_calls']}")
    print(f"\nProof Steps:")
    for step in result['proof_steps']:
        print(f"  • {step}")
    
    return result['success']


def _run_all_demos():
    """Run all demo scenarios and report summary."""
    print("\n" + "█" * 60)
    print("█  MAGNATRIX-OS Theorem Prover Native — Self-Test Suite")
    print("█" * 60)
    
    demos = [
        ("Identity (A → A)", _demo_identity),
        ("Modus Ponens", _demo_modus_ponens),
        ("Conjunction Intro", _demo_conjunction),
        ("Reflexivity (∀x. x=x)", _demo_reflexivity),
        ("Transitivity", _demo_transitivity),
        ("Double Negation", _demo_negation),
        ("Biconditional (A ↔ A)", _demo_biconditional),
        ("Disjunction Intro", _demo_disjunction),
        ("Axiom-Driven", _demo_axiom_driven),
        ("Kernel Status", _demo_kernel_status),
        ("Draft/Sketch/Prove", _demo_draft_sketch_prove),
    ]
    
    passed = 0
    failed = 0
    
    for name, demo_fn in demos:
        try:
            ok = demo_fn()
            if ok:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n[ERROR in {name}]: {e}")
            failed += 1
    
    print("\n" + "█" * 60)
    print(f"█  Results: {passed} passed / {failed} failed / {len(demos)} total")
    print("█" * 60)
    
    return failed == 0


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    ok = _run_all_demos()
    sys.exit(0 if ok else 1)
