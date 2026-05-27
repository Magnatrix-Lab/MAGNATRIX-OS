"""
MAGNATRIX — Native Cognitive Load Analyzer
═══════════════════════════════════════════
AMATI-PELAJARI-TIRU dari https://github.com/zakirullin/cognitive-load

"Cognitive Load is what matters" — living document yang diterjemahkan ke
native analyzer engine. Andrej Karpathy: "Probably the most true, least
practiced viewpoint." 9.8K+ stars, endorsed oleh Rob Pike (Unix/Go),
Elon Musk, John Ousterhout (Raft/Tcl), Addy Osmani (Chrome).

Patterns ditiru:
1. Cognitive Load Measurement — quantify thinking required untuk tasks
2. Intrinsic vs Extraneous Load — distinguish essential vs unnecessary complexity
3. Code Complexity Scoring — heuristics-based scoring per function/module
4. Shallow Module Detection — flag modules yang tidak provide meaningful abstraction
5. Deep Nesting Detection — early return analysis vs deeply nested structures
6. Working Memory Chunking — count conceptual chunks (functions, conditions, variables)
7. Naming Quality Score — assess how well names reduce cognitive overhead
8. Refactoring Suggestions — concrete simplifications dari analysis
9. Onboarding Readiness Metric — estimate time for new devs to contribute
10. Agent Prompt Optimization — apply cognitive load principles to agent instructions

Author: MAGNATRIX-OS
"""

from __future__ import annotations

import ast
import asyncio
import hashlib
import json
import os
import re
import textwrap
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


# ═══════════════════════════════════════════════════════════════════════════
# 1. COGNITIVE LOAD TYPES — Intrinsic vs Extraneous vs Germane
# ═══════════════════════════════════════════════════════════════════════════

class LoadType(Enum):
    INTRINSIC = "intrinsic"      # Essential complexity from the task itself
    EXTRANEOUS = "extraneous"    # Unnecessary complexity from poor presentation
    GERMANE = "germane"          # Load devoted to understanding the domain


@dataclass
class CognitiveLoadChunk:
    """Single conceptual chunk yang occupies working memory."""
    chunk_id: str
    description: str
    load_type: LoadType
    weight: float = 1.0  # how many "slots" it occupies (human working memory = ~4)
    location: Optional[str] = None  # file:line reference


# ═══════════════════════════════════════════════════════════════════════════
# 2. CODE COMPLEXITY SCORER — Heuristics-Based Analysis
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class FunctionScore:
    function_name: str
    line_count: int
    nesting_depth: int
    chunk_count: float
    cognitive_load: float  # total load score
    extraneous_load: float  # unnecessary load
    intrinsic_load: float  # essential load
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ModuleScore:
    module_name: str
    function_scores: List[FunctionScore] = field(default_factory=list)
    shallow_module_score: float = 0.0  # 0 = deep/good, 1 = shallow/bad
    total_lines: int = 0
    total_functions: int = 0
    average_load: float = 0.0
    max_load: float = 0.0
    onboarding_estimate_hours: float = 0.0  # estimated time to understand


class CodeComplexityScorer:
    """Scorer berdasarkan cognitive load heuristics dari zakirullin/cognitive-load."""

    # Working memory limit — George Miller's "magical number seven, plus or minus two"
    # Updated research suggests ~4 chunks for complex tasks
    WORKING_MEMORY_CAPACITY = 4.0

    # Load weights per issue type
    WEIGHTS = {
        "deep_nesting": 2.0,           # deeply nested if/for/while
        "long_function": 1.5,          # functions > 30 lines
        "many_params": 0.5,            # each param beyond 3
        "complex_condition": 1.0,      # compound boolean expressions
        "magic_number": 0.3,           # unexplained numeric literals
        "poor_naming": 1.0,            # unclear variable/function names
        "shallow_module": 0.5,         # module that doesn't hide complexity
        "global_state": 1.5,           # reliance on globals
        "side_effect": 0.8,            # hidden side effects
        "deep_inheritance": 1.0,       # inheritance chains > 3
        "callback_hell": 1.5,          # nested callbacks
        "string_concat": 0.2,          # building strings in loops
        "type_confusion": 0.5,         # unclear type expectations
    }

    def __init__(self):
        self._results: List[ModuleScore] = []

    def analyze_file(self, file_path: Union[str, Path], content: Optional[str] = None) -> ModuleScore:
        """Analyze satu Python file untuk cognitive load."""
        path = Path(file_path)
        if content is None:
            content = path.read_text(encoding="utf-8")

        module_name = path.stem
        lines = content.splitlines()
        total_lines = len(lines)

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return ModuleScore(
                module_name=module_name,
                total_lines=total_lines,
                total_functions=0,
                average_load=0.0,
                max_load=0.0,
                onboarding_estimate_hours=total_lines / 100,  # rough estimate
            )

        function_scores = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                score = self._analyze_function(node, content, lines)
                function_scores.append(score)

        # Calculate module-level scores
        total_funcs = len(function_scores)
        avg_load = sum(f.cognitive_load for f in function_scores) / total_funcs if total_funcs > 0 else 0
        max_load = max((f.cognitive_load for f in function_scores), default=0)

        # Shallow module detection: module exports too many things without hiding complexity
        # "A shallow module is one whose interface is complex relative to the functionality it provides"
        shallow_score = self._calculate_shallow_module_score(tree, function_scores, total_lines)

        # Onboarding estimate: hours until new dev can contribute
        # Based on total load and module complexity
        onboarding = self._estimate_onboarding(function_scores, total_lines)

        score = ModuleScore(
            module_name=module_name,
            function_scores=function_scores,
            shallow_module_score=shallow_score,
            total_lines=total_lines,
            total_functions=total_funcs,
            average_load=round(avg_load, 2),
            max_load=round(max_load, 2),
            onboarding_estimate_hours=round(onboarding, 1),
        )
        self._results.append(score)
        return score

    def _analyze_function(self, node: ast.FunctionDef, content: str, lines: List[str]) -> FunctionScore:
        func_name = node.name
        start_line = node.lineno - 1
        end_line = getattr(node, 'end_lineno', start_line + 1) - 1
        func_lines = lines[start_line:end_line + 1]
        line_count = len(func_lines)

        issues = []
        suggestions = []
        chunks = []

        # 1. Deep nesting detection
        max_depth = self._calculate_nesting_depth(node)
        if max_depth >= 4:
            issues.append(f"Deep nesting: {max_depth} levels (limit: 3)")
            suggestions.append("Use early returns to reduce nesting")
            chunks.append(CognitiveLoadChunk(
                chunk_id=f"{func_name}:nesting",
                description=f"{max_depth}-level nested control flow",
                load_type=LoadType.EXTRANEOUS,
                weight=self.WEIGHTS["deep_nesting"] * (max_depth - 3),
            ))

        # 2. Function length
        if line_count > 30:
            issues.append(f"Long function: {line_count} lines (limit: 30)")
            suggestions.append("Extract helper functions to reduce length")
            chunks.append(CognitiveLoadChunk(
                chunk_id=f"{func_name}:length",
                description=f"Function is {line_count} lines long",
                load_type=LoadType.EXTRANEOUS,
                weight=self.WEIGHTS["long_function"] * (line_count / 30),
            ))

        # 3. Parameter count
        param_count = len(node.args.args) + len(node.args.kwonlyargs)
        if param_count > 4:
            issues.append(f"Many parameters: {param_count} (limit: 4)")
            suggestions.append("Use a config object or dataclass for parameters")
            chunks.append(CognitiveLoadChunk(
                chunk_id=f"{func_name}:params",
                description=f"{param_count} parameters",
                load_type=LoadType.EXTRANEOUS,
                weight=self.WEIGHTS["many_params"] * (param_count - 4),
            ))

        # 4. Complex conditions
        complex_conditions = self._find_complex_conditions(node)
        if complex_conditions > 0:
            issues.append(f"Complex conditions: {complex_conditions}")
            suggestions.append("Break complex conditions into named boolean variables")
            chunks.append(CognitiveLoadChunk(
                chunk_id=f"{func_name}:conditions",
                description=f"{complex_conditions} complex boolean expressions",
                load_type=LoadType.EXTRANEOUS,
                weight=self.WEIGHTS["complex_condition"] * complex_conditions,
            ))

        # 5. Naming quality
        naming_score = self._assess_naming(node)
        if naming_score < 0.5:
            issues.append("Poor naming: variables/functions are unclear")
            suggestions.append("Use descriptive names that reveal intent")
            chunks.append(CognitiveLoadChunk(
                chunk_id=f"{func_name}:naming",
                description="Unclear variable/function naming",
                load_type=LoadType.EXTRANEOUS,
                weight=self.WEIGHTS["poor_naming"],
            ))

        # 6. Global state usage
        globals_used = self._find_globals(node)
        if globals_used > 0:
            issues.append(f"Uses {globals_used} global variables")
            suggestions.append("Pass state as parameters instead of using globals")
            chunks.append(CognitiveLoadChunk(
                chunk_id=f"{func_name}:globals",
                description=f"{globals_used} global variable references",
                load_type=LoadType.EXTRANEOUS,
                weight=self.WEIGHTS["global_state"] * globals_used,
            ))

        # 7. Side effects detection
        side_effects = self._find_side_effects(node)
        if side_effects > 0:
            issues.append(f"{side_effects} potential side effects detected")
            suggestions.append("Separate pure functions from side-effecting code")
            chunks.append(CognitiveLoadChunk(
                chunk_id=f"{func_name}:sideeffects",
                description=f"{side_effects} side-effecting operations",
                load_type=LoadType.EXTRANEOUS,
                weight=self.WEIGHTS["side_effect"] * side_effects,
            ))

        # Calculate loads
        extraneous = sum(c.weight for c in chunks if c.load_type == LoadType.EXTRANEOUS)
        intrinsic = self._estimate_intrinsic_load(node, line_count)
        total = extraneous + intrinsic

        # Normalize to working memory capacity
        normalized = min(10.0, total / self.WORKING_MEMORY_CAPACITY * 4)

        return FunctionScore(
            function_name=func_name,
            line_count=line_count,
            nesting_depth=max_depth,
            chunk_count=sum(c.weight for c in chunks),
            cognitive_load=round(normalized, 2),
            extraneous_load=round(extraneous, 2),
            intrinsic_load=round(intrinsic, 2),
            issues=issues,
            suggestions=suggestions,
        )

    def _calculate_nesting_depth(self, node: ast.AST) -> int:
        """Calculate maximum nesting depth of control structures."""
        max_depth = 0
        current_depth = 0

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.ExceptHandler)):
                # Count ancestors that are also control structures
                depth = 0
                parent = child
                while hasattr(parent, 'parent'):
                    parent = getattr(parent, 'parent', None)
                    if isinstance(parent, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                        depth += 1
                max_depth = max(max_depth, depth + 1)

        return max_depth

    def _find_complex_conditions(self, node: ast.AST) -> int:
        """Count complex boolean expressions."""
        count = 0
        for child in ast.walk(node):
            if isinstance(child, ast.BoolOp):
                if len(child.values) > 2:
                    count += 1
        return count

    def _assess_naming(self, node: ast.AST) -> float:
        """Score naming quality (0-1, 1 = excellent)."""
        names_to_check = []
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                names_to_check.append(child.id)
            elif isinstance(child, ast.FunctionDef):
                names_to_check.append(child.name)

        if not names_to_check:
            return 1.0

        scores = []
        for name in set(names_to_check):
            score = 1.0
            # Penalize single-letter names (except common iterators)
            if len(name) == 1 and name not in 'ijkxyz':
                score -= 0.5
            # Penalize abbreviations
            if re.match(r'^[a-z]+[0-9]+$', name):  # e.g., var1, tmp2
                score -= 0.3
            # Penalize unclear prefixes
            if name.startswith(('tmp', 'temp', 'foo', 'bar', 'baz')):
                score -= 0.4
            # Reward descriptive names
            if len(name) > 10 and '_' in name:
                score += 0.1
            scores.append(max(0.0, min(1.0, score)))

        return sum(scores) / len(scores) if scores else 1.0

    def _find_globals(self, node: ast.AST) -> int:
        """Count global variable references."""
        count = 0
        for child in ast.walk(node):
            if isinstance(child, ast.Global):
                count += len(child.names)
        return count

    def _find_side_effects(self, node: ast.AST) -> int:
        """Count potential side-effect operations."""
        count = 0
        for child in ast.walk(node):
            if isinstance(child, (ast.Assign, ast.AugAssign)):
                # Check if assigning to attribute (obj.attr = val)
                if isinstance(child.targets[0] if hasattr(child, 'targets') else child.target, ast.Attribute):
                    count += 1
        return count

    def _estimate_intrinsic_load(self, node: ast.FunctionDef, line_count: int) -> float:
        """Estimate essential complexity that cannot be reduced."""
        # Based on: algorithmic complexity, domain concepts, necessary conditionals
        base = line_count / 20  # ~20 lines = 1 unit of intrinsic load

        # Count necessary control structures (intrinsic)
        necessary_ifs = sum(1 for c in ast.walk(node) if isinstance(c, ast.If))
        necessary_loops = sum(1 for c in ast.walk(node) if isinstance(c, (ast.For, ast.While)))

        return base + necessary_ifs * 0.5 + necessary_loops * 0.5

    def _calculate_shallow_module_score(self, tree: ast.AST, func_scores: List[FunctionScore], total_lines: int) -> float:
        """Detect shallow modules: "interface is complex relative to functionality provided"."""
        # John Ousterhout's concept: shallow module = interface complexity / functionality is high
        exported_names = len(func_scores)
        total_functionality = total_lines
        if total_functionality == 0:
            return 0.0

        # High export count relative to implementation = shallow
        ratio = exported_names / (total_functionality / 50)  # normalize by ~50 lines per function
        return min(1.0, max(0.0, ratio - 0.5))

    def _estimate_onboarding(self, func_scores: List[FunctionScore], total_lines: int) -> float:
        """Estimate hours until new dev can contribute meaningfully."""
        if not func_scores:
            return total_lines / 200  # rough: 200 lines per hour

        avg_load = sum(f.cognitive_load for f in func_scores) / len(func_scores)
        # Higher cognitive load = longer onboarding
        base_hours = total_lines / 150  # base reading speed
        load_multiplier = 1 + (avg_load / 5)  # 0-10 scale
        return base_hours * load_multiplier

    def analyze_directory(self, dir_path: str, pattern: str = "**/*.py") -> List[ModuleScore]:
        """Analyze semua Python files dalam directory."""
        results = []
        for file in Path(dir_path).glob(pattern):
            if 'test' in file.name or 'venv' in str(file):
                continue
            try:
                result = self.analyze_file(file)
                results.append(result)
            except Exception:
                pass
        return results

    def get_project_summary(self) -> Dict[str, Any]:
        """Aggregate summary dari semua analyzed modules."""
        if not self._results:
            return {}

        total_funcs = sum(m.total_functions for m in self._results)
        total_lines = sum(m.total_lines for m in self._results)
        all_func_scores = []
        for m in self._results:
            all_func_scores.extend(m.function_scores)

        # Find worst offenders
        sorted_funcs = sorted(all_func_scores, key=lambda f: f.cognitive_load, reverse=True)
        worst = sorted_funcs[:10]

        # Category distribution
        load_distribution = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        for f in all_func_scores:
            if f.cognitive_load < 3:
                load_distribution["LOW"] += 1
            elif f.cognitive_load < 6:
                load_distribution["MEDIUM"] += 1
            elif f.cognitive_load < 9:
                load_distribution["HIGH"] += 1
            else:
                load_distribution["CRITICAL"] += 1

        return {
            "modules_analyzed": len(self._results),
            "total_functions": total_funcs,
            "total_lines": total_lines,
            "average_cognitive_load": round(sum(f.cognitive_load for f in all_func_scores) / len(all_func_scores), 2) if all_func_scores else 0,
            "max_cognitive_load": round(max((f.cognitive_load for f in all_func_scores), default=0), 2),
            "load_distribution": load_distribution,
            "worst_offenders": [
                {
                    "function": f.function_name,
                    "module": next((m.module_name for m in self._results if f in m.function_scores), "unknown"),
                    "load": f.cognitive_load,
                    "issues": f.issues,
                }
                for f in worst
            ],
            "project_onboarding_estimate_hours": round(sum(m.onboarding_estimate_hours for m in self._results), 1),
        }


# ═══════════════════════════════════════════════════════════════════════════
# 3. AGENT PROMPT OPTIMIZER — Cognitive Load untuk AI Agents
# ═══════════════════════════════════════════════════════════════════════════

class AgentPromptOptimizer:
    """Apply cognitive load principles ke agent prompts dan instructions.

    AI agents juga punya "working memory" (context window). Principles dari
    zakirullin/cognitive-load apply: reduce extraneous load, chunk information,
    use clear naming, avoid deep nesting dalam reasoning.
    """

    def __init__(self):
        self.chunk_size = 4  # ~4 chunks per prompt section

    def optimize_prompt(self, prompt: str) -> Dict[str, Any]:
        """Analyze dan optimize prompt untuk minimal cognitive load."""
        lines = prompt.splitlines()
        word_count = len(prompt.split())
        chunk_estimate = word_count / 20  # ~20 words = 1 conceptual chunk

        issues = []
        suggestions = []

        # 1. Too long
        if word_count > 500:
            issues.append(f"Prompt too long: {word_count} words (limit: 500)")
            suggestions.append("Split into multiple focused prompts")

        # 2. Too many conditions
        conditions = prompt.count("if ") + prompt.count("If ") + prompt.count("when ")
        if conditions > 5:
            issues.append(f"Too many conditional branches: {conditions}")
            suggestions.append("Use decision trees instead of nested conditionals")

        # 3. Unclear structure
        has_sections = any(line.startswith(("#", "##", "###", "- ", "1. ", "2. ")) for line in lines)
        if not has_sections:
            issues.append("No clear structure/sections")
            suggestions.append("Add headers and bullet points for scannability")

        # 4. Nested instructions
        nesting_depth = max((len(line) - len(line.lstrip())) for line in lines if line.strip()) if lines else 0
        if nesting_depth > 4:
            issues.append(f"Deep nesting in instructions: {nesting_depth} levels")
            suggestions.append("Flatten hierarchy, use sequential steps")

        # 5. Ambiguous terms
        ambiguous = ["it", "this", "that", "they", "them", "some", "thing", "stuff"]
        ambiguous_count = sum(prompt.lower().count(f" {w} ") for w in ambiguous)
        if ambiguous_count > 3:
            issues.append(f"Ambiguous references: {ambiguous_count}")
            suggestions.append("Use explicit noun references instead of pronouns")

        optimized = self._restructure_prompt(prompt, suggestions)

        return {
            "original_word_count": word_count,
            "chunk_estimate": round(chunk_estimate, 1),
            "issues": issues,
            "suggestions": suggestions,
            "cognitive_load_score": min(10, chunk_estimate / self.chunk_size * 2),
            "optimized_prompt": optimized,
        }

    def _restructure_prompt(self, prompt: str, suggestions: List[str]) -> str:
        """Apply structural improvements ke prompt."""
        lines = prompt.splitlines()
        result = []

        # Add clear header
        if not any(line.startswith("#") for line in lines[:3]):
            result.append("# Task")
            result.append("")

        for line in lines:
            # Flatten deep indentation
            if line.startswith("        "):
                line = line.lstrip()
            result.append(line)

        # Add summary if too long
        if len(prompt) > 1000 and "Split into multiple focused prompts" in suggestions:
            result.insert(0, "## Summary")
            result.insert(1, "[Key objective in one sentence]")
            result.insert(2, "")

        return "\n".join(result)

    def chunk_instructions(self, instructions: List[str]) -> List[List[str]]:
        """Chunk instructions into groups of ~4 (working memory limit)."""
        chunks = []
        for i in range(0, len(instructions), self.chunk_size):
            chunk = instructions[i:i + self.chunk_size]
            chunks.append(chunk)
        return chunks

    def create_scaffolded_prompt(self, task: str, prerequisites: List[str], steps: List[str]) -> str:
        """Create prompt dengan scaffolded structure — reduces cognitive load."""
        chunks = self.chunk_instructions(steps)

        lines = [
            f"# {task}",
            "",
            "## Prerequisites (complete these first)",
        ]
        for p in prerequisites:
            lines.append(f"- [ ] {p}")
        lines.append("")
        lines.append("## Steps")

        for i, chunk in enumerate(chunks, 1):
            lines.append(f"")
            lines.append(f"### Phase {i}")
            for step in chunk:
                lines.append(f"{i}. {step}")

        lines.extend([
            "",
            "## Completion Criteria",
            "- [ ] All phases completed",
            "- [ ] Output verified",
            "- [ ] Edge cases considered",
        ])

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# 4. REFACTORING SUGGESTION ENGINE
# ═══════════════════════════════════════════════════════════════════════════

class RefactoringEngine:
    """Generate concrete refactoring suggestions berdasarkan cognitive load analysis."""

    def __init__(self, scorer: CodeComplexityScorer):
        self.scorer = scorer

    def suggest_for_function(self, func_score: FunctionScore, source_code: str) -> List[Dict[str, Any]]:
        """Generate specific refactoring suggestions."""
        suggestions = []

        for issue in func_score.issues:
            if "Deep nesting" in issue:
                suggestions.append({
                    "type": "guard_clause",
                    "description": "Replace nested ifs with early returns",
                    "before": "if condition:\n    if other:\n        do_something()",
                    "after": "if not condition:\n    return\nif not other:\n    return\ndo_something()",
                    "effort": "low",
                    "impact": "high",
                })

            if "Long function" in issue:
                suggestions.append({
                    "type": "extract_method",
                    "description": f"Extract parts of {func_score.function_name} into helpers",
                    "before": f"def {func_score.function_name}():\n    # {func_score.line_count} lines...",
                    "after": "def helper_a(): ...\ndef helper_b(): ...\ndef main(): helper_a(); helper_b()",
                    "effort": "medium",
                    "impact": "high",
                })

            if "Many parameters" in issue:
                suggestions.append({
                    "type": "introduce_parameter_object",
                    "description": "Group parameters into a config dataclass",
                    "before": "def func(a, b, c, d, e, f):",
                    "after": "@dataclass\nclass Config:\n    a, b, c, d, e, f\ndef func(cfg: Config):",
                    "effort": "low",
                    "impact": "medium",
                })

            if "Complex conditions" in issue:
                suggestions.append({
                    "type": "extract_condition",
                    "description": "Name intermediate boolean expressions",
                    "before": "if a and b and c and d:",
                    "after": "is_valid = a and b\nhas_permission = c and d\nif is_valid and has_permission:",
                    "effort": "low",
                    "impact": "medium",
                })

            if "Poor naming" in issue:
                suggestions.append({
                    "type": "rename",
                    "description": "Use intention-revealing names",
                    "before": "def process(data):\n    tmp = data[0]\n    res = calculate(tmp)",
                    "after": "def calculate_monthly_revenue(sales_records):\n    first_record = sales_records[0]\n    revenue = compute_revenue(first_record)",
                    "effort": "low",
                    "impact": "medium",
                })

            if "global" in issue.lower():
                suggestions.append({
                    "type": "eliminate_globals",
                    "description": "Pass state explicitly as parameters",
                    "before": "global_state = {}\ndef func():\n    global_state['x'] = 1",
                    "after": "def func(state: dict):\n    state['x'] = 1\n    return state",
                    "effort": "medium",
                    "impact": "high",
                })

        return suggestions

    def suggest_for_module(self, module_score: ModuleScore) -> List[Dict[str, Any]]:
        """Generate module-level refactoring suggestions."""
        suggestions = []

        if module_score.shallow_module_score > 0.5:
            suggestions.append({
                "type": "deepen_module",
                "description": f"Module {module_score.module_name} is shallow — increase functionality or reduce exports",
                "detail": "A shallow module has a complex interface but little functionality. Consider merging with related modules or increasing internal complexity hiding.",
                "effort": "medium",
                "impact": "high",
                "reference": "John Ousterhout: 'A Philosophy of Software Design'",
            })

        high_load_funcs = [f for f in module_score.function_scores if f.cognitive_load > 7]
        if len(high_load_funcs) > len(module_score.function_scores) * 0.3:
            suggestions.append({
                "type": "split_module",
                "description": f"{len(high_load_funcs)}/{len(module_score.function_scores)} functions have high cognitive load — consider splitting module",
                "effort": "high",
                "impact": "high",
            })

        return suggestions


# ═══════════════════════════════════════════════════════════════════════════
# 5. COGNITIVE LOAD DASHBOARD — Real-Time Metrics
# ═══════════════════════════════════════════════════════════════════════════

class CognitiveLoadDashboard:
    """Dashboard untuk track cognitive load metrics across codebase."""

    def __init__(self):
        self.scorer = CodeComplexityScorer()
        self.optimizer = AgentPromptOptimizer()
        self.refactor = RefactoringEngine(self.scorer)
        self._history: List[Dict[str, Any]] = []

    async def analyze_project(self, project_path: str) -> Dict[str, Any]:
        """Full project analysis."""
        modules = self.scorer.analyze_directory(project_path)
        summary = self.scorer.get_project_summary()

        # Add refactoring suggestions for worst offenders
        all_suggestions = []
        for m in modules:
            mod_suggestions = self.refactor.suggest_for_module(m)
            all_suggestions.extend(mod_suggestions)
            for f in m.function_scores:
                if f.cognitive_load > 5:
                    # We would need source code for detailed suggestions
                    pass

        result = {
            "timestamp": time.time(),
            "project_path": project_path,
            "summary": summary,
            "modules": [
                {
                    "name": m.module_name,
                    "total_lines": m.total_lines,
                    "functions": m.total_functions,
                    "avg_load": m.average_load,
                    "max_load": m.max_load,
                    "shallow_score": m.shallow_module_score,
                    "onboarding_hours": m.onboarding_estimate_hours,
                    "function_scores": [
                        {
                            "name": f.function_name,
                            "lines": f.line_count,
                            "nesting": f.nesting_depth,
                            "load": f.cognitive_load,
                            "extraneous": f.extraneous_load,
                            "intrinsic": f.intrinsic_load,
                            "issues": f.issues,
                            "suggestions": f.suggestions,
                        }
                        for f in m.function_scores
                    ],
                }
                for m in modules
            ],
            "refactoring_opportunities": len(all_suggestions),
            "module_suggestions": all_suggestions,
        }

        self._history.append(result)
        return result

    async def optimize_agent_prompt(self, prompt: str) -> Dict[str, Any]:
        """Optimize AI agent prompt untuk minimal cognitive load."""
        return self.optimizer.optimize_prompt(prompt)

    async def generate_onboarding_guide(self, project_path: str) -> Dict[str, Any]:
        """Generate onboarding guide berdasarkan cognitive load analysis."""
        modules = self.scorer.analyze_directory(project_path)

        # Sort by onboarding time (easiest first)
        sorted_modules = sorted(modules, key=lambda m: m.onboarding_estimate_hours)

        guide = {
            "estimated_total_hours": round(sum(m.onboarding_estimate_hours for m in modules), 1),
            "recommended_order": [
                {
                    "module": m.module_name,
                    "estimated_hours": m.onboarding_estimate_hours,
                    "difficulty": "easy" if m.average_load < 3 else "medium" if m.average_load < 6 else "hard",
                    "prerequisites": [],
                }
                for m in sorted_modules[:5]
            ],
            "avoid_initially": [
                m.module_name for m in sorted(modules, key=lambda m: m.average_load, reverse=True)[:3]
            ],
            "tips": [
                "Start with modules that have low cognitive load (< 3)",
                "Read function signatures before implementation details",
                "Use IDE navigation to trace call hierarchies",
                "Focus on one module at a time — respect working memory limits",
            ],
        }
        return guide

    def get_health_trend(self) -> Dict[str, Any]:
        """Track cognitive load trends over time."""
        if len(self._history) < 2:
            return {"trend": "insufficient_data"}

        recent = self._history[-10:]
        loads = [r["summary"]["average_cognitive_load"] for r in recent if "summary" in r]
        if not loads:
            return {"trend": "no_data"}

        return {
            "trend": "improving" if loads[-1] < loads[0] else "degrading" if loads[-1] > loads[0] else "stable",
            "current_avg": round(loads[-1], 2),
            "initial_avg": round(loads[0], 2),
            "change_pct": round((loads[-1] - loads[0]) / loads[0] * 100, 1) if loads[0] > 0 else 0,
            "datapoints": len(loads),
        }


# ═══════════════════════════════════════════════════════════════════════════
# 6. MAGNATRIX INTEGRATION — Adapter ke IDE & Agent Layers
# ═══════════════════════════════════════════════════════════════════════════

class CognitiveLoadAdapter:
    """Adapter menghubungkan Cognitive Load Analyzer ke MAGNATRIX layers."""

    def __init__(self, dashboard: CognitiveLoadDashboard):
        self.dashboard = dashboard

    async def analyze_magnatrix_codebase(self) -> Dict[str, Any]:
        """Analyze MAGNATRIX codebase sendiri untuk self-improvement."""
        # In production: analyze /mnt/agents/MAGNATRIX-OS
        return await self.dashboard.analyze_project("/mnt/agents/MAGNATRIX-OS")

    async def optimize_agent_instructions(self, agent_system_prompt: str) -> str:
        """Optimize system prompt untuk MAGNATRIX agents."""
        result = await self.dashboard.optimize_agent_prompt(agent_system_prompt)
        return result.get("optimized_prompt", agent_system_prompt)

    async def generate_ide_recommendations(self, file_path: str) -> List[Dict[str, Any]]:
        """Generate real-time IDE recommendations saat coding."""
        try:
            score = self.dashboard.scorer.analyze_file(file_path)
            suggestions = []
            for f in score.function_scores:
                if f.cognitive_load > 5:
                    suggestions.append({
                        "function": f.function_name,
                        "severity": "warning" if f.cognitive_load < 8 else "error",
                        "message": f"Cognitive load: {f.cognitive_load}/10 — {', '.join(f.issues[:2])}",
                        "quick_fix": f.suggestions[0] if f.suggestions else "Consider simplifying",
                    })
            return suggestions
        except Exception:
            return []


# ═══════════════════════════════════════════════════════════════════════════
# Standalone Demo
# ═══════════════════════════════════════════════════════════════════════════

async def demo_cognitive_load():
    print("=" * 70)
    print("MAGNATRIX — Native Cognitive Load Analyzer Demo")
    print("=" * 70)

    dashboard = CognitiveLoadDashboard()

    # 1. Analyze sample code
    sample_code = textwrap.dedent("""\
        def process_user_request(data, config, db, logger, cache, validator):
            global state
            result = []
            if data:
                if config:
                    if db.is_connected() and cache.has(data['id']) and validator.validate(data):
                        if data['type'] == 'A':
                            tmp = db.query(data)
                            if tmp:
                                for item in tmp:
                                    if item['status'] == 'active':
                                        r = process_item(item, config, db, logger)
                                        result.append(r)
                                    else:
                                        logger.log("skipped")
                            else:
                                logger.log("no data")
                        elif data['type'] == 'B':
                            state['processed'] += 1
                            cache.put(data['id'], result)
                            logger.log("done")
                        else:
                            logger.log("unknown type")
                    else:
                        logger.log("validation failed")
                else:
                    logger.log("no config")
            else:
                logger.log("no data")
            return result

        def process_item(item, cfg, database, log):
            x = item['value']
            y = cfg['multiplier']
            z = database.fetch(x)
            return x * y + z
    """)

    print("\n[1] Analyzing sample code...")
    # Write temp file
    tmp_path = "/tmp/magnatrix_cognitive_demo.py"
    Path(tmp_path).write_text(sample_code, encoding="utf-8")
    score = dashboard.scorer.analyze_file(tmp_path)

    print(f"    Module: {score.module_name}")
    print(f"    Functions: {score.total_functions}")
    print(f"    Total lines: {score.total_lines}")
    print(f"    Average load: {score.average_load}")
    print(f"    Max load: {score.max_load}")
    print(f"    Shallow module score: {score.shallow_module_score:.2f}")
    print(f"    Onboarding estimate: {score.onboarding_estimate_hours} hours")

    for f in score.function_scores:
        print(f"\n    Function: {f.function_name}")
        print(f"      Lines: {f.line_count}, Nesting: {f.nesting_depth}")
        print(f"      Cognitive load: {f.cognitive_load}/10 (extraneous: {f.extraneous_load}, intrinsic: {f.intrinsic_load})")
        print(f"      Issues: {f.issues}")
        print(f"      Suggestions: {f.suggestions}")

    # 2. Prompt optimization
    print("\n[2] Agent Prompt Optimization:")
    long_prompt = """
    You are an AI assistant. If the user asks about weather, check the API. If they ask about news, search the web. If they ask about stocks, query the financial database. If they ask about code, analyze their repository. If they ask about translation, use the translation engine. If they ask about images, generate one. If they ask about audio, transcribe it. If the input is unclear, ask for clarification. If the input is a greeting, respond warmly. If the input is a command, execute it. If the input is a question, answer it. If the input is a statement, acknowledge it.
    """""

    opt = await dashboard.optimize_agent_prompt(long_prompt)
    print(f"    Original words: {opt['original_word_count']}")
    print(f"    Chunk estimate: {opt['chunk_estimate']}")
    print(f"    Cognitive load score: {opt['cognitive_load_score']:.1f}/10")
    print(f"    Issues: {opt['issues']}")

    # 3. Scaffolded prompt creation
    print("\n[3] Scaffolded Prompt Example:")
    scaffolded = dashboard.optimizer.create_scaffolded_prompt(
        task="Implement trading strategy backtester",
        prerequisites=["Understand strategy parameters", "Load historical data"],
        steps=[
            "Define entry/exit conditions",
            "Implement signal generator",
            "Build portfolio tracker",
            "Run backtest simulation",
            "Calculate performance metrics",
            "Generate report",
        ],
    )
    print(f"    Phases: {scaffolded.count('Phase')}")
    print(f"    Steps chunked by working memory limit (4 per phase)")

    # 4. Project analysis stub
    print("\n[4] Project Summary:")
    summary = dashboard.scorer.get_project_summary()
    if summary:
        print(f"    {json.dumps(summary, indent=2)}")
    else:
        print(f"    [single module analyzed]")

    # 5. Health trend
    print("\n[5] Health Trend:")
    trend = dashboard.get_health_trend()
    print(f"    {json.dumps(trend, indent=2)}")

    print("\n" + "=" * 70)
    print("Demo selesai — Cognitive Load Analyzer 100% native di MAGNATRIX")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo_cognitive_load())
