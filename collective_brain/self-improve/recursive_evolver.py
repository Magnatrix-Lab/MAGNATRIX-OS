"""
collective-brain/self-improve/recursive_evolver.py
==================================================
MAGNATRIX Recursive Self-Improvement Engine
Layer 14: Self-Improvement

Core: meta-circular code evolution — system that rewrites itself.
Patterns: genetic programming, AST mutation, fitness evaluation loop.
"""

import asyncio, ast, copy, hashlib, inspect, json, random, re, textwrap, time, uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable, Any, Tuple
from enum import Enum

class MutationType(Enum):
    INSERT = "insert"; DELETE = "delete"; MODIFY = "modify"
    SWAP = "swap"; WRAP = "wrap"

@dataclass
class Genome:
    id: str = field(default_factory=lambda: f"gen-{uuid.uuid4().hex[:8]}")
    source: str = ""                    # Python source code
    ast_tree: Optional[ast.AST] = None  # Parsed AST
    fitness: float = 0.0
    generation: int = 0
    parent_ids: List[str] = field(default_factory=list)
    mutations: List[Dict] = field(default_factory=list)
    lineage: List[str] = field(default_factory=list)

@dataclass
class FitnessSuite:
    """Test suite for evaluating code fitness"""
    tests: List[Dict] = field(default_factory=list)  # {input, expected, name}
    performance_targets: Dict = field(default_factory=dict)  # {latency_ms, memory_mb}
    correctness_weight: float = 0.6
    performance_weight: float = 0.2
    complexity_weight: float = 0.2

class ASTMutator:
    """AST-based code mutation engine"""

    SAFE_NODES = (ast.Name, ast.Constant, ast.BinOp, ast.Compare, ast.Call,
                  ast.Attribute, ast.Subscript, ast.If, ast.For, ast.While)

    def __init__(self, seed: int = None):
        self.rng = random.Random(seed)

    def mutate(self, source: str, num_mutations: int = 3) -> Tuple[str, List[Dict]]:
        """Apply random AST mutations to source code"""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return source, []

        mutations_log = []
        for _ in range(num_mutations):
            nodes = [n for n in ast.walk(tree) if isinstance(n, self.SAFE_NODES)]
            if not nodes:
                break
            node = self.rng.choice(nodes)
            mutation = self._apply_mutation(node)
            if mutation:
                mutations_log.append(mutation)

        new_source = ast.unparse(tree) if hasattr(ast, 'unparse') else source
        return new_source, mutations_log

    def _apply_mutation(self, node: ast.AST) -> Optional[Dict]:
        """Apply single safe mutation"""
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            old = node.value
            if isinstance(old, int):
                node.value = old + random.randint(-5, 5)
            else:
                node.value = old * random.uniform(0.5, 2.0)
            return {"type": "constant_modify", "old": old, "new": node.value}

        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            alternatives = ["x", "y", "z", "temp", "val", "result", "data"]
            old = node.id
            node.id = random.choice([a for a in alternatives if a != old])
            return {"type": "rename_var", "old": old, "new": node.id}

        if isinstance(node, ast.BinOp):
            ops = [ast.Add(), ast.Sub(), ast.Mult(), ast.Div(), ast.Pow()]
            old_type = type(node.op).__name__
            node.op = random.choice(ops)
            return {"type": "binop_swap", "old": old_type, "new": type(node.op).__name__}

        return None

    def crossover(self, source_a: str, source_b: str) -> str:
        """Crossover two code sources at function boundaries"""
        try:
            tree_a = ast.parse(source_a)
            tree_b = ast.parse(source_b)
        except SyntaxError:
            return source_a

        funcs_a = [n for n in ast.walk(tree_a) if isinstance(n, ast.FunctionDef)]
        funcs_b = [n for n in ast.walk(tree_b) if isinstance(n, ast.FunctionDef)]

        if not funcs_a or not funcs_b:
            return source_a

        # Swap one function
        swap_idx = random.randint(0, min(len(funcs_a), len(funcs_b)) - 1)
        if swap_idx < len(funcs_a) and swap_idx < len(funcs_b):
            funcs_a[swap_idx].body = funcs_b[swap_idx].body

        return ast.unparse(tree_a) if hasattr(ast, 'unparse') else source_a


class FitnessEvaluator:
    """Evaluate code fitness across multiple dimensions"""

    def evaluate(self, genome: Genome, suite: FitnessSuite) -> float:
        """Run fitness evaluation: correctness + performance + complexity"""
        scores = []

        # Correctness
        correct = 0
        for test in suite.tests:
            try:
                local_ns = {}
                exec(genome.source, {}, local_ns)
                # Find function and test
                func = None
                for obj in local_ns.values():
                    if callable(obj):
                        func = obj
                        break
                if func:
                    result = func(test["input"])
                    if result == test["expected"]:
                        correct += 1
            except Exception:
                pass
        correctness = correct / max(len(suite.tests), 1)
        scores.append(correctness * suite.correctness_weight)

        # Performance (simulated)
        perf = 1.0 - min(len(genome.source) / 10000, 1.0)
        scores.append(perf * suite.performance_weight)

        # Complexity (simpler is better)
        lines = genome.source.count('\n')
        complexity = 1.0 - min(lines / 200, 1.0)
        scores.append(complexity * suite.complexity_weight)

        return sum(scores)


class EvolutionEngine:
    """Main genetic programming evolution loop"""

    def __init__(self, population_size: int = 20, mutation_rate: float = 0.3):
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.mutator = ASTMutator()
        self.evaluator = FitnessEvaluator()
        self.generation = 0
        self.population: List[Genome] = []
        self.best_ever: Optional[Genome] = None
        self.history: List[Dict] = []

    def seed(self, source_code: str):
        """Seed population with initial code"""
        for i in range(self.population_size):
            genome = Genome(source=source_code, generation=0)
            self.population.append(genome)

    async def evolve(self, suite: FitnessSuite, generations: int = 10) -> Genome:
        """Run evolution loop"""
        for gen in range(generations):
            self.generation = gen

            # Evaluate all
            for genome in self.population:
                genome.fitness = self.evaluator.evaluate(genome, suite)

            # Sort by fitness
            self.population.sort(key=lambda g: g.fitness, reverse=True)

            # Track best
            current_best = self.population[0]
            if not self.best_ever or current_best.fitness > self.best_ever.fitness:
                self.best_ever = Genome(
                    id=current_best.id, source=current_best.source,
                    fitness=current_best.fitness, generation=gen,
                    lineage=current_best.lineage + [current_best.id]
                )

            self.history.append({
                "generation": gen,
                "best_fitness": current_best.fitness,
                "avg_fitness": sum(g.fitness for g in self.population) / len(self.population),
                "best_id": current_best.id
            })

            # Selection + reproduction
            new_population = []
            elites = int(self.population_size * 0.2)
            new_population.extend(copy.deepcopy(self.population[:elites]))

            while len(new_population) < self.population_size:
                parent = self._select_parent()
                child = self._reproduce(parent, gen)
                new_population.append(child)

            self.population = new_population

            await asyncio.sleep(0)  # Yield control

        return self.best_ever

    def _select_parent(self) -> Genome:
        """Tournament selection"""
        tournament = random.sample(self.population, min(3, len(self.population)))
        return max(tournament, key=lambda g: g.fitness)

    def _reproduce(self, parent: Genome, generation: int) -> Genome:
        """Create child via mutation or crossover"""
        child_source = parent.source
        mutations = []

        if random.random() < self.mutation_rate:
            child_source, mutations = self.mutator.mutate(parent.source)

        if random.random() < 0.1 and len(self.population) > 1:
            other = random.choice([g for g in self.population if g.id != parent.id])
            child_source = self.mutator.crossover(child_source, other.source)
            mutations.append({"type": "crossover", "parent": other.id})

        return Genome(
            source=child_source, generation=generation,
            parent_ids=[parent.id], mutations=mutations,
            lineage=parent.lineage + [parent.id]
        )

    def get_stats(self) -> Dict:
        return {
            "generation": self.generation,
            "population": len(self.population),
            "best_fitness": self.best_ever.fitness if self.best_ever else 0,
            "history_entries": len(self.history)
        }


class RecursiveEvolver:
    """
    Meta-circular: the evolver evolves itself.
    The ultimate self-improvement loop.
    """

    def __init__(self):
        self.engine = EvolutionEngine()
        self.improvement_log: List[Dict] = []

    async def improve_module(self, module_source: str, test_suite: FitnessSuite,
                            iterations: int = 5) -> Tuple[str, float]:
        """
        Improve a module via evolutionary programming.
        This is the core recursive self-improvement mechanism.
        """
        self.engine.seed(module_source)
        best = await self.engine.evolve(test_suite, iterations)

        self.improvement_log.append({
            "timestamp": time.time(),
            "original_size": len(module_source),
            "improved_size": len(best.source),
            "fitness_gain": best.fitness,
            "generations": iterations
        })

        return best.source, best.fitness

    def get_status(self) -> Dict:
        return {
            "engine": self.engine.get_stats(),
            "improvements": len(self.improvement_log),
            "last_improvement": self.improvement_log[-1] if self.improvement_log else None
        }


if __name__ == "__main__":
    async def demo():
        print("=" * 60)
        print("MAGNATRIX Recursive Self-Improvement Engine")
        print("=" * 60)

        source = 