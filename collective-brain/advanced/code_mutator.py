#!/usr/bin/env python3
"""
code_mutator.py — MAGNATRIX Self-Modifying Code Engine
Batch Super AI — File 1/3

Engine self-modifying code: AI analyzes, mutates, validates, and applies
improved versions of its own functions.

Strategies: speed | memory | correctness | robustness
Safety: every mutant must be output-identical on the test suite.
"""
import ast
import copy
import time
import types
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


# ── data structures ──────────────────────────────────────────────────────────

@dataclass
class AnalysisResult:
    func_name: str
    complexity_score: float          # crude cyclomatic proxy 0-1
    has_loops: bool
    has_recursion: bool
    has_nested_loops: bool
    bottleneck_hints: List[str] = field(default_factory=list)


@dataclass
class Mutant:
    strategy: str
    source: str
    func_name: str
    speed_ms: float = 0.0
    memory_bytes: int = 0
    correctness_passed: bool = False
    improvement_pct: float = 0.0
    applied: bool = False


# ── analyzer ───────────────────────────────────────────────────────────────

class FunctionAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.loop_depth = 0
        self.max_loop_depth = 0
        self.has_loops = False
        self.has_recursion = False
        self.func_name = ""
        self.hints: List[str] = []
        self.has_nested_loops = False

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.func_name = node.name
        self.generic_visit(node)

    def visit_For(self, node: ast.For):
        self.has_loops = True
        self.loop_depth += 1
        self.max_loop_depth = max(self.max_loop_depth, self.loop_depth)
        self.generic_visit(node)
        self.loop_depth -= 1

    def visit_While(self, node: ast.While):
        self.has_loops = True
        self.loop_depth += 1
        self.max_loop_depth = max(self.max_loop_depth, self.loop_depth)
        self.generic_visit(node)
        self.loop_depth -= 1

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == self.func_name:
            self.has_recursion = True
        self.generic_visit(node)


class _RecursionChecker(ast.NodeVisitor):
    def __init__(self, func_name: str):
        self.func_name = func_name
        self.is_recursive = False

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == self.func_name:
            self.is_recursive = True
        self.generic_visit(node)


def analyze_function(func_source: str) -> AnalysisResult:
    tree = ast.parse(func_source.strip())
    visitor = FunctionAnalyzer()
    visitor.visit(tree)
    visitor.has_nested_loops = visitor.max_loop_depth > 1

    hints = []
    if visitor.has_nested_loops:
        hints.append("nested loops — candidate for vectorization/loop fusion")
    if visitor.has_recursion:
        hints.append("recursion — candidate for memoization or iterative rewrite")
    if visitor.has_loops and not visitor.has_nested_loops:
        hints.append("simple loops — candidate for unrolling or comprehension")
    if not visitor.has_loops:
        hints.append("no loops — likely I/O bound or arithmetic micro-optimisation")

    # crude complexity: nested loops + recursion + AST node count
    node_count = sum(1 for _ in ast.walk(tree))
    complexity = min(1.0, (visitor.max_loop_depth * 0.25 +
                          (0.15 if visitor.has_recursion else 0) +
                          min(0.4, node_count / 200)))

    return AnalysisResult(
        func_name=visitor.func_name,
        complexity_score=round(complexity, 3),
        has_loops=visitor.has_loops,
        has_recursion=visitor.has_recursion,
        has_nested_loops=visitor.max_loop_depth > 1,
        bottleneck_hints=hints,
    )


# ── mutators ─────────────────────────────────────────────────────────────────

class MutatorEngine:
    STRATEGIES = {"speed", "memory", "correctness", "robustness"}

    @classmethod
    def mutate(cls, func_source: str, strategy: str) -> Optional[str]:
        if strategy not in cls.STRATEGIES:
            raise ValueError(f"unknown strategy {strategy}")
        tree = ast.parse(func_source.strip())
        if strategy == "speed":
            tree = cls._apply_memoization(tree)
            tree = cls._apply_builtin_replace(tree)
        elif strategy == "memory":
            tree = cls._apply_generator_replace(tree)
            tree = cls._apply_slots_hint(tree)
        elif strategy == "correctness":
            tree = cls._apply_input_guard(tree)
            tree = cls._apply_division_guard(tree)
        elif strategy == "robustness":
            tree = cls._apply_try_wrap(tree)
            tree = cls._apply_type_assert(tree)
        return ast.unparse(tree)

    # ── speed transforms ──
    @staticmethod
    def _apply_memoization(tree: ast.AST) -> ast.AST:
        class MemoTransformer(ast.NodeTransformer):
            def visit_FunctionDef(self, node: ast.FunctionDef):
                # only memoize if function is recursive
                checker = _RecursionChecker(node.name)
                checker.visit(node)
                if not checker.is_recursive:
                    return self.generic_visit(node)
                # inject @functools.lru_cache(maxsize=None)
                dec = ast.Attribute(
                    value=ast.Attribute(
                        value=ast.Name(id="functools", ctx=ast.Load()),
                        attr="lru_cache",
                        ctx=ast.Load()),
                    attr="__call__",
                    ctx=ast.Load())
                dec_call = ast.Call(func=dec, args=[],
                                    keywords=[ast.keyword(arg="maxsize", value=ast.Constant(value=None))])
                node.decorator_list.insert(0, dec_call)
                return self.generic_visit(node)
        return MemoTransformer().visit(tree)

    @staticmethod
    def _apply_loop_unroll(tree: ast.AST) -> ast.AST:
        class UnrollTransformer(ast.NodeTransformer):
            def visit_For(self, node: ast.For):
                # unroll range(3) or range(4) statically
                if (isinstance(node.iter, ast.Call) and
                        isinstance(node.iter.func, ast.Name) and
                        node.iter.func.id == "range" and
                        len(node.iter.args) == 1 and
                        isinstance(node.iter.args[0], ast.Constant) and
                        isinstance(node.iter.args[0].value, int) and
                        node.iter.args[0].value <= 4):
                    n = node.iter.args[0].value
                    stmts = []
                    for i in range(n):
                        subst = copy.deepcopy(node.body)
                        for sub in ast.walk(ast.Module(body=subst, type_ignores=[])):
                            if isinstance(sub, ast.Name) and sub.id == node.target.id:
                                sub.id = str(i)
                        stmts.extend(subst)
                    return stmts
                return self.generic_visit(node)
        return UnrollTransformer().visit(tree)

    @staticmethod
    def _apply_builtin_replace(tree: ast.AST) -> ast.AST:
        class BuiltinTransformer(ast.NodeTransformer):
            def visit_Call(self, node: ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id == "sum" and len(node.args) == 1:
                        pass
                return self.generic_visit(node)
        return BuiltinTransformer().visit(tree)

    # ── memory transforms ──
    @staticmethod
    def _apply_generator_replace(tree: ast.AST) -> ast.AST:
        class GenTransformer(ast.NodeTransformer):
            def visit_ListComp(self, node: ast.ListComp):
                # Don't auto-convert listcomp because consumers may need list
                return self.generic_visit(node)
        return GenTransformer().visit(tree)

    @staticmethod
    def _apply_slots_hint(tree: ast.AST) -> ast.AST:
        class SlotsTransformer(ast.NodeTransformer):
            def visit_ClassDef(self, node: ast.ClassDef):
                fields = []
                for stmt in node.body:
                    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                        fields.append(stmt.target.id)
                if fields and not any(isinstance(b, ast.Assign) and
                                       any(isinstance(t, ast.Name) and t.id == "__slots__"
                                           for t in b.targets)
                                       for b in node.body):
                    slots = ast.Assign(
                        targets=[ast.Name(id="__slots__", ctx=ast.Store())],
                        value=ast.Tuple(elts=[ast.Constant(value=f) for f in fields], ctx=ast.Load()))
                    node.body.insert(0, slots)
                return self.generic_visit(node)
        return SlotsTransformer().visit(tree)

    # ── correctness transforms ──
    @staticmethod
    def _apply_input_guard(tree: ast.AST) -> ast.AST:
        class GuardTransformer(ast.NodeTransformer):
            def visit_FunctionDef(self, node: ast.FunctionDef):
                guards = []
                for arg in node.args.args:
                    ann = arg.annotation
                    if isinstance(ann, ast.Subscript):
                        continue
                    if isinstance(ann, ast.Name) and ann.id in ("str", "list", "dict", "tuple", "set"):
                        continue
                    guard = ast.If(
                        test=ast.BoolOp(
                            op=ast.Or(),
                            values=[
                                ast.Compare(
                                    left=ast.Name(id=arg.arg, ctx=ast.Load()),
                                    ops=[ast.Is()],
                                    comparators=[ast.Constant(value=None)]),
                                ast.Call(
                                    func=ast.Name(id="isinstance", ctx=ast.Load()),
                                    args=[
                                        ast.Name(id=arg.arg, ctx=ast.Load()),
                                        ast.Tuple(elts=[ast.Name(id="int", ctx=ast.Load()),
                                                           ast.Name(id="float", ctx=ast.Load())],
                                                      ctx=ast.Load())],
                                    keywords=[])]),
                        body=[ast.Raise(
                            exc=ast.Call(
                                func=ast.Name(id="TypeError", ctx=ast.Load()),
                                args=[ast.Constant(
                                    value=f"{arg.arg} must be numeric and not None")],
                                keywords=[]))],
                        orelse=[])
                    guards.append(guard)
                node.body = guards + node.body
                return self.generic_visit(node)
        return GuardTransformer().visit(tree)

    @staticmethod
    def _apply_division_guard(tree: ast.AST) -> ast.AST:
        class DivGuard(ast.NodeTransformer):
            def visit_BinOp(self, node: ast.BinOp):
                if isinstance(node.op, ast.Div):
                    safe = ast.IfExp(
                        test=ast.Compare(
                            left=node.right,
                            ops=[ast.Eq()],
                            comparators=[ast.Constant(value=0)]),
                        body=ast.Constant(value=0),
                        orelse=ast.BinOp(left=node.left, op=ast.Div(), right=node.right))
                    return ast.copy_location(safe, node)
                return self.generic_visit(node)
        return DivGuard().visit(tree)

    # ── robustness transforms ──
    @staticmethod
    def _apply_try_wrap(tree: ast.AST) -> ast.AST:
        class TryWrap(ast.NodeTransformer):
            def visit_FunctionDef(self, node: ast.FunctionDef):
                new_body = [ast.Try(
                    body=node.body,
                    handlers=[ast.ExceptHandler(
                        type=ast.Name(id="Exception", ctx=ast.Load()),
                        name=None,
                        body=[ast.Return(value=ast.Constant(value=None))])],
                    orelse=[],
                    finalbody=[])]
                node.body = new_body
                return self.generic_visit(node)
        return TryWrap().visit(tree)

    @staticmethod
    def _apply_type_assert(tree: ast.AST) -> ast.AST:
        # already handled in correctness via isinstance guard
        return tree


# ── validator ────────────────────────────────────────────────────────────────

class MutantValidator:
    THRESHOLD_PCT = 10.0

    @classmethod
    def validate_mutant(cls, original_source: str, mutant_source: str,
                        test_cases: List[Tuple[Tuple[Any, ...], Any]]) -> Mutant:
        mutant = Mutant(strategy="unknown", source=mutant_source, func_name="")
        try:
            mutant_module = types.ModuleType("mutant_module")
            exec(mutant_source, mutant_module.__dict__)
            orig_module = types.ModuleType("orig_module")
            exec(original_source, orig_module.__dict__)
        except Exception as e:
            mutant.correctness_passed = False
            return mutant

        orig_func = cls._extract_function(orig_module)
        mutant_func = cls._extract_function(mutant_module)
        mutant.func_name = orig_func.__name__ if orig_func else "unknown"

        if orig_func is None or mutant_func is None:
            mutant.correctness_passed = False
            return mutant

        # correctness: output-identical on every test case
        for args, expected in test_cases:
            try:
                orig_out = orig_func(*args)
                mut_out = mutant_func(*args)
                if type(orig_out) != type(mut_out):
                    mutant.correctness_passed = False
                    return mutant
                if isinstance(orig_out, float):
                    if abs(orig_out - mut_out) > 1e-9:
                        mutant.correctness_passed = False
                        return mutant
                elif orig_out != mut_out:
                    mutant.correctness_passed = False
                    return mutant
            except Exception:
                mutant.correctness_passed = False
                return mutant

        mutant.correctness_passed = True

        # benchmark speed
        speed_orig = cls._benchmark(orig_func, test_cases)
        speed_mut = cls._benchmark(mutant_func, test_cases)
        mutant.speed_ms = round(speed_mut, 3)

        # benchmark memory (crude: bytecode size proxy)
        mutant.memory_bytes = len(mutant_source.encode("utf-8"))

        if speed_orig > 0:
            mutant.improvement_pct = round((speed_orig - speed_mut) / speed_orig * 100, 2)
        else:
            mutant.improvement_pct = 0.0

        return mutant

    @staticmethod
    def _extract_function(module: types.ModuleType) -> Optional[Callable]:
        for name, obj in module.__dict__.items():
            if isinstance(obj, types.FunctionType) and not name.startswith("_"):
                return obj
        return None

    @staticmethod
    def _benchmark(func: Callable, test_cases: List[Tuple[Tuple[Any, ...], Any]],
                    runs: int = 1000) -> float:
        start = time.perf_counter()
        for _ in range(runs):
            for args, _ in test_cases:
                func(*args)
        return (time.perf_counter() - start) * 1000

    @classmethod
    def apply_if_better(cls, mutant: Mutant, threshold_pct: float = THRESHOLD_PCT) -> bool:
        if not mutant.correctness_passed:
            return False
        if mutant.improvement_pct >= threshold_pct:
            mutant.applied = True
            return True
        return False


# ── orchestrator ─────────────────────────────────────────────────────────────

class CodeMutator:
    def __init__(self):
        self.history: List[Mutant] = []
        self.applied_count = 0

    def evolve(self, func_source: str, strategy: str = "speed",
               test_cases: Optional[List[Tuple[Tuple[Any, ...], Any]]] = None) -> Optional[Mutant]:
        if test_cases is None:
            raise ValueError("test_cases required for safety")
        analysis = analyze_function(func_source)
        mutated_src = MutatorEngine.mutate(func_source, strategy)
        if mutated_src is None or mutated_src.strip() == func_source.strip():
            return None
        mutant = MutantValidator.validate_mutant(func_source, mutated_src, test_cases)
        mutant.strategy = strategy
        self.history.append(mutant)
        if MutantValidator.apply_if_better(mutant):
            self.applied_count += 1
        return mutant

    def stats(self) -> Dict[str, Any]:
        total = len(self.history)
        applied = sum(1 for m in self.history if m.applied)
        avg_improvement = sum(m.improvement_pct for m in self.history) / total if total else 0
        return {
            "total_mutants": total,
            "applied": applied,
            "rejected": total - applied,
            "avg_improvement_pct": round(avg_improvement, 2),
            "last_func": self.history[-1].func_name if self.history else None,
        }


# ── demo ───────────────────────────────────────────────────────────────────────

def demo_slow_sum(n: int) -> int:
    result = []
    for i in range(n):
        result.append(i * i)
    return sum(result)


def demo_fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return demo_fibonacci(n - 1) + demo_fibonacci(n - 2)


def demo_average(data: list[float]) -> float:
    total = sum(data)
    return total / len(data)


if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX Code Mutator — Self-Improvement Engine")
    print("=" * 60)

    import inspect
    mutator = CodeMutator()

    # ── demo 1: speed strategy on slow_sum ──
    src1 = inspect.getsource(demo_slow_sum)
    print(f"\n[1] ANALYZE → {demo_slow_sum.__name__}")
    a1 = analyze_function(src1)
    print(f"    complexity={a1.complexity_score} loops={a1.has_loops} "
          f"nested={a1.has_nested_loops} recursion={a1.has_recursion}")
    print(f"    hints: {a1.bottleneck_hints}")

    tc1 = [((10,), 285), ((100,), 328350), ((5,), 30)]
    m1 = mutator.evolve(src1, strategy="speed", test_cases=tc1)
    if m1:
        print(f"    mutant speed={m1.speed_ms}ms improvement={m1.improvement_pct}% "
              f"correct={m1.correctness_passed} applied={m1.applied}")
        if m1.applied:
            print(f"\n--- APPLIED MUTANT ({m1.strategy}) ---")
            import textwrap
            print(textwrap.indent(m1.source, "    "))
    else:
        print("    no mutation generated")

    # ── demo 2: correctness strategy on average ──
    src2 = inspect.getsource(demo_average)
    print(f"\n[2] ANALYZE → {demo_average.__name__}")
    a2 = analyze_function(src2)
    print(f"    complexity={a2.complexity_score} hints: {a2.bottleneck_hints}")

    tc2 = [(([1.0, 2.0, 3.0],), 2.0), (([5.0, 5.0],), 5.0)]
    m2 = mutator.evolve(src2, strategy="correctness", test_cases=tc2)
    if m2:
        print(f"    mutant improvement={m2.improvement_pct}% correct={m2.correctness_passed}")
        if m2.correctness_passed:
            print(f"\n--- CORRECTNESS MUTANT ---")
            import textwrap
            print(textwrap.indent(m2.source, "    "))

    # ── demo 3: robustness strategy on fibonacci ──
    src3 = inspect.getsource(demo_fibonacci)
    print(f"\n[3] ANALYZE → {demo_fibonacci.__name__}")
    a3 = analyze_function(src3)
    print(f"    complexity={a3.complexity_score} recursion={a3.has_recursion}")

    tc3 = [((0,), 0), ((1,), 1), ((10,), 55), ((15,), 610)]
    m3 = mutator.evolve(src3, strategy="robustness", test_cases=tc3)
    if m3:
        print(f"    mutant correct={m3.correctness_passed} applied={m3.applied}")
        if m3.correctness_passed:
            print(f"\n--- ROBUSTNESS MUTANT ---")
            import textwrap
            print(textwrap.indent(m3.source, "    "))

    # ── stats ──
    print("\n" + "=" * 60)
    print("MUTATOR STATS")
    print("=" * 60)
    for k, v in mutator.stats().items():
        print(f"  {k}: {v}")
    print("=" * 60)
