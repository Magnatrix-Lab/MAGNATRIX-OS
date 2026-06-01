"""Code Synthesis Engine — Structured code generation, planning, test-driven synthesis, review.

Modul ini menyediakan:
- CodePlanner untuk decompose requirements into implementation steps
- CodeGenerator untuk generate code dengan templates dan patterns
- TestGenerator untuk generate unit tests automatically
- CodeReviewer untuk static analysis, style checking, linting
- SynthesisPipeline untuk end-to-end code generation workflow
"""

from __future__ import annotations

import json
import time
import uuid
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class CodeLanguage(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    RUST = "rust"
    GO = "go"
    CPP = "cpp"
    JAVA = "java"
    BASH = "bash"
    SQL = "sql"


class SynthesisStage(Enum):
    PLANNING = auto()
    GENERATING = auto()
    TESTING = auto()
    REVIEWING = auto()
    COMPLETED = auto()
    FAILED = auto()


@dataclass
class CodeRequirement:
    """Parsed requirement for code generation."""
    requirement_id: str
    description: str
    language: CodeLanguage
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    examples: List[Tuple[str, str]] = field(default_factory=list)  # (input, expected_output)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ImplementationStep:
    """Single step in implementation plan."""
    step_id: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    estimated_tokens: int = 0
    status: str = "pending"  # pending, done, failed


@dataclass
class CodeArtifact:
    """Generated code with metadata."""
    artifact_id: str
    language: CodeLanguage
    filename: str
    content: str
    token_count: int = 0
    steps: List[str] = field(default_factory=list)
    tests: List[str] = field(default_factory=list)
    reviews: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def __post_init__(self):
        if self.token_count == 0:
            self.token_count = max(1, len(self.content) // 4)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "language": self.language.value,
            "filename": self.filename,
            "token_count": self.token_count,
            "steps": self.steps,
            "tests_count": len(self.tests),
            "reviews_count": len(self.reviews),
        }


@dataclass
class TestCase:
    """Unit test case."""
    test_id: str
    name: str
    input_data: str
    expected_output: str
    test_code: str = ""
    passed: Optional[bool] = None


class CodePlanner:
    """Decompose requirements into implementation steps."""

    def __init__(self):
        self._patterns: Dict[str, List[str]] = {
            "function": ["Define function signature", "Implement core logic", "Add input validation", "Add error handling"],
            "class": ["Define class structure", "Implement constructor", "Add methods", "Add property accessors"],
            "api": ["Define endpoints", "Implement request handlers", "Add validation", "Add error responses"],
            "algorithm": ["Understand problem", "Design algorithm", "Implement core loop", "Add edge cases"],
        }

    def plan(self, requirement: CodeRequirement) -> List[ImplementationStep]:
        desc = requirement.description.lower()
        # Select pattern
        pattern = "function"
        if "class" in desc or "object" in desc:
            pattern = "class"
        elif "api" in desc or "endpoint" in desc or "server" in desc:
            pattern = "api"
        elif "algorithm" in desc or "sort" in desc or "search" in desc:
            pattern = "algorithm"

        steps = []
        for i, s in enumerate(self._patterns.get(pattern, self._patterns["function"])):
            steps.append(ImplementationStep(
                step_id=f"step-{i}",
                description=s,
                dependencies=[f"step-{i-1}"] if i > 0 else [],
                estimated_tokens=200
            ))
        # Add constraint steps
        for c in requirement.constraints:
            steps.append(ImplementationStep(
                step_id=f"step-constraint-{len(steps)}",
                description=f"Apply constraint: {c}",
                dependencies=[steps[-1].step_id] if steps else [],
                estimated_tokens=100
            ))
        return steps


class CodeGenerator:
    """Generate code from requirements and plans."""

    def __init__(self):
        self._templates: Dict[CodeLanguage, Dict[str, str]] = {
            CodeLanguage.PYTHON: {
                "function": "def {name}({params}):\n    {body}\n    return result\n",
                "class": "class {name}:\n    def __init__(self, {params}):\n        {init_body}\n",
                "test": "def test_{name}():\n    assert {call} == {expected}\n",
            },
            CodeLanguage.JAVASCRIPT: {
                "function": "function {name}({params}) {{\n    {body}\n    return result;\n}}\n",
                "class": "class {name} {{\n    constructor({params}) {{\n        {init_body}\n    }}\n}}\n",
                "test": "test('{name}', () => {{\n    expect({call}).toBe({expected});\n}});\n",
            },
        }

    def generate(self, requirement: CodeRequirement, steps: List[ImplementationStep],
                 generator_fn: Optional[Callable[[CodeRequirement, List[ImplementationStep]], str]] = None) -> CodeArtifact:
        generator_fn = generator_fn or self._default_generator
        content = generator_fn(requirement, steps)
        return CodeArtifact(
            artifact_id=str(uuid.uuid4())[:12],
            language=requirement.language,
            filename=f"generated_{requirement.requirement_id}.{requirement.language.value}",
            content=content,
            steps=[s.step_id for s in steps]
        )

    def _default_generator(self, req: CodeRequirement, steps: List[ImplementationStep]) -> str:
        # Simple simulation: generate a function with comments
        lines = [f"# Generated {req.language.value} code for: {req.description}", ""]
        lines.append(f"def {req.requirement_id}({', '.join(req.inputs)}):")
        lines.append(f'    """')
        lines.append(f'    {req.description}')
        for c in req.constraints:
            lines.append(f'    Constraint: {c}')
        lines.append(f'    """')
        for s in steps:
            lines.append(f"    # {s.description}")
        lines.append(f"    # TODO: Implement core logic")
        lines.append(f"    result = None  # Placeholder")
        lines.append(f"    return result")
        lines.append("")
        if req.examples:
            lines.append("# Examples:")
            for inp, out in req.examples:
                lines.append(f"# {req.requirement_id}({inp}) -> {out}")
        return "\n".join(lines)

    def apply_template(self, language: CodeLanguage, template_name: str, **kwargs) -> str:
        tmpl = self._templates.get(language, {}).get(template_name, "")
        return tmpl.format(**kwargs)


class TestGenerator:
    """Generate unit tests from requirements and code."""

    def __init__(self):
        self._test_frameworks: Dict[CodeLanguage, str] = {
            CodeLanguage.PYTHON: "pytest",
            CodeLanguage.JAVASCRIPT: "jest",
            CodeLanguage.TYPESCRIPT: "jest",
            CodeLanguage.RUST: "cargo test",
            CodeLanguage.GO: "go test",
            CodeLanguage.JAVA: "junit",
        }

    def generate_tests(self, requirement: CodeRequirement, artifact: CodeArtifact) -> List[TestCase]:
        tests = []
        for i, (inp, expected) in enumerate(requirement.examples):
            tc = TestCase(
                test_id=f"test-{i}",
                name=f"test_{requirement.requirement_id}_{i}",
                input_data=inp,
                expected_output=expected,
                test_code=self._generate_test_code(requirement, artifact, inp, expected, i)
            )
            tests.append(tc)
        return tests

    def _generate_test_code(self, req: CodeRequirement, art: CodeArtifact, inp: str, expected: str, idx: int) -> str:
        if req.language == CodeLanguage.PYTHON:
            return f"def test_{req.requirement_id}_{idx}():\n    assert {req.requirement_id}({inp}) == {expected}\n"
        elif req.language in (CodeLanguage.JAVASCRIPT, CodeLanguage.TYPESCRIPT):
            return f"test('{req.requirement_id} {idx}', () => {{\n    expect({req.requirement_id}({inp})).toBe({expected});\n}});\n"
        else:
            return f"// Test {idx}: {req.requirement_id}({inp}) -> {expected}"

    def run_tests(self, tests: List[TestCase], runner_fn: Optional[Callable[[TestCase], bool]] = None) -> List[TestCase]:
        runner_fn = runner_fn or self._default_runner
        for t in tests:
            t.passed = runner_fn(t)
        return tests

    def _default_runner(self, tc: TestCase) -> bool:
        # Simulated: tests with 'valid' examples pass
        return "error" not in tc.input_data.lower() and "invalid" not in tc.input_data.lower()


class CodeReviewer:
    """Static analysis and review of generated code."""

    def __init__(self):
        self._rules: List[Tuple[str, Callable[[str], bool], str]] = []
        self._register_default_rules()

    def _register_default_rules(self):
        self._rules.append(("no-bare-except", lambda c: "except:" not in c, "Avoid bare except clauses"))
        self._rules.append(("no-print", lambda c: "print(" not in c, "Remove debug print statements"))
        self._rules.append(("has-docstring", lambda c: '"""' in c or "'''" in c, "Add docstrings"))
        self._rules.append(("line-length", lambda c: all(len(l) <= 120 for l in c.split("\n")), "Keep lines under 120 chars"))
        self._rules.append(("imports-top", lambda c: True, "Imports should be at top"))

    def review(self, artifact: CodeArtifact) -> List[Dict[str, Any]]:
        issues = []
        for rule_id, checker, message in self._rules:
            passed = checker(artifact.content)
            issues.append({
                "rule": rule_id,
                "passed": passed,
                "message": message if not passed else "",
                "severity": "warning" if not passed else "info"
            })
        return issues

    def score(self, artifact: CodeArtifact) -> float:
        issues = self.review(artifact)
        passed = sum(1 for i in issues if i["passed"])
        return passed / max(len(issues), 1)

    def suggest_fixes(self, artifact: CodeArtifact) -> List[str]:
        issues = self.review(artifact)
        return [f"[{i['rule']}] {i['message']}" for i in issues if not i["passed"]]


class SynthesisPipeline:
    """End-to-end code synthesis: plan → generate → test → review."""

    def __init__(self):
        self.planner = CodePlanner()
        self.generator = CodeGenerator()
        self.tester = TestGenerator()
        self.reviewer = CodeReviewer()
        self._runs: List[Dict[str, Any]] = []
        self._status = SynthesisStage.PLANNING

    def synthesize(self, requirement: CodeRequirement) -> Dict[str, Any]:
        self._status = SynthesisStage.PLANNING
        # Plan
        steps = self.planner.plan(requirement)
        # Generate
        self._status = SynthesisStage.GENERATING
        artifact = self.generator.generate(requirement, steps)
        # Test
        self._status = SynthesisStage.TESTING
        tests = self.tester.generate_tests(requirement, artifact)
        tests = self.tester.run_tests(tests)
        artifact.tests = [t.test_code for t in tests]
        # Review
        self._status = SynthesisStage.REVIEWING
        reviews = self.reviewer.review(artifact)
        artifact.reviews = reviews
        score = self.reviewer.score(artifact)
        # Complete
        self._status = SynthesisStage.COMPLETED if score > 0.5 else SynthesisStage.FAILED
        run = {
            "run_id": str(uuid.uuid4())[:12],
            "requirement": requirement.requirement_id,
            "artifact": artifact.to_dict(),
            "steps": len(steps),
            "tests": len(tests),
            "passed_tests": sum(1 for t in tests if t.passed),
            "review_score": round(score, 2),
            "issues": [i for i in reviews if not i["passed"]],
            "status": self._status.name,
        }
        self._runs.append(run)
        return run

    def get_status(self) -> SynthesisStage:
        return self._status

    def get_runs(self) -> List[Dict[str, Any]]:
        return self._runs

    def export_report(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "runs": self._runs,
                "total": len(self._runs),
                "avg_score": sum(r["review_score"] for r in self._runs) / max(len(self._runs), 1),
            }, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("CODE SYNTHESIS ENGINE DEMO")
    print("=" * 70)

    # 1. Requirement
    print("\n[1] Code Requirements")
    req = CodeRequirement(
        requirement_id="calc-stats",
        description="Calculate mean, median, and standard deviation of a list of numbers",
        language=CodeLanguage.PYTHON,
        inputs=["numbers"],
        outputs=["mean", "median", "std_dev"],
        constraints=["Handle empty list gracefully", "O(n) time complexity", "No external libraries"],
        examples=[("[1, 2, 3, 4, 5]", "{'mean': 3.0, 'median': 3, 'std_dev': 1.41}"), ("[]", "None")]
    )
    print(f"  Req: {req.description}")
    print(f"  Language: {req.language.value}")
    print(f"  Constraints: {req.constraints}")
    print(f"  Examples: {len(req.examples)}")

    # 2. Planning
    print("\n[2] Planning")
    planner = CodePlanner()
    steps = planner.plan(req)
    for s in steps:
        print(f"  {s.step_id}: {s.description}")

    # 3. Generation
    print("\n[3] Code Generation")
    generator = CodeGenerator()
    artifact = generator.generate(req, steps)
    print(f"  Artifact: {artifact.artifact_id}")
    print(f"  File: {artifact.filename}")
    print(f"  Tokens: {artifact.token_count}")
    print(f"  Content preview:")
    for line in artifact.content.split("\n")[:10]:
        print(f"    {line}")

    # 4. Template
    print("\n[4] Template Generation")
    tmpl = generator.apply_template(CodeLanguage.PYTHON, "function", name="hello", params="name", body="print(f'Hello, {name}')", result="None")
    print(f"  Template result:\n{tmpl}")

    # 5. Test Generation
    print("\n[5] Test Generation")
    tester = TestGenerator()
    tests = tester.generate_tests(req, artifact)
    for t in tests:
        print(f"  {t.name}: input={t.input_data[:30]}... expected={t.expected_output[:30]}...")
    tests = tester.run_tests(tests)
    passed = sum(1 for t in tests if t.passed)
    print(f"  Passed: {passed}/{len(tests)}")

    # 6. Review
    print("\n[6] Code Review")
    reviewer = CodeReviewer()
    issues = reviewer.review(artifact)
    for i in issues:
        status = "PASS" if i["passed"] else "FAIL"
        print(f"  [{status}] {i['rule']}: {i['message'] or 'OK'}")
    score = reviewer.score(artifact)
    print(f"  Review score: {score:.0%}")
    fixes = reviewer.suggest_fixes(artifact)
    if fixes:
        print(f"  Suggested fixes: {len(fixes)}")
        for f in fixes:
            print(f"    {f}")

    # 7. Full pipeline
    print("\n[7] Full Synthesis Pipeline")
    pipeline = SynthesisPipeline()
    result = pipeline.synthesize(req)
    print(f"  Run: {result['run_id']}")
    print(f"  Status: {result['status']}")
    print(f"  Steps: {result['steps']}")
    print(f"  Tests: {result['passed_tests']}/{result['tests']}")
    print(f"  Review score: {result['review_score']}")
    print(f"  Issues: {len(result['issues'])}")

    # Multiple runs
    req2 = CodeRequirement(
        requirement_id="sort-list",
        description="Implement quicksort algorithm",
        language=CodeLanguage.PYTHON,
        inputs=["arr"],
        outputs=["sorted_arr"],
        constraints=["In-place", "O(n log n) average"],
        examples=[("[3,1,4,1,5]", "[1,1,3,4,5]"), ("[]", "[]")]
    )
    pipeline.synthesize(req2)
    print(f"\n[8] Pipeline Stats: {len(pipeline.get_runs())} runs, avg score={sum(r['review_score'] for r in pipeline.get_runs())/len(pipeline.get_runs()):.2f}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
