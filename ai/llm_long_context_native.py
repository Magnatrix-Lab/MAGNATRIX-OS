"""Long Context Handler — Hierarchical summarization, sliding window, recursive chunking, context stitching.

Modul ini menyediakan:
- ContextChunker untuk recursive document chunking
- HierarchicalSummarizer untuk multi-level summary
- SlidingWindow untuk sliding window attention simulation
- ContextStitcher untuk stitching chunks back together
- TokenBudgetManager untuk managing token budget across context

Arsitektur: Document → Chunk → Summarize → Stitch → (Repeat / Output)
"""

from __future__ import annotations

import json
import time
import uuid
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class ChunkStrategy(Enum):
    FIXED = auto()
    PARAGRAPH = auto()
    SENTENCE = auto()
    SEMANTIC = auto()
    RECURSIVE = auto()


@dataclass
class Chunk:
    """Document chunk."""
    chunk_id: str
    content: str
    start_pos: int
    end_pos: int
    tokens: int = 0
    level: int = 0
    summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def estimate_tokens(self) -> int:
        if self.tokens == 0:
            self.tokens = len(self.content.split()) + len(self.content) // 4
        return self.tokens


@dataclass
class SummaryNode:
    """Node in hierarchical summary tree."""
    node_id: str
    content: str
    level: int
    children: List[str] = field(default_factory=list)
    parent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextChunker:
    """Chunk documents into manageable pieces."""

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str, strategy: ChunkStrategy = ChunkStrategy.PARAGRAPH) -> List[Chunk]:
        if strategy == ChunkStrategy.FIXED:
            return self._fixed_chunk(text)
        elif strategy == ChunkStrategy.PARAGRAPH:
            return self._paragraph_chunk(text)
        elif strategy == ChunkStrategy.SENTENCE:
            return self._sentence_chunk(text)
        elif strategy == ChunkStrategy.RECURSIVE:
            return self._recursive_chunk(text)
        else:
            return self._fixed_chunk(text)

    def _fixed_chunk(self, text: str) -> List[Chunk]:
        chunks = []
        pos = 0
        chunk_id = 0
        while pos < len(text):
            end = min(pos + self.chunk_size, len(text))
            if end < len(text):
                # Find word boundary
                while end > pos and text[end] not in " \n":
                    end -= 1
            content = text[pos:end]
            chunks.append(Chunk(
                chunk_id=f"chunk-{chunk_id}",
                content=content,
                start_pos=pos,
                end_pos=end
            ))
            pos = end - self.overlap if end < len(text) else end
            chunk_id += 1
        return chunks

    def _paragraph_chunk(self, text: str) -> List[Chunk]:
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
        chunks = []
        current = ""
        current_pos = 0
        chunk_id = 0
        for para in paragraphs:
            if len(current) + len(para) > self.chunk_size and current:
                chunks.append(Chunk(
                    chunk_id=f"chunk-{chunk_id}",
                    content=current,
                    start_pos=current_pos,
                    end_pos=current_pos + len(current)
                ))
                current_pos += len(current)
                current = para
            else:
                current += ("\n\n" if current else "") + para
        if current:
            chunks.append(Chunk(
                chunk_id=f"chunk-{chunk_id}",
                content=current,
                start_pos=current_pos,
                end_pos=current_pos + len(current)
            ))
        return chunks

    def _sentence_chunk(self, text: str) -> List[Chunk]:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current = ""
        current_pos = 0
        chunk_id = 0
        for sent in sentences:
            if len(current) + len(sent) > self.chunk_size and current:
                chunks.append(Chunk(
                    chunk_id=f"chunk-{chunk_id}",
                    content=current,
                    start_pos=current_pos,
                    end_pos=current_pos + len(current)
                ))
                current_pos += len(current)
                current = sent
            else:
                current += (" " if current else "") + sent
        if current:
            chunks.append(Chunk(
                chunk_id=f"chunk-{chunk_id}",
                content=current,
                start_pos=current_pos,
                end_pos=current_pos + len(current)
            ))
        return chunks

    def _recursive_chunk(self, text: str, level: int = 0) -> List[Chunk]:
        if len(text) <= self.chunk_size:
            return [Chunk(
                chunk_id=f"chunk-{level}-0",
                content=text,
                start_pos=0,
                end_pos=len(text),
                level=level
            )]
        mid = len(text) // 2
        # Find word boundary
        while mid > 0 and text[mid] not in " \n":
            mid -= 1
        left = self._recursive_chunk(text[:mid], level + 1)
        right = self._recursive_chunk(text[mid:], level + 1)
        for r in right:
            r.start_pos += mid
            r.end_pos += mid
        return left + right


class HierarchicalSummarizer:
    """Create multi-level summaries."""

    def __init__(self, summarizer_fn: Optional[Callable[[str], str]] = None):
        self.summarizer_fn = summarizer_fn or self._default_summarizer
        self._nodes: Dict[str, SummaryNode] = {}

    def summarize(self, chunks: List[Chunk], levels: int = 3) -> SummaryNode:
        # Create leaf nodes
        leaves = []
        for chunk in chunks:
            node = SummaryNode(
                node_id=chunk.chunk_id,
                content=chunk.content,
                level=0
            )
            self._nodes[node.node_id] = node
            leaves.append(node)

        # Build hierarchy bottom-up
        current_level = leaves
        for level in range(1, levels):
            if len(current_level) <= 1:
                break
            next_level = []
            group_size = max(2, len(current_level) // max(1, levels - level))
            for i in range(0, len(current_level), group_size):
                group = current_level[i:i+group_size]
                combined = " ".join(n.content for n in group)
                summary = self.summarizer_fn(combined)
                parent = SummaryNode(
                    node_id=f"level{level}-{i//group_size}",
                    content=summary,
                    level=level,
                    children=[n.node_id for n in group]
                )
                self._nodes[parent.node_id] = parent
                for child in group:
                    child.parent = parent.node_id
                next_level.append(parent)
            current_level = next_level

        return current_level[0] if current_level else leaves[0]

    def _default_summarizer(self, text: str) -> str:
        # Simple summarization: first sentence + word count
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) <= 2:
            return text
        return f"[Summary: {len(sentences)} sentences, {len(text)} chars] " + sentences[0][:100] + "..."

    def get_tree(self, root_id: str) -> Dict[str, Any]:
        node = self._nodes.get(root_id)
        if not node:
            return {}
        return {
            "id": node.node_id,
            "content": node.content[:100] + "..." if len(node.content) > 100 else node.content,
            "level": node.level,
            "children": [self.get_tree(cid) for cid in node.children]
        }

    def get_path_to_leaf(self, leaf_id: str) -> List[SummaryNode]:
        path = []
        current = self._nodes.get(leaf_id)
        while current:
            path.append(current)
            if current.parent:
                current = self._nodes.get(current.parent)
            else:
                break
        return list(reversed(path))


class SlidingWindow:
    """Simulate sliding window over long context."""

    def __init__(self, window_size: int = 1024, stride: int = 512):
        self.window_size = window_size
        self.stride = stride

    def slide(self, tokens: List[str]) -> List[Tuple[int, int, List[str]]]:
        windows = []
        start = 0
        while start < len(tokens):
            end = min(start + self.window_size, len(tokens))
            window = tokens[start:end]
            windows.append((start, end, window))
            start += self.stride
            if end >= len(tokens):
                break
        return windows

    def process_with_overlap(self, text: str, processor: Callable[[str], str]) -> List[str]:
        chunks = []
        pos = 0
        while pos < len(text):
            end = min(pos + self.window_size, len(text))
            chunk = text[pos:end]
            result = processor(chunk)
            chunks.append(result)
            pos += self.stride
            if end >= len(text):
                break
        return chunks

    def merge_windows(self, windows: List[str], overlap_size: int = 50) -> str:
        if not windows:
            return ""
        result = windows[0]
        for window in windows[1:]:
            # Find overlap
            if overlap_size > 0 and len(result) >= overlap_size and len(window) >= overlap_size:
                if result[-overlap_size:] == window[:overlap_size]:
                    result += window[overlap_size:]
                else:
                    result += "\n" + window
            else:
                result += "\n" + window
        return result


class ContextStitcher:
    """Stitch chunks back together with smooth transitions."""

    def __init__(self):
        self._transitions: List[str] = []

    def stitch(self, chunks: List[Chunk], summaries: Optional[List[str]] = None) -> str:
        if not chunks:
            return ""
        parts = []
        for i, chunk in enumerate(chunks):
            parts.append(chunk.content)
            if summaries and i < len(summaries):
                parts.append(f"[Summary: {summaries[i]}]")
            if i < len(chunks) - 1:
                parts.append(self._transition(chunk, chunks[i + 1]))
        return "\n\n".join(parts)

    def _transition(self, from_chunk: Chunk, to_chunk: Chunk) -> str:
        # Find overlap or create bridge
        overlap = self._find_overlap(from_chunk.content, to_chunk.content)
        if overlap:
            return f"[Continue from: {overlap[:50]}...]"
        return "[Context continues...]"

    def _find_overlap(self, a: str, b: str, min_len: int = 10) -> Optional[str]:
        for length in range(min(min_len * 3, len(a), len(b)), min_len - 1, -1):
            if a[-length:] == b[:length]:
                return a[-length:]
        return None


class TokenBudgetManager:
    """Manage token budget across context components."""

    def __init__(self, total_budget: int = 4096, system_reserve: int = 200, response_reserve: int = 1000):
        self.total_budget = total_budget
        self.system_reserve = system_reserve
        self.response_reserve = response_reserve
        self.available = total_budget - system_reserve - response_reserve
        self._allocations: Dict[str, int] = {}

    def allocate(self, component: str, requested: int) -> int:
        used = sum(self._allocations.values())
        remaining = self.available - used
        granted = min(requested, remaining)
        self._allocations[component] = granted
        return granted

    def deallocate(self, component: str) -> int:
        return self._allocations.pop(component, 0)

    def get_usage(self) -> Dict[str, Any]:
        used = sum(self._allocations.values())
        return {
            "total_budget": self.total_budget,
            "available": self.available,
            "used": used,
            "remaining": self.available - used,
            "allocations": self._allocations,
        }

    def optimize(self, chunks: List[Chunk], priority_fn: Optional[Callable[[Chunk], float]] = None) -> List[Chunk]:
        """Select chunks that fit within budget, prioritized."""
        priority_fn = priority_fn or (lambda c: 1.0 / (c.level + 1))
        scored = [(priority_fn(c), c) for c in chunks]
        scored.sort(reverse=True, key=lambda x: x[0])
        selected = []
        total_tokens = 0
        for _, chunk in scored:
            tokens = chunk.estimate_tokens()
            if total_tokens + tokens <= self.available:
                selected.append(chunk)
                total_tokens += tokens
        return selected


class LongContextHandler:
    """End-to-end long context handler."""

    def __init__(self, chunk_size: int = 500, overlap: int = 50, window_size: int = 1024):
        self.chunker = ContextChunker(chunk_size, overlap)
        self.summarizer = HierarchicalSummarizer()
        self.window = SlidingWindow(window_size)
        self.stitcher = ContextStitcher()
        self.budget = TokenBudgetManager()

    def process(self, text: str, strategy: ChunkStrategy = ChunkStrategy.PARAGRAPH,
                max_levels: int = 3) -> Dict[str, Any]:
        chunks = self.chunker.chunk(text, strategy)
        root = self.summarizer.summarize(chunks, max_levels)
        tree = self.summarizer.get_tree(root.node_id)
        return {
            "chunks": len(chunks),
            "total_tokens": sum(c.estimate_tokens() for c in chunks),
            "hierarchy": tree,
            "root_summary": root.content[:200] if len(root.content) > 200 else root.content,
        }

    def slide_and_process(self, text: str, processor: Callable[[str], str]) -> str:
        chunks = self.chunker.chunk(text, ChunkStrategy.FIXED)
        results = []
        for chunk in chunks:
            result = processor(chunk.content)
            results.append(result)
        return self.stitcher.stitch(chunks, results)

    def optimize_for_budget(self, text: str, budget: int = 4096) -> List[Chunk]:
        self.budget = TokenBudgetManager(budget)
        chunks = self.chunker.chunk(text, ChunkStrategy.PARAGRAPH)
        return self.budget.optimize(chunks)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "chunk_size": self.chunker.chunk_size,
            "overlap": self.chunker.overlap,
            "window_size": self.window.window_size,
            "stride": self.window.stride,
        }


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("LONG CONTEXT HANDLER DEMO")
    print("=" * 70)

    # Create long text
    long_text = "\n\n".join([
        f"Paragraph {i}: This is an important section about topic {i}. "
        f"It contains detailed information that needs to be processed by the model. "
        f"The content discusses various aspects including technical details, implications, and future directions."
        for i in range(20)
    ])

    handler = LongContextHandler(chunk_size=300, overlap=30)

    # 1. Chunking strategies
    print("\n[1] Chunking Strategies")
    for strategy in [ChunkStrategy.FIXED, ChunkStrategy.PARAGRAPH, ChunkStrategy.SENTENCE, ChunkStrategy.RECURSIVE]:
        chunks = handler.chunker.chunk(long_text[:1000], strategy)
        print(f"  {strategy.name}: {len(chunks)} chunks")
        if chunks:
            print(f"    First chunk: {len(chunks[0].content)} chars, ~{chunks[0].estimate_tokens()} tokens")

    # 2. Hierarchical summarization
    print("\n[2] Hierarchical Summarization")
    chunks = handler.chunker.chunk(long_text, ChunkStrategy.PARAGRAPH)
    result = handler.process(long_text, ChunkStrategy.PARAGRAPH, max_levels=3)
    print(f"  Chunks: {result['chunks']}")
    print(f"  Total tokens: {result['total_tokens']}")
    print(f"  Root summary: {result['root_summary'][:80]}...")

    # 3. Tree structure
    print("\n[3] Hierarchy Tree")
    tree = result['hierarchy']
    if tree:
        def print_tree(node, depth=0):
            indent = "  " * depth
            print(f"{indent}[L{node.get('level', 0)}] {node.get('content', '')[:50]}...")
            for child in node.get('children', []):
                print_tree(child, depth + 1)
        print_tree(tree)

    # 4. Sliding window
    print("\n[4] Sliding Window")
    tokens = long_text.split()
    windows = handler.window.slide(tokens[:500])
    print(f"  Tokens: {len(tokens[:500])}")
    print(f"  Windows: {len(windows)}")
    for start, end, window in windows[:3]:
        print(f"    Window {start}-{end}: {len(window)} tokens")

    # 5. Context stitching
    print("\n[5] Context Stitching")
    chunks = handler.chunker.chunk(long_text[:500], ChunkStrategy.FIXED)
    stitched = handler.stitcher.stitch(chunks)
    print(f"  Chunks: {len(chunks)}")
    print(f"  Stitched length: {len(stitched)} chars")

    # 6. Token budget
    print("\n[6] Token Budget Management")
    budget = TokenBudgetManager(total_budget=2000, system_reserve=100, response_reserve=300)
    budget.allocate("system", 100)
    budget.allocate("history", 500)
    budget.allocate("context", 800)
    print(f"  Budget usage: {budget.get_usage()}")

    # 7. Budget optimization
    print("\n[7] Budget Optimization")
    optimized = handler.optimize_for_budget(long_text, budget=800)
    print(f"  Selected chunks: {len(optimized)}")
    total = sum(c.estimate_tokens() for c in optimized)
    print(f"  Total tokens: {total}")

    # 8. Stats
    print("\n[8] Handler Stats")
    print(f"  {handler.get_stats()}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
