"""
ai/deep_research_native.py — MAGNATRIX-OS
Deep Research Engine (pure Python, zero external AI frameworks)

Inspired by dzhng/deep-research pattern:
- Recursive exploration with breadth (parallel queries) and depth (recursion levels)
- Concurrent query processing via asyncio
- Learning deduplication across iterations
- Direction pruning based on relevance score
- Markdown report generation with hierarchical structure and citations

Usage:
    from ai.deep_research_native import DeepResearch
    dr = DeepResearch(breadth=5, depth=3)
    report = await dr.run("Your research topic here")
    print(report)

No LangChain, no LlamaIndex, no OpenAI imports. Pure stdlib + asyncio.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import random
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set, Tuple


# ───────────────────────────────────────────────
# Data Models
# ───────────────────────────────────────────────

@dataclass
class Source:
    """A single source reference with title, URL, and relevance score."""
    title: str
    url: str
    snippet: str = ""
    relevance_score: float = 0.0
    source_id: str = field(default_factory=lambda: f"src_{uuid.uuid4().hex[:8]}")

    def to_citation(self) -> str:
        return f"[{self.source_id}] {self.title} — {self.url}"


@dataclass
class Learning:
    """A distilled learning extracted from search results."""
    text: str
    sources: List[Source] = field(default_factory=list)
    learning_id: str = field(default_factory=lambda: f"l_{uuid.uuid4().hex[:8]}")
    _hash: str = field(default="", repr=False)

    def __post_init__(self):
        if not self._hash:
            self._hash = hashlib.sha256(self.text.encode()).hexdigest()[:16]

    def is_duplicate_of(self, other: Learning) -> bool:
        """Check if two learnings are semantically duplicates."""
        return self._hash == other._hash or self._similarity(other) > 0.85

    def _similarity(self, other: Learning) -> float:
        """Simple Jaccard-like similarity on word sets."""
        words_a = set(self.text.lower().split())
        words_b = set(other.text.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)


@dataclass
class Direction:
    """A follow-up research direction generated from learnings."""
    query: str
    rationale: str
    relevance_score: float = 0.0
    direction_id: str = field(default_factory=lambda: f"d_{uuid.uuid4().hex[:8]}")
    parent_learning_ids: List[str] = field(default_factory=list)


@dataclass
class ResearchResult:
    """Result of a single query search."""
    query: str
    sources: List[Source] = field(default_factory=list)
    learnings: List[Learning] = field(default_factory=list)
    directions: List[Direction] = field(default_factory=list)
    duration_ms: float = 0.0


@dataclass
class ResearchIteration:
    """One level of the research tree."""
    depth_level: int
    queries: List[str] = field(default_factory=list)
    results: List[ResearchResult] = field(default_factory=list)
    learnings: List[Learning] = field(default_factory=list)
    directions: List[Direction] = field(default_factory=list)
    iteration_id: str = field(default_factory=lambda: f"iter_{uuid.uuid4().hex[:8]}")


@dataclass
class ResearchState:
    """Global state tracking across all iterations."""
    goal: str = ""
    all_learnings: List[Learning] = field(default_factory=list)
    all_sources: List[Source] = field(default_factory=list)
    all_directions: List[Direction] = field(default_factory=list)
    visited_queries: Set[str] = field(default_factory=set)
    learning_hashes: Set[str] = field(default_factory=set)
    iteration_count: int = 0
    start_time: float = field(default_factory=time.time)

    def add_learnings(self, learnings: List[Learning]) -> List[Learning]:
        """Add learnings, deduplicating against existing ones."""
        new_learnings = []
        for learning in learnings:
            if learning._hash not in self.learning_hashes:
                # Check for near-duplicates
                is_duplicate = any(learning.is_duplicate_of(existing) for existing in self.all_learnings)
                if not is_duplicate:
                    self.learning_hashes.add(learning._hash)
                    self.all_learnings.append(learning)
                    new_learnings.append(learning)
        return new_learnings

    def add_sources(self, sources: List[Source]) -> None:
        """Add sources, deduplicating by URL."""
        existing_urls = {s.url for s in self.all_sources}
        for source in sources:
            if source.url not in existing_urls:
                self.all_sources.append(source)
                existing_urls.add(source.url)

    def prune_directions(self, directions: List[Direction], max_directions: int) -> List[Direction]:
        """Prune directions based on relevance score, keeping top N."""
        sorted_dirs = sorted(directions, key=lambda d: d.relevance_score, reverse=True)
        return sorted_dirs[:max_directions]


# ───────────────────────────────────────────────
# Query Generator
# ───────────────────────────────────────────────

class QueryGenerator:
    """Generates targeted search queries from research goals and context."""

    def __init__(self, breadth: int = 5):
        self.breadth = max(3, min(10, breadth))
        self._query_history: Set[str] = set()

    async def generate(
        self,
        goal: str,
        context: Optional[List[Learning]] = None,
        directions: Optional[List[Direction]] = None,
    ) -> List[str]:
        """Generate `breadth` unique search queries for the given goal."""
        queries: List[str] = []
        base_queries = self._generate_base_queries(goal)
        queries.extend(base_queries)

        if context:
            context_queries = self._generate_context_queries(goal, context)
            queries.extend(context_queries)

        if directions:
            direction_queries = [d.query for d in directions if d.query not in self._query_history]
            queries.extend(direction_queries)

        # Deduplicate and limit to breadth
        unique_queries = []
        for q in queries:
            normalized = q.lower().strip()
            if normalized not in self._query_history and normalized not in {uq.lower().strip() for uq in unique_queries}:
                unique_queries.append(q)
                self._query_history.add(normalized)
            if len(unique_queries) >= self.breadth:
                break

        return unique_queries[: self.breadth]

    def _generate_base_queries(self, goal: str) -> List[str]:
        """Generate base queries from the research goal itself."""
        # In a real implementation, this would call an LLM
        # Here we simulate by creating variations of the goal
        queries = [goal]

        # Add variations
        variations = [
            f"{goal} overview and fundamentals",
            f"{goal} latest developments 2024 2025",
            f"{goal} key challenges and problems",
            f"{goal} expert analysis and insights",
            f"{goal} comparison and alternatives",
            f"{goal} implementation guide tutorial",
            f"{goal} case studies and real world examples",
            f"{goal} future trends and predictions",
            f"{goal} technical deep dive architecture",
            f"{goal} best practices and recommendations",
        ]
        queries.extend(variations)
        return queries

    def _generate_context_queries(self, goal: str, context: List[Learning]) -> List[str]:
        """Generate queries based on previous learnings."""
        queries = []
        for learning in context[-3:]:  # Use last 3 learnings for context
            # Extract key terms and create follow-up queries
            text = learning.text[:100]  # Truncate for query generation
            queries.append(f"{goal} {text}")
            queries.append(f"{text} detailed explanation")
        return queries


# ───────────────────────────────────────────────
# Result Processor
# ───────────────────────────────────────────────

class ResultProcessor:
    """Extracts key learnings, sources, and follow-up directions from search results."""

    def __init__(self, max_learnings_per_result: int = 3, max_directions_per_result: int = 2):
        self.max_learnings = max_learnings_per_result
        self.max_directions = max_directions_per_result

    async def process(self, query: str, raw_results: List[Dict[str, Any]]) -> ResearchResult:
        """Process raw search results into structured learnings and directions."""
        start_time = time.time()

        sources = self._extract_sources(raw_results)
        learnings = self._extract_learnings(query, raw_results, sources)
        directions = self._extract_directions(query, learnings, sources)

        duration = (time.time() - start_time) * 1000

        return ResearchResult(
            query=query,
            sources=sources,
            learnings=learnings,
            directions=directions,
            duration_ms=duration,
        )

    def _extract_sources(self, raw_results: List[Dict[str, Any]]) -> List[Source]:
        """Extract and score sources from raw results."""
        sources = []
        for idx, result in enumerate(raw_results):
            source = Source(
                title=result.get("title", f"Result {idx + 1}"),
                url=result.get("url", ""),
                snippet=result.get("snippet", result.get("content", "")[:200]),
                relevance_score=result.get("score", 1.0 - (idx * 0.1)),
            )
            sources.append(source)
        return sources

    def _extract_learnings(
        self, query: str, raw_results: List[Dict[str, Any]], sources: List[Source]
    ) -> List[Learning]:
        """Extract key learnings from raw results."""
        learnings = []

        for result in raw_results[: self.max_learnings]:
            content = result.get("content", result.get("snippet", ""))
            if not content:
                continue

            # Simulate learning extraction by creating structured summaries
            # In a real implementation, this would use an LLM to extract key insights
            learning_text = self._create_learning_text(query, content)
            related_sources = [sources[0]] if sources else []

            learning = Learning(text=learning_text, sources=related_sources)
            learnings.append(learning)

        return learnings

    def _create_learning_text(self, query: str, content: str) -> str:
        """Create a structured learning text from content."""
        # Simulate extraction — in real implementation, use LLM
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

        if not sentences:
            return f"Regarding '{query}': {content[:150]}..."

        # Pick the most informative sentence(s)
        key_sentences = sentences[:2]
        learning = " ".join(key_sentences)
        return learning[:300] + ("..." if len(learning) > 300 else "")

    def _extract_directions(
        self, query: str, learnings: List[Learning], sources: List[Source]
    ) -> List[Direction]:
        """Generate follow-up research directions from learnings."""
        directions = []

        for learning in learnings[: self.max_directions]:
            # Generate follow-up questions based on learning content
            follow_up_queries = self._generate_follow_ups(learning.text)

            for follow_up in follow_up_queries[:1]:  # 1 direction per learning
                direction = Direction(
                    query=follow_up,
                    rationale=f"Derived from learning: {learning.text[:80]}...",
                    relevance_score=learning.sources[0].relevance_score if learning.sources else 0.5,
                    parent_learning_ids=[learning.learning_id],
                )
                directions.append(direction)

        return directions

    def _generate_follow_ups(self, learning_text: str) -> List[str]:
        """Generate follow-up questions from a learning."""
        # Simulate follow-up generation — in real implementation, use LLM
        prompts = [
            f"What are the implications of: {learning_text[:80]}?",
            f"How does {learning_text[:60]} work in practice?",
            f"What are the alternatives to {learning_text[:60]}?",
            f"Why is {learning_text[:60]} important?",
            f"What are the limitations of {learning_text[:60]}?",
        ]
        return prompts


# ───────────────────────────────────────────────
# Research Node
# ───────────────────────────────────────────────

class ResearchNode:
    """A single research iteration unit with learning accumulation."""

    def __init__(
        self,
        query_generator: QueryGenerator,
        result_processor: ResultProcessor,
        search_func: Optional[Callable[[str], Awaitable[List[Dict[str, Any]]]]] = None,
    ):
        self.query_generator = query_generator
        self.result_processor = result_processor
        self.search_func = search_func or self._default_search

    async def execute(
        self,
        goal: str,
        depth_level: int,
        state: ResearchState,
        directions: Optional[List[Direction]] = None,
    ) -> ResearchIteration:
        """Execute one iteration of research: generate queries, search, process results."""
        iteration = ResearchIteration(depth_level=depth_level)

        # Generate queries
        context = state.all_learnings[-5:] if state.all_learnings else None
        queries = await self.query_generator.generate(goal, context, directions)
        iteration.queries = queries

        # Concurrent search execution
        search_tasks = [self._search_with_timing(q) for q in queries]
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Process results
        for query, raw_result in zip(queries, search_results):
            if isinstance(raw_result, Exception):
                # Log error but continue
                result = ResearchResult(
                    query=query,
                    sources=[],
                    learnings=[Learning(text=f"Search error for '{query}': {str(raw_result)}")],
                )
            else:
                result = await self.result_processor.process(query, raw_result)

            iteration.results.append(result)
            iteration.learnings.extend(result.learnings)
            iteration.directions.extend(result.directions)

            # Update global state
            state.add_sources(result.sources)
            state.visited_queries.add(query.lower().strip())

        # Deduplicate and add learnings to global state
        new_learnings = state.add_learnings(iteration.learnings)
        iteration.learnings = new_learnings

        return iteration

    async def _search_with_timing(self, query: str) -> List[Dict[str, Any]]:
        """Execute search with timing."""
        return await self.search_func(query)

    async def _default_search(self, query: str) -> List[Dict[str, Any]]:
        """Default search implementation — simulates search results."""
        # In a real implementation, this would call a search API (Serper, Google, Bing, etc.)
        # Here we simulate with structured mock data
        await asyncio.sleep(0.1)  # Simulate network delay

        # Generate simulated results based on query
        return [
            {
                "title": f"Result for: {query[:50]}",
                "url": f"https://example.com/search?q={query.replace(' ', '+')}",
                "snippet": f"This is a simulated search result for '{query}'. In a real implementation, this would contain actual search results from a search API like Google, Bing, or Serper. The result includes relevant information about the query topic with key insights and data points.",
                "content": f"Detailed content about {query}. This simulated result provides comprehensive information that would typically be extracted from a real web page. It includes key findings, statistics, expert opinions, and relevant context that helps answer the research query. The content is structured to demonstrate how the deep research engine processes and extracts learnings from search results.",
                "score": 0.9 - (i * 0.1),
            }
            for i in range(3)
        ]


# ───────────────────────────────────────────────
# Report Compiler
# ───────────────────────────────────────────────

class ReportCompiler:
    """Compiles research results into a hierarchical markdown report with citations."""

    def __init__(self, include_sources: bool = True, include_directions: bool = False):
        self.include_sources = include_sources
        self.include_directions = include_directions

    def compile(self, state: ResearchState, iterations: List[ResearchIteration]) -> str:
        """Compile a markdown report from research state and iterations."""
        sections = []

        # Title
        sections.append(f"# Deep Research Report: {state.goal}\n")

        # Metadata
        sections.append(self._compile_metadata(state, iterations))

        # Executive Summary
        sections.append(self._compile_executive_summary(state))

        # Key Learnings
        sections.append(self._compile_learnings(state))

        # Research Iterations Detail
        if len(iterations) > 1:
            sections.append(self._compile_iterations(iterations))

        # Sources
        if self.include_sources and state.all_sources:
            sections.append(self._compile_sources(state))

        # Directions (optional)
        if self.include_directions and state.all_directions:
            sections.append(self._compile_directions(state))

        return "\n".join(sections)

    def _compile_metadata(self, state: ResearchState, iterations: List[ResearchIteration]) -> str:
        """Compile report metadata section."""
        duration = time.time() - state.start_time
        return f"""## Metadata

- **Research Goal:** {state.goal}
- **Iterations Completed:** {len(iterations)}
- **Total Learnings:** {len(state.all_learnings)}
- **Total Sources:** {len(state.all_sources)}
- **Duration:** {duration:.1f}s
- **Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}

---

"""

    def _compile_executive_summary(self, state: ResearchState) -> str:
        """Compile executive summary from top learnings."""
        top_learnings = state.all_learnings[:5]
        summary_points = "\n".join(f"- {l.text[:150]}..." for l in top_learnings)

        return f"""## Executive Summary

This research explored **{state.goal}** through {len(state.all_learnings)} key learnings across multiple iterations. The following represent the most significant findings:

{summary_points}

---

"""

    def _compile_learnings(self, state: ResearchState) -> str:
        """Compile all learnings with citations."""
        sections = ["## Key Learnings\n"]

        for idx, learning in enumerate(state.all_learnings, 1):
            citation_links = " ".join(
                f"[{s.source_id}]" for s in learning.sources[:3]
            )
            sections.append(f"### {idx}. {learning.text[:100]}\n")
            sections.append(f"{learning.text}\n")
            if citation_links:
                sections.append(f"*Sources: {citation_links}*\n")
            sections.append("")

        return "\n".join(sections) + "\n---\n\n"

    def _compile_iterations(self, iterations: List[ResearchIteration]) -> str:
        """Compile iteration-by-iteration detail."""
        sections = ["## Research Iterations\n"]

        for iteration in iterations:
            sections.append(f"### Iteration {iteration.depth_level} ({iteration.iteration_id})\n")
            sections.append(f"**Queries explored:** {len(iteration.queries)}\n")
            sections.append(f"**New learnings:** {len(iteration.learnings)}\n")
            sections.append(f"**New directions:** {len(iteration.directions)}\n")

            if iteration.queries:
                sections.append("\n**Queries:**\n")
                for q in iteration.queries:
                    sections.append(f"- {q}\n")

            sections.append("")

        return "\n".join(sections) + "\n---\n\n"

    def _compile_sources(self, state: ResearchState) -> str:
        """Compile sources bibliography."""
        sections = ["## Sources\n"]

        for source in state.all_sources:
            sections.append(f"- {source.to_citation()}\n")
            if source.snippet:
                sections.append(f"  > {source.snippet[:100]}...\n")

        return "\n".join(sections) + "\n---\n\n"

    def _compile_directions(self, state: ResearchState) -> str:
        """Compile follow-up directions."""
        sections = ["## Future Research Directions\n"]

        for direction in state.all_directions[:10]:
            sections.append(f"- **{direction.query}** (score: {direction.relevance_score:.2f})\n")
            sections.append(f"  {direction.rationale}\n")

        return "\n".join(sections) + "\n"


# ───────────────────────────────────────────────
# Main Orchestrator: DeepResearch
# ───────────────────────────────────────────────

class DeepResearch:
    """
    Main orchestrator for deep recursive research.

    Configurable breadth (3-10 parallel queries) and depth (1-5 recursion levels).
    Supports custom search functions and LLM query generators.
    """

    def __init__(
        self,
        breadth: int = 5,
        depth: int = 3,
        query_generator: Optional[QueryGenerator] = None,
        result_processor: Optional[ResultProcessor] = None,
        report_compiler: Optional[ReportCompiler] = None,
        search_func: Optional[Callable[[str], Awaitable[List[Dict[str, Any]]]]] = None,
        max_directions_per_iteration: int = 3,
        relevance_threshold: float = 0.3,
    ):
        self.breadth = max(3, min(10, breadth))
        self.depth = max(1, min(5, depth))
        self.max_directions = max_directions_per_iteration
        self.relevance_threshold = relevance_threshold

        self.query_generator = query_generator or QueryGenerator(breadth=self.breadth)
        self.result_processor = result_processor or ResultProcessor()
        self.report_compiler = report_compiler or ReportCompiler()
        self.search_func = search_func

        self._node = ResearchNode(
            query_generator=self.query_generator,
            result_processor=self.result_processor,
            search_func=self.search_func,
        )

    async def run(self, goal: str, context: Optional[str] = None) -> str:
        """
        Execute deep research on the given goal.

        Args:
            goal: The research goal/question
            context: Optional initial context or background

        Returns:
            Markdown formatted research report
        """
        state = ResearchState(goal=goal)
        iterations: List[ResearchIteration] = []
        directions: Optional[List[Direction]] = None

        for level in range(1, self.depth + 1):
            # Execute iteration
            iteration = await self._node.execute(goal, level, state, directions)
            iterations.append(iteration)
            state.iteration_count += 1

            # Check if we should continue deeper
            if level < self.depth:
                # Prune directions based on relevance
                new_directions = state.prune_directions(
                    iteration.directions, self.max_directions
                )
                # Filter by threshold
                new_directions = [
                    d for d in new_directions if d.relevance_score >= self.relevance_threshold
                ]

                if not new_directions:
                    break  # No promising directions, stop early

                directions = new_directions
                state.all_directions.extend(new_directions)
            else:
                state.all_directions.extend(iteration.directions)

        # Compile report
        return self.report_compiler.compile(state, iterations)

    async def run_structured(self, goal: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute research and return structured data instead of markdown.

        Returns dict with: goal, learnings, sources, iterations, directions, report
        """
        state = ResearchState(goal=goal)
        iterations: List[ResearchIteration] = []
        directions: Optional[List[Direction]] = None

        for level in range(1, self.depth + 1):
            iteration = await self._node.execute(goal, level, state, directions)
            iterations.append(iteration)
            state.iteration_count += 1

            if level < self.depth:
                new_directions = state.prune_directions(
                    iteration.directions, self.max_directions
                )
                new_directions = [
                    d for d in new_directions if d.relevance_score >= self.relevance_threshold
                ]

                if not new_directions:
                    break

                directions = new_directions
                state.all_directions.extend(new_directions)
            else:
                state.all_directions.extend(iteration.directions)

        report = self.report_compiler.compile(state, iterations)

        return {
            "goal": goal,
            "learnings": [
                {"text": l.text, "sources": [s.source_id for s in l.sources]}
                for l in state.all_learnings
            ],
            "sources": [
                {"id": s.source_id, "title": s.title, "url": s.url}
                for s in state.all_sources
            ],
            "iterations": [
                {
                    "level": i.depth_level,
                    "queries": i.queries,
                    "learning_count": len(i.learnings),
                    "direction_count": len(i.directions),
                }
                for i in iterations
            ],
            "directions": [
                {"query": d.query, "score": d.relevance_score, "rationale": d.rationale}
                for d in state.all_directions
            ],
            "report": report,
        }


# ───────────────────────────────────────────────
# Demo / Self-Test
# ───────────────────────────────────────────────

async def _demo():
    """Demonstrate DeepResearch capabilities."""
    print("=" * 60)
    print("DeepResearch Native — Self Test")
    print("=" * 60)

    # Test 1: Basic research
    print("\n[Test 1] Basic research with default settings")
    dr = DeepResearch(breadth=3, depth=2)
    report = await dr.run("asyncio best practices in Python 2024")
    print(f"Report length: {len(report)} chars")
    print(f"First 500 chars:\n{report[:500]}...")

    # Test 2: Structured output
    print("\n[Test 2] Structured output")
    dr2 = DeepResearch(breadth=3, depth=2)
    structured = await dr2.run_structured("machine learning deployment patterns")
    print(f"Learnings: {len(structured['learnings'])}")
    print(f"Sources: {len(structured['sources'])}")
    print(f"Iterations: {len(structured['iterations'])}")
    print(f"Directions: {len(structured['directions'])}")

    # Test 3: Custom search function
    print("\n[Test 3] Custom search function")

    async def custom_search(query: str) -> List[Dict[str, Any]]:
        return [
            {
                "title": f"Custom: {query}",
                "url": f"https://custom.example.com/{query.replace(' ', '-')}",
                "snippet": f"Custom search result for {query}",
                "content": f"Detailed custom content about {query} with specific insights and data points relevant to the research goal.",
                "score": 0.95,
            }
        ]

    dr3 = DeepResearch(breadth=3, depth=2, search_func=custom_search)
    report3 = await dr3.run("custom integration test")
    print(f"Custom report length: {len(report3)} chars")

    # Test 4: Breadth and depth bounds
    print("\n[Test 4] Bounds validation")
    dr4 = DeepResearch(breadth=15, depth=10)
    assert dr4.breadth == 10, "Breadth should be capped at 10"
    assert dr4.depth == 5, "Depth should be capped at 5"
    print(f"Breadth capped: {dr4.breadth} (requested 15)")
    print(f"Depth capped: {dr4.depth} (requested 10)")

    print("\n" + "=" * 60)
    print("All tests passed ✓")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(_demo())
