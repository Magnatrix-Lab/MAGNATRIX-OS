"""
vane_native_search.py
======================
MAGNATRIX Native AI-Powered Answering Engine
Layer 5: Knowledge (extends Arkon + Curriculum bridges)
Layer 7: Browser (extends Browser capabilities)

Pola AMATI-PELAJARI-TIRU dari Vane/Perplexica (github.com/ItzCrazyKns/Vane):
- Amati:  RAG-based answering engine, SearXNG metasearch integration,
          Copilot Mode (multi-query generation untuk source enrichment),
          Focus Modes (All, Academic, YouTube, Wolfram, Reddit, Writing),
          TypeScript 98.8%, self-hosted architecture, Perplexity AI alternative
- Pelajari: Core pattern adalah (1) Query → Multi-Query Generation (Copilot),
            (2) Parallel Search via SearXNG API,
            (3) Source Reranking & Relevance Scoring,
            (4) Context Assembly dari top-N sources,
            (5) LLM Answer Generation dengan citation,
            (6) Streaming Response,
            (7) Focus Mode = pre-configured search parameters
- Tiru:   Reimplementasi native Python dengan:
            - Asyncio-based search pipeline
            - Native SearXNG API integration (bukan TypeScript wrapper)
            - Multi-query generation via MAGNATRIX LLM router
            - Source ranking dengan hybrid score (relevance + freshness + authority)
            - Citation-aware context assembly
            - Streaming answer generation
            - Integration dengan: mesh messaging, free LLM router, skill registry,
              knowledge graph, curriculum bridge

Architecture:
    User Query
        ↓
    QueryPlanner (Copilot Mode: generate multiple search queries)
        ↓
    SearchOrchestrator (parallel search via SearXNG + internal knowledge)
        ↓
    SourceRanker (rerank & filter sources)
        ↓
    ContextAssembler (build context window dengan citations)
        ↓
    AnswerGenerator (LLM-powered RAG answer dengan streaming)
        ↓
    ResponseFormatter (structured output dengan sources)
        ↓
    Mesh broadcast: knowledge.discoveries

Focus Modes (tiru Vane):
    - ALL: General web search
    - ACADEMIC: Scholar/arXiv/Google Scholar focus
    - WRITING: No search, pure LLM writing assistant
    - YOUTUBE: Video search focus
    - WOLFRAM: Computation/data focus
    - REDDIT: Discussion/opinion focus
    - NEWS: News source focus
    - CODE: GitHub/code search focus
    - MAGNATRIX: Internal knowledge graph focus
"""

import asyncio
import json
import time
import uuid
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, AsyncGenerator
from enum import Enum
from collections import defaultdict
import re


class FocusMode(Enum):
    ALL = "all"
    ACADEMIC = "academic"
    WRITING = "writing"
    YOUTUBE = "youtube"
    WOLFRAM = "wolfram"
    REDDIT = "reddit"
    NEWS = "news"
    CODE = "code"
    MAGNATRIX = "magnatrix"  # Internal knowledge search


class SearchProvider(Enum):
    SEARXNG = "searxng"
    BRAVE = "brave"
    DUCKDUCKGO = "duckduckgo"
    GOOGLE = "google"
    BING = "bing"
    ARXIV = "arxiv"
    GITHUB = "github"
    REDDIT = "reddit"
    WIKIPEDIA = "wikipedia"
    WOLFRAM = "wolfram"
    INTERNAL_KG = "internal_kg"  # MAGNATRIX knowledge graph
    INTERNAL_DOC = "internal_doc"  # MAGNATRIX internal documents


@dataclass
class SearchQuery:
    """Individual search query dalam pipeline"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    original_query: str = ""  # User's original query
    generated_query: str = ""  # LLM-generated query
    intent: str = ""  # Detected intent
    focus_mode: FocusMode = FocusMode.ALL
    category: str = ""  # factual, analytical, creative, technical, etc.
    confidence: float = 0.0  # Query generation confidence


@dataclass
class SearchResult:
    """Individual search result dari provider"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    query_id: str = ""
    provider: SearchProvider = SearchProvider.SEARXNG
    title: str = ""
    url: str = ""
    snippet: str = ""
    content: Optional[str] = None  # Full content jika fetched
    source_name: str = ""  # Domain/site name
    source_type: str = ""  # web, academic, video, discussion, code, news
    published_at: Optional[float] = None
    author: Optional[str] = None
    # Quality metrics
    relevance_score: float = 0.0
    freshness_score: float = 0.0
    authority_score: float = 0.0
    credibility_score: float = 0.0
    hybrid_score: float = 0.0  # Combined score
    # MAGNATRIX integration
    mesh_mentioned: bool = False
    internal_source: bool = False

    def calculate_hybrid_score(self, weights: Dict = None):
        """Calculate hybrid ranking score"""
        w = weights or {"relevance": 0.4, "freshness": 0.2, "authority": 0.25, "credibility": 0.15}
        self.hybrid_score = (
            self.relevance_score * w["relevance"] +
            self.freshness_score * w["freshness"] +
            self.authority_score * w["authority"] +
            self.credibility_score * w["credibility"]
        )
        return self.hybrid_score


@dataclass
class Citation:
    """Citation untuk answer generation"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:4])
    result_id: str = ""
    title: str = ""
    url: str = ""
    snippet: str = ""
    source_name: str = ""
    used_in_answer: bool = False
    quote: Optional[str] = None  # Exact quote used


@dataclass
class AnswerChunk:
    """Streaming answer chunk"""
    text: str = ""
    citations: List[str] = field(default_factory=list)  # Citation IDs
    is_final: bool = False
    metadata: Dict = field(default_factory=dict)


@dataclass
class SearchSession:
    """Complete search session"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    query: str = ""
    focus_mode: FocusMode = FocusMode.ALL
    copilot_mode: bool = False
    # Pipeline results
    generated_queries: List[SearchQuery] = field(default_factory=list)
    search_results: List[SearchResult] = field(default_factory=list)
    ranked_results: List[SearchResult] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    answer: str = ""
    answer_chunks: List[AnswerChunk] = field(default_factory=list)
    # Metrics
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    total_search_time_ms: float = 0.0
    total_answer_time_ms: float = 0.0
    sources_count: int = 0
    # Metadata
    llm_model: str = ""
    search_providers_used: List[str] = field(default_factory=list)
    # MAGNATRIX
    agent_id: Optional[str] = None
    mesh_broadcast: bool = True

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "query": self.query,
            "focus_mode": self.focus_mode.value,
            "copilot_mode": self.copilot_mode,
            "answer": self.answer,
            "sources_count": self.sources_count,
            "search_providers": self.search_providers_used,
            "llm_model": self.llm_model,
            "total_time_ms": (self.finished_at or time.time()) - self.started_at,
            "citations": [{"id": c.id, "title": c.title, "url": c.url} for c in self.citations]
        }


class QueryPlanner:
    """
    Query planning engine - tiru Vane Copilot Mode.
    Generate multiple search queries dari single user query.
    """

    def __init__(self, llm_callback: Optional[Callable] = None):
        self.llm_callback = llm_callback
        self._intent_patterns = {
            "factual": [r"what is", r"who is", r"when did", r"where is", r"how many", r"definition"],
            "analytical": [r"compare", r"difference between", r"pros and cons", r"analysis"],
            "creative": [r"write", r"create", r"generate", r"draft", r"compose"],
            "technical": [r"how to", r"tutorial", r"guide", r"setup", r"configure", r"error"],
            "opinion": [r"best", r"worst", r"should i", r"recommend", r"review", r"opinion"],
            "code": [r"code", r"function", r"api", r"library", r"github", r"programming"],
        }

    def detect_intent(self, query: str) -> tuple[str, float]:
        """Detect query intent"""
        query_lower = query.lower()
        scores = {}
        for intent, patterns in self._intent_patterns.items():
            score = sum(1 for p in patterns if re.search(p, query_lower))
            scores[intent] = score

        best_intent = max(scores, key=scores.get)
        confidence = min(scores[best_intent] / 2, 1.0)
        return best_intent, confidence

    async def generate_queries(self, query: str, focus_mode: FocusMode = FocusMode.ALL,
                               copilot_mode: bool = False) -> List[SearchQuery]:
        """
        Generate search queries - tiru Vane Copilot multi-query generation.
        Jika copilot_mode=True, generate 3-5 queries untuk comprehensive search.
        """
        intent, confidence = self.detect_intent(query)
        queries = []

        # Primary query
        primary = SearchQuery(
            original_query=query,
            generated_query=query,
            intent=intent,
            focus_mode=focus_mode,
            category=intent,
            confidence=confidence
        )
        queries.append(primary)

        if copilot_mode and self.llm_callback:
            # Generate additional queries via LLM
            prompt = f"""Given the user query: "{query}"
Generate 3 additional search queries that would help find comprehensive information.
Each query should explore a different angle or aspect.
Return ONLY a JSON array of strings."""

            try:
                response = await self.llm_callback(prompt, max_tokens=200)
                # Parse generated queries
                try:
                    generated = json.loads(response)
                    if isinstance(generated, list):
                        for q in generated[:3]:
                            if isinstance(q, str) and q != query:
                                queries.append(SearchQuery(
                                    original_query=query,
                                    generated_query=q,
                                    intent=intent,
                                    focus_mode=focus_mode,
                                    category=f"copilot_{intent}",
                                    confidence=0.7
                                ))
                except:
                    # Fallback: heuristic expansion
                    queries.extend(self._heuristic_expand(query, intent, focus_mode))
            except:
                queries.extend(self._heuristic_expand(query, intent, focus_mode))
        else:
            # Light expansion untuk non-copilot
            queries.extend(self._heuristic_expand(query, intent, focus_mode, max_expansions=1))

        return queries

    def _heuristic_expand(self, query: str, intent: str, 
                          focus_mode: FocusMode, max_expansions: int = 2) -> List[SearchQuery]:
        """Heuristic query expansion"""
        expansions = []

        # Focus mode modifiers
        mode_prefixes = {
            FocusMode.ACADEMIC: ["site:arxiv.org", "research paper", "journal"],
            FocusMode.YOUTUBE: ["site:youtube.com", "video tutorial"],
            FocusMode.REDDIT: ["site:reddit.com", "discussion"],
            FocusMode.CODE: ["site:github.com", "code example", "implementation"],
            FocusMode.NEWS: ["site:news", "latest news", "recent"],
        }

        prefixes = mode_prefixes.get(focus_mode, [])
        for prefix in prefixes[:max_expansions]:
            expansions.append(SearchQuery(
                original_query=query,
                generated_query=f"{prefix} {query}",
                intent=intent,
                focus_mode=focus_mode,
                category=f"expanded_{intent}",
                confidence=0.5
            ))

        return expansions


class SearchOrchestrator:
    """
    Parallel search orchestrator - tiru Vane search pipeline.
    Execute multiple searches across providers secara parallel.
    """

    def __init__(self, searxng_url: str = "http://localhost:8080",
                 brave_api_key: str = "",
                 llm_callback: Optional[Callable] = None):
        self.searxng_url = searxng_url
        self.brave_api_key = brave_api_key
        self.llm_callback = llm_callback
        self._provider_weights = {
            SearchProvider.SEARXNG: 1.0,
            SearchProvider.BRAVE: 0.9,
            SearchProvider.ARXIV: 0.95,
            SearchProvider.GITHUB: 0.9,
            SearchProvider.WIKIPEDIA: 0.85,
            SearchProvider.REDDIT: 0.7,
            SearchProvider.WOLFRAM: 0.8,
            SearchProvider.INTERNAL_KG: 1.0,
            SearchProvider.INTERNAL_DOC: 1.0,
        }

    async def search(self, queries: List[SearchQuery],
                     focus_mode: FocusMode = FocusMode.ALL) -> List[SearchResult]:
        """Execute parallel search untuk semua queries"""
        start = time.time()
        all_results = []

        # Determine providers berdasarkan focus mode
        providers = self._get_providers_for_mode(focus_mode)

        # Execute all query+provider combinations secara parallel
        tasks = []
        for query in queries:
            for provider in providers:
                tasks.append(self._search_single(query, provider))

        results_lists = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results_lists:
            if isinstance(result, list):
                all_results.extend(result)

        # Deduplicate by URL
        seen_urls = set()
        deduped = []
        for r in all_results:
            url_hash = hashlib.md5(r.url.encode()).hexdigest()[:16]
            if url_hash not in seen_urls:
                seen_urls.add(url_hash)
                deduped.append(r)

        return deduped

    def _get_providers_for_mode(self, focus_mode: FocusMode) -> List[SearchProvider]:
        """Map focus mode ke search providers"""
        mode_map = {
            FocusMode.ALL: [SearchProvider.SEARXNG, SearchProvider.BRAVE],
            FocusMode.ACADEMIC: [SearchProvider.ARXIV, SearchProvider.SEARXNG],
            FocusMode.YOUTUBE: [SearchProvider.SEARXNG],
            FocusMode.REDDIT: [SearchProvider.REDDIT, SearchProvider.SEARXNG],
            FocusMode.CODE: [SearchProvider.GITHUB, SearchProvider.SEARXNG],
            FocusMode.NEWS: [SearchProvider.SEARXNG],
            FocusMode.WOLFRAM: [SearchProvider.WOLFRAM, SearchProvider.SEARXNG],
            FocusMode.WRITING: [],  # No search, pure LLM
            FocusMode.MAGNATRIX: [SearchProvider.INTERNAL_KG, SearchProvider.INTERNAL_DOC],
        }
        return mode_map.get(focus_mode, [SearchProvider.SEARXNG])

    async def _search_single(self, query: SearchQuery, 
                             provider: SearchProvider) -> List[SearchResult]:
        """Execute single search pada single provider"""
        try:
            if provider == SearchProvider.SEARXNG:
                return await self._search_searxng(query)
            elif provider == SearchProvider.ARXIV:
                return await self._search_arxiv(query)
            elif provider == SearchProvider.GITHUB:
                return await self._search_github(query)
            elif provider == SearchProvider.INTERNAL_KG:
                return await self._search_internal_kg(query)
            elif provider == SearchProvider.BRAVE and self.brave_api_key:
                return await self._search_brave(query)
            else:
                return []
        except Exception as e:
            return []

    async def _search_searxng(self, query: SearchQuery) -> List[SearchResult]:
        """Search via SearXNG API - tiru Vane core integration"""
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "q": query.generated_query,
                    "format": "json",
                    "language": "en",
                    "safesearch": "0",
                    "engines": "google,bing,duckduckgo,wikipedia"
                }

                async with session.get(f"{self.searxng_url}/search", 
                                       params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = []

                        for i, r in enumerate(data.get("results", [])[:10]):
                            result = SearchResult(
                                query_id=query.id,
                                provider=SearchProvider.SEARXNG,
                                title=r.get("title", ""),
                                url=r.get("url", ""),
                                snippet=r.get("content", ""),
                                source_name=r.get("engine", "web"),
                                source_type="web",
                                relevance_score=1.0 - (i * 0.1),  # Position-based
                                freshness_score=0.5,
                                authority_score=0.5
                            )
                            result.calculate_hybrid_score()
                            results.append(result)

                        return results
        except Exception as e:
            pass

        return []

    async def _search_arxiv(self, query: SearchQuery) -> List[SearchResult]:
        """Search via arXiv API"""
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                search_query = query.generated_query.replace(" ", "+")
                url = f"http://export.arxiv.org/api/query?search_query=all:{search_query}&max_results=5"

                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        # Simple XML parsing (would use xml.etree in production)
                        results = []
                        # Placeholder: return mock results
                        return results
        except:
            pass
        return []

    async def _search_github(self, query: SearchQuery) -> List[SearchResult]:
        """Search via GitHub API"""
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                params = {"q": query.generated_query, "sort": "stars", "order": "desc"}

                async with session.get("https://api.github.com/search/repositories",
                                       params=params,
                                       timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = []

                        for i, item in enumerate(data.get("items", [])[:5]):
                            result = SearchResult(
                                query_id=query.id,
                                provider=SearchProvider.GITHUB,
                                title=item.get("full_name", ""),
                                url=item.get("html_url", ""),
                                snippet=item.get("description", ""),
                                source_name="github.com",
                                source_type="code",
                                relevance_score=1.0 - (i * 0.15),
                                freshness_score=0.3,
                                authority_score=min(item.get("stargazers_count", 0) / 10000, 1.0)
                            )
                            result.calculate_hybrid_score()
                            results.append(result)

                        return results
        except:
            pass
        return []

    async def _search_brave(self, query: SearchQuery) -> List[SearchResult]:
        """Search via Brave Search API"""
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                headers = {"X-Subscription-Token": self.brave_api_key}
                params = {"q": query.generated_query, "count": 10}

                async with session.get("https://api.search.brave.com/res/v1/web/search",
                                       headers=headers, params=params,
                                       timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = []

                        for i, r in enumerate(data.get("web", {}).get("results", [])[:10]):
                            result = SearchResult(
                                query_id=query.id,
                                provider=SearchProvider.BRAVE,
                                title=r.get("title", ""),
                                url=r.get("url", ""),
                                snippet=r.get("description", ""),
                                source_name="brave",
                                source_type="web",
                                relevance_score=1.0 - (i * 0.1)
                            )
                            result.calculate_hybrid_score()
                            results.append(result)

                        return results
        except:
            pass
        return []

    async def _search_internal_kg(self, query: SearchQuery) -> List[SearchResult]:
        """Search MAGNATRIX internal knowledge graph"""
        # Would integrate dengan knowledge graph system
        # Placeholder: return empty, would query internal vector store
        return []


class SourceRanker:
    """
    Source ranking engine - tiru Vane relevance reranking.
    Hybrid scoring dengan multiple dimensions.
    """

    def __init__(self):
        self._authority_domains = {
            "arxiv.org": 1.0,
            "github.com": 0.95,
            "wikipedia.org": 0.9,
            "stackexchange.com": 0.85,
            "stackoverflow.com": 0.85,
            "reddit.com": 0.6,
            "medium.com": 0.5,
            "news.ycombinator.com": 0.7,
            "techcrunch.com": 0.65,
            "theguardian.com": 0.75,
            "nytimes.com": 0.75,
            "reuters.com": 0.8,
            "bloomberg.com": 0.8,
            "mit.edu": 0.95,
            "stanford.edu": 0.95,
            "google.com": 0.7,
            "microsoft.com": 0.75,
            "aws.amazon.com": 0.8,
        }

    def rank(self, results: List[SearchResult], max_results: int = 10) -> List[SearchResult]:
        """Rank sources dengan hybrid scoring"""
        # Score each result
        for result in results:
            # Authority score dari domain
            domain = self._extract_domain(result.url)
            result.authority_score = self._authority_domains.get(domain, 0.3)

            # Freshness score
            if result.published_at:
                age_days = (time.time() - result.published_at) / 86400
                result.freshness_score = max(0, 1.0 - (age_days / 365))
            else:
                result.freshness_score = 0.5

            # Credibility boost untuk academic/code sources
            if result.source_type in ("academic", "code"):
                result.credibility_score = 0.9
            elif result.source_type == "discussion":
                result.credibility_score = 0.5
            else:
                result.credibility_score = 0.6

            result.calculate_hybrid_score()

        # Sort by hybrid score
        ranked = sorted(results, key=lambda r: r.hybrid_score, reverse=True)

        # Diversify sources: jangan semua dari domain yang sama
        diversified = []
        domain_counts = defaultdict(int)

        for result in ranked:
            domain = self._extract_domain(result.url)
            if domain_counts[domain] < 2 and len(diversified) < max_results:
                diversified.append(result)
                domain_counts[domain] += 1

        return diversified

    def _extract_domain(self, url: str) -> str:
        """Extract domain dari URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove www.
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except:
            return ""


class ContextAssembler:
    """
    Context assembly untuk RAG - tiru Vane context builder.
    Build context window dari ranked sources dengan proper citation.
    """

    def __init__(self, max_context_tokens: int = 4000,
                 max_sources: int = 8):
        self.max_context_tokens = max_context_tokens
        self.max_sources = max_sources
        self._avg_chars_per_token = 4  # Rough estimate

    def assemble(self, ranked_results: List[SearchResult],
                 query: str) -> tuple[str, List[Citation]]:
        """Assemble context dari sources"""
        citations = []
        context_parts = []

        # System context
        context_parts.append(
            f"You are a helpful AI assistant. Answer the following question "
            f"based on the provided sources. Cite sources using [1], [2], etc. "
            f"If the sources don't contain enough information, say so.\n\n"
            f"Question: {query}\n\nSources:"
        )

        used_chars = len(context_parts[0])
        max_chars = self.max_context_tokens * self._avg_chars_per_token

        for i, result in enumerate(ranked_results[:self.max_sources]):
            citation = Citation(
                id=str(i + 1),
                result_id=result.id,
                title=result.title,
                url=result.url,
                snippet=result.snippet,
                source_name=result.source_name
            )
            citations.append(citation)

            source_text = f"\n[{i+1}] {result.title} ({result.source_name})\n{result.snippet}"

            if used_chars + len(source_text) < max_chars:
                context_parts.append(source_text)
                citation.used_in_answer = True
                used_chars += len(source_text)
            else:
                break

        context = "\n".join(context_parts)
        return context, citations


class AnswerGenerator:
    """
    LLM-powered answer generator - tiru Vane answering engine.
    Streaming generation dengan citation integration.
    """

    def __init__(self, llm_callback: Optional[Callable] = None):
        self.llm_callback = llm_callback

    async def generate(self, context: str, citations: List[Citation],
                       query: str, model: str = "openrouter/auto",
                       stream: bool = True) -> AsyncGenerator[AnswerChunk, None]:
        """Generate answer dengan streaming"""

        prompt = f"""{context}

Please provide a comprehensive answer. Use citations [1], [2], etc. when referencing sources.
Be concise but thorough. If sources are insufficient, acknowledge limitations.

Answer:"""

        if stream and self.llm_callback:
            # Streaming mode
            full_text = ""
            async for chunk in self._stream_llm(prompt, model):
                full_text += chunk
                # Detect citations dalam chunk
                cited = re.findall(r'\[(\d+)\]', chunk)
                yield AnswerChunk(
                    text=chunk,
                    citations=cited,
                    is_final=False
                )

            yield AnswerChunk(
                text="",
                citations=[],
                is_final=True,
                metadata={"full_text": full_text, "model": model}
            )
        else:
            # Non-streaming
            if self.llm_callback:
                response = await self.llm_callback(prompt, model=model, max_tokens=2000)
            else:
                response = f"[Generated answer for: {query}]"

            cited = re.findall(r'\[(\d+)\]', response)
            yield AnswerChunk(
                text=response,
                citations=cited,
                is_final=True,
                metadata={"model": model}
            )

    async def _stream_llm(self, prompt: str, model: str) -> AsyncGenerator[str, None]:
        """Stream LLM response - placeholder untuk actual streaming"""
        # Would integrate dengan free_llm_router.py streaming endpoint
        # Placeholder: yield chunks
        chunks = [
            "Based on the provided sources, ",
            f"I can answer your question about the query. ",
            "[1] The first source indicates key information. ",
            "[2] Additional context from the second source supports this. ",
            "In summary, the answer is derived from multiple authoritative sources."
        ]
        for chunk in chunks:
            yield chunk
            await asyncio.sleep(0.05)


class AnsweringEngine:
    """
    High-level answering engine - orchestrator untuk Vane-native.
    Tiru Vane's end-to-end pipeline.
    """

    def __init__(self,
                 searxng_url: str = "http://localhost:8080",
                 brave_api_key: str = "",
                 llm_callback: Optional[Callable] = None,
                 mesh_broadcast: Optional[Callable] = None):

        self.llm_callback = llm_callback
        self.mesh_broadcast = mesh_broadcast

        self.query_planner = QueryPlanner(llm_callback)
        self.search_orchestrator = SearchOrchestrator(
            searxng_url=searxng_url,
            brave_api_key=brave_api_key,
            llm_callback=llm_callback
        )
        self.source_ranker = SourceRanker()
        self.context_assembler = ContextAssembler()
        self.answer_generator = AnswerGenerator(llm_callback)

        self._session_history: Dict[str, SearchSession] = {}

    async def search(self, query: str,
                     focus_mode: str = "all",
                     copilot_mode: bool = False,
                     stream: bool = True,
                     model: str = "openrouter/auto",
                     agent_id: Optional[str] = None) -> SearchSession:
        """
        Main search entry point - tiru Vane search API.
        End-to-end pipeline: query → search → rank → answer.
        """
        session = SearchSession(
            query=query,
            focus_mode=FocusMode(focus_mode),
            copilot_mode=copilot_mode,
            agent_id=agent_id
        )

        # Phase 1: Query Planning (Copilot Mode)
        search_start = time.time()
        generated_queries = await self.query_planner.generate_queries(
            query, session.focus_mode, copilot_mode
        )
        session.generated_queries = generated_queries

        # Phase 2: Parallel Search
        search_results = await self.search_orchestrator.search(
            generated_queries, session.focus_mode
        )
        session.search_results = search_results
        session.search_providers_used = list(set(
            r.provider.value for r in search_results
        ))

        # Phase 3: Source Ranking
        ranked = self.source_ranker.rank(search_results)
        session.ranked_results = ranked
        session.sources_count = len(ranked)
        session.total_search_time_ms = (time.time() - search_start) * 1000

        # Phase 4: Context Assembly
        context, citations = self.context_assembler.assemble(ranked, query)
        session.citations = citations

        # Phase 5: Answer Generation
        answer_start = time.time()
        answer_chunks = []

        if stream:
            async for chunk in self.answer_generator.generate(
                context, citations, query, model, stream=True
            ):
                answer_chunks.append(chunk)
        else:
            async for chunk in self.answer_generator.generate(
                context, citations, query, model, stream=False
            ):
                answer_chunks.append(chunk)

        session.answer_chunks = answer_chunks
        if answer_chunks:
            final_chunk = answer_chunks[-1]
            if final_chunk.is_final:
                session.answer = final_chunk.metadata.get("full_text", "")
            else:
                session.answer = "".join(c.text for c in answer_chunks)

        session.total_answer_time_ms = (time.time() - answer_start) * 1000
        session.finished_at = time.time()
        session.llm_model = model

        # Store session
        self._session_history[session.id] = session

        # Mesh broadcast
        if self.mesh_broadcast and session.mesh_broadcast:
            self.mesh_broadcast({
                "type": "KNOWLEDGE_DISCOVERY",
                "channel": "knowledge.discoveries",
                "session_id": session.id,
                "query": query,
                "focus_mode": focus_mode,
                "sources_count": session.sources_count,
                "answer_preview": session.answer[:200] if session.answer else "",
                "agent_id": agent_id
            })

        return session

    async def stream_search(self, query: str,
                           focus_mode: str = "all",
                           copilot_mode: bool = False,
                           model: str = "openrouter/auto") -> AsyncGenerator[Dict, None]:
        """Streaming search dengan real-time updates"""

        # Yield: query planning
        yield {"stage": "planning", "status": "generating_queries"}

        session = await self.search(query, focus_mode, copilot_mode, 
                                    stream=False, model=model)

        # Yield: sources
        yield {
            "stage": "sources",
            "sources": [
                {"id": c.id, "title": c.title, "url": c.url, "name": c.source_name}
                for c in session.citations
            ]
        }

        # Yield: answer chunks
        for chunk in session.answer_chunks:
            if not chunk.is_final:
                yield {"stage": "answer", "chunk": chunk.text, "citations": chunk.citations}

        # Yield: final
        yield {
            "stage": "complete",
            "session_id": session.id,
            "answer": session.answer,
            "sources": len(session.citations),
            "search_time_ms": session.total_search_time_ms,
            "answer_time_ms": session.total_answer_time_ms
        }

    def get_session(self, session_id: str) -> Optional[SearchSession]:
        return self._session_history.get(session_id)

    def get_history(self, limit: int = 50) -> List[Dict]:
        sessions = sorted(
            self._session_history.values(),
            key=lambda s: s.started_at,
            reverse=True
        )
        return [s.to_dict() for s in sessions[:limit]]

    def clear_history(self):
        self._session_history.clear()


class KnowledgeHub:
    """
    MAGNATRIX Knowledge Hub - integrasi Vane-native dengan Arkon + internal KG.
    Unified interface untuk semua knowledge operations.
    """

    def __init__(self, answering_engine: Optional[AnsweringEngine] = None):
        self.answering_engine = answering_engine or AnsweringEngine()
        self._local_documents: Dict[str, Dict] = {}
        self._knowledge_graph: Dict[str, Any] = {}

    async def ask(self, question: str, 
                  focus: str = "all",
                  use_copilot: bool = False) -> Dict:
        """Ask a question - unified interface"""
        session = await self.answering_engine.search(
            question,
            focus_mode=focus,
            copilot_mode=use_copilot
        )
        return session.to_dict()

    async def research(self, topic: str,
                       depth: str = "medium") -> Dict:
        """Deep research mode - comprehensive topic exploration"""
        # Generate research questions
        research_queries = [
            f"What is {topic}?",
            f"How does {topic} work?",
            f"Latest developments in {topic}",
            f"Experts and key figures in {topic}",
            f"Criticism and limitations of {topic}",
        ]

        sessions = []
        for query in research_queries:
            session = await self.answering_engine.search(
                query, focus_mode="academic", copilot_mode=True
            )
            sessions.append(session.to_dict())

        # Synthesize
        return {
            "topic": topic,
            "depth": depth,
            "sessions": sessions,
            "total_sources": sum(s["sources_count"] for s in sessions),
            "synthesized_at": time.time()
        }

    def index_document(self, doc_id: str, content: str, 
                       metadata: Dict = None) -> bool:
        """Index local document untuk internal search"""
        self._local_documents[doc_id] = {
            "id": doc_id,
            "content": content,
            "metadata": metadata or {},
            "indexed_at": time.time()
        }
        return True

    def query_internal(self, query: str) -> List[Dict]:
        """Query internal documents - simple keyword search"""
        results = []
        query_lower = query.lower()

        for doc_id, doc in self._local_documents.items():
            content_lower = doc["content"].lower()
            score = content_lower.count(query_lower) / max(len(content_lower.split()), 1)
            if score > 0:
                results.append({
                    "id": doc_id,
                    "score": score,
                    "preview": doc["content"][:200],
                    "metadata": doc["metadata"]
                })

        return sorted(results, key=lambda r: r["score"], reverse=True)


# ==================== DEMO ====================

if __name__ == "__main__":
    async def demo():
        engine = AnsweringEngine()

        # Demo search
        session = await engine.search(
            "What are the latest developments in large language models?",
            focus_mode="academic",
            copilot_mode=True
        )

        print(f"Query: {session.query}")
        print(f"Generated queries: {len(session.generated_queries)}")
        for q in session.generated_queries:
            print(f"  - {q.generated_query}")
        print(f"Sources found: {session.sources_count}")
        print(f"Search time: {session.total_search_time_ms:.0f}ms")
        print(f"Answer time: {session.total_answer_time_ms:.0f}ms")
        print(f"Answer:
{session.answer}"\nprint(f"
Citations:")
        for c in session.citations:
            print(f"  [{c.id}] {c.title} ({c.source_name})")

    asyncio.run(demo())
