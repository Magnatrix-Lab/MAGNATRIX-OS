#!/usr/bin/env python3
"""
Knowledge Ingestion Pipeline for MAGNATRIX-OS
============================================
Auto-crawl URL, parse PDF, extract text, chunking, build knowledge graph
real-time. Pipeline: URL → crawler → parser → chunker → graph → RAG-ready.
Pure stdlib.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations
import json, re, urllib.request, urllib.error, urllib.parse, time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple
from html.parser import HTMLParser


@dataclass
class Document:
    """A parsed document."""
    doc_id: str
    source: str  # URL or file path
    title: str = ""
    content: str = ""
    chunks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    parsed_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class KnowledgeNode:
    """A node in the knowledge graph."""
    node_id: str
    label: str
    node_type: str  # "concept", "entity", "fact", "chunk"
    content: str = ""
    sources: List[str] = field(default_factory=list)
    related: List[str] = field(default_factory=list)  # Related node IDs
    embedding: List[float] = field(default_factory=list)  # Simulated
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HTMLStripper(HTMLParser):
    """Strip HTML tags to extract text."""
    
    def __init__(self) -> None:
        super().__init__()
        self.text = []
        self.skip_tags = {"script", "style", "nav", "footer", "header"}
        self._skip_depth = 0
    
    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str]]) -> None:
        if tag in self.skip_tags:
            self._skip_depth += 1
    
    def handle_endtag(self, tag: str) -> None:
        if tag in self.skip_tags and self._skip_depth > 0:
            self._skip_depth -= 1
    
    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self.text.append(data)
    
    def get_text(self) -> str:
        return " ".join(self.text)


class WebCrawler:
    """Crawl web pages and extract content."""
    
    def __init__(self, timeout: float = 10.0, user_agent: str = "MAGNATRIX-OS/1.0") -> None:
        self.timeout = timeout
        self.user_agent = user_agent
        self.visited: Set[str] = set()
        self._crawl_delay = 1.0
    
    def fetch(self, url: str) -> Optional[str]:
        if url in self.visited:
            return None
        try:
            req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = resp.read().decode("utf-8", errors="ignore")
                self.visited.add(url)
                return data
        except Exception:
            return None
    
    def extract_links(self, html: str, base_url: str) -> List[str]:
        links = re.findall(r'href=["\']([^"\']+)["\']', html)
        absolute = []
        for link in links:
            if link.startswith("http"):
                absolute.append(link)
            elif link.startswith("/"):
                base = urllib.parse.urlparse(base_url)
                absolute.append(f"{base.scheme}://{base.netloc}{link}")
        return absolute
    
    def crawl(self, start_url: str, max_depth: int = 2, max_pages: int = 10) -> List[Document]:
        docs = []
        queue = [(start_url, 0)]
        while queue and len(docs) < max_pages:
            url, depth = queue.pop(0)
            if depth > max_depth or url in self.visited:
                continue
            html = self.fetch(url)
            if html:
                stripper = HTMLStripper()
                stripper.feed(html)
                text = stripper.get_text()
                # Extract title
                title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
                title = title_match.group(1).strip() if title_match else ""
                doc = Document(
                    doc_id=f"doc_{len(docs)}_{int(time.time())}",
                    source=url,
                    title=title,
                    content=text,
                )
                docs.append(doc)
                if depth < max_depth:
                    links = self.extract_links(html, url)
                    for link in links[:5]:
                        queue.append((link, depth + 1))
            time.sleep(self._crawl_delay)
        return docs


class PDFParser:
    """Parse PDF-like text content."""
    
    def parse_text(self, text: str, source: str = "") -> Document:
        """Parse raw text as if from PDF extraction."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        title = lines[0] if lines else ""
        content = "\n".join(lines[1:]) if len(lines) > 1 else ""
        return Document(
            doc_id=f"pdf_{int(time.time())}_{hash(source) % 10000}",
            source=source,
            title=title,
            content=content,
        )
    
    def parse_binary(self, data: bytes, source: str = "") -> Document:
        """Attempt to extract text from binary PDF data."""
        try:
            text = data.decode("utf-8", errors="ignore")
            # Remove PDF structure markers
            text = re.sub(r'[\x00-\x08\x0b-\x1f]', '', text)
            return self.parse_text(text, source)
        except Exception:
            return Document(
                doc_id=f"pdf_err_{int(time.time())}",
                source=source,
                content="[PDF parsing failed]",
            )


class TextChunker:
    """Split text into chunks for RAG."""
    
    def __init__(self, chunk_size: int = 512, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        words = text.split()
        if len(words) <= self.chunk_size:
            return [text]
        chunks = []
        start = 0
        while start < len(words):
            end = min(start + self.chunk_size, len(words))
            chunk = " ".join(words[start:end])
            chunks.append(chunk)
            start += self.chunk_size - self.overlap
        return chunks
    
    def chunk_document(self, doc: Document) -> Document:
        """Chunk a document and return updated document."""
        doc.chunks = self.chunk(doc.content)
        return doc


class KnowledgeGraphBuilder:
    """Build knowledge graph from documents."""
    
    def __init__(self) -> None:
        self.nodes: Dict[str, KnowledgeNode] = {}
        self._node_counter = 0
    
    def _make_id(self, label: str) -> str:
        self._node_counter += 1
        return f"kg_{label[:20]}_{self._node_counter}"
    
    def add_document(self, doc: Document) -> List[KnowledgeNode]:
        """Add a document to the knowledge graph."""
        nodes = []
        # Create document node
        doc_node = KnowledgeNode(
            node_id=self._make_id("doc"),
            label=doc.title or "Untitled",
            node_type="chunk",
            content=doc.content[:500],
            sources=[doc.source],
        )
        self.nodes[doc_node.node_id] = doc_node
        nodes.append(doc_node)
        
        # Extract entities and create nodes
        entities = self._extract_entities(doc.content)
        for entity in entities:
            existing = self._find_node_by_label(entity)
            if existing:
                existing.sources.append(doc.source)
                doc_node.related.append(existing.node_id)
                existing.related.append(doc_node.node_id)
            else:
                entity_node = KnowledgeNode(
                    node_id=self._make_id(entity),
                    label=entity,
                    node_type="entity",
                    sources=[doc.source],
                )
                self.nodes[entity_node.node_id] = entity_node
                doc_node.related.append(entity_node.node_id)
                entity_node.related.append(doc_node.node_id)
                nodes.append(entity_node)
        
        # Extract concepts
        concepts = self._extract_concepts(doc.content)
        for concept in concepts:
            existing = self._find_node_by_label(concept)
            if not existing:
                concept_node = KnowledgeNode(
                    node_id=self._make_id(concept),
                    label=concept,
                    node_type="concept",
                    sources=[doc.source],
                )
                self.nodes[concept_node.node_id] = concept_node
                nodes.append(concept_node)
        
        return nodes
    
    def _extract_entities(self, text: str) -> List[str]:
        """Extract named entities using simple patterns."""
        # Capitalized multi-word phrases
        entities = re.findall(r'\b[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)+\b', text)
        return list(set(entities))[:20]  # Limit to top 20
    
    def _extract_concepts(self, text: str) -> List[str]:
        """Extract key concepts."""
        # Common technical terms
        words = re.findall(r'\b[a-z]+(?:_[a-z]+)+\b|\b[A-Z]{2,}(?:_[A-Z]+)*\b', text.lower())
        freq = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1
        # Return most frequent
        return [w for w, c in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:15]]
    
    def _find_node_by_label(self, label: str) -> Optional[KnowledgeNode]:
        for node in self.nodes.values():
            if node.label.lower() == label.lower():
                return node
        return None
    
    def query(self, concept: str) -> List[KnowledgeNode]:
        """Query knowledge graph for a concept."""
        results = []
        for node in self.nodes.values():
            if concept.lower() in node.label.lower() or concept.lower() in node.content.lower():
                results.append(node)
        return results
    
    def get_graph_stats(self) -> Dict[str, Any]:
        types = {}
        for node in self.nodes.values():
            types[node.node_type] = types.get(node.node_type, 0) + 1
        total_edges = sum(len(n.related) for n in self.nodes.values())
        return {
            "total_nodes": len(self.nodes),
            "total_edges": total_edges,
            "by_type": types,
        }


class KnowledgeIngestionPipeline:
    """Top-level knowledge ingestion pipeline."""
    
    def __init__(self, repo_root: str = "") -> None:
        self.repo_root = repo_root
        self.crawler = WebCrawler()
        self.pdf_parser = PDFParser()
        self.chunker = TextChunker()
        self.graph = KnowledgeGraphBuilder()
        self.documents: List[Document] = []
    
    def ingest_url(self, url: str, max_depth: int = 1) -> List[Document]:
        """Ingest content from a URL."""
        docs = self.crawler.crawl(url, max_depth=max_depth, max_pages=5)
        for doc in docs:
            self.chunker.chunk_document(doc)
            self.graph.add_document(doc)
            self.documents.append(doc)
        return docs
    
    def ingest_text(self, text: str, source: str = "") -> Document:
        """Ingest raw text."""
        doc = self.pdf_parser.parse_text(text, source)
        self.chunker.chunk_document(doc)
        self.graph.add_document(doc)
        self.documents.append(doc)
        return doc
    
    def ingest_pdf_bytes(self, data: bytes, source: str = "") -> Document:
        """Ingest PDF bytes."""
        doc = self.pdf_parser.parse_binary(data, source)
        self.chunker.chunk_document(doc)
        self.graph.add_document(doc)
        self.documents.append(doc)
        return doc
    
    def query(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Query ingested knowledge."""
        # Search in chunks
        results = []
        for doc in self.documents:
            for i, chunk in enumerate(doc.chunks):
                if query.lower() in chunk.lower():
                    results.append({
                        "source": doc.source,
                        "title": doc.title,
                        "chunk_index": i,
                        "content": chunk[:300],
                    })
        # Also search in knowledge graph
        kg_nodes = self.graph.query(query)
        for node in kg_nodes[:top_k]:
            results.append({
                "source": node.sources[0] if node.sources else "",
                "title": node.label,
                "type": node.node_type,
                "content": node.content[:300] if node.content else "",
            })
        return results[:top_k]
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "documents": len(self.documents),
            "total_chunks": sum(len(d.chunks) for d in self.documents),
            "graph": self.graph.get_graph_stats(),
            "crawled_urls": len(self.crawler.visited),
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()
