# ADR-003: Hash-Based Deterministic Embeddings (No numpy)

## Status
Accepted

## Context
RAG (Retrieval-Augmented Generation) requires vector embeddings. Standard approach uses OpenAI embeddings or sentence-transformers (which requires torch, numpy, scipy — hundreds of MB).

## Decision
Implement deterministic hash-based embeddings using SHA-256. Fixed 128-dimensional vectors generated from text content. Normalized to unit length for cosine similarity.

## Algorithm
```python
def embed(text: str) -> List[float]:
    h = hashlib.sha256(text.encode()).digest()
    vec = []
    for i in range(128):
        val = (h[i % 32] + i * 7) % 200 - 100
        vec.append(val / 100.0)
    # L2 normalize
    mag = sum(x * x for x in vec) ** 0.5
    return [x / mag for x in vec]
```

## Consequences

**Positive:**
- Zero dependencies. No torch, no numpy, no transformers.
- Deterministic: same text always produces same embedding.
- Fast: pure Python, no model loading latency.
- Works for exact-match and near-match retrieval.

**Negative:**
- Not semantically meaningful like BERT embeddings.
- Cannot capture nuanced semantic similarity (synonyms, paraphrases).
- Dimension limited to 128 (vs 768/1024/1536 for transformer models).

## Mitigations
- For production semantic search, slot in real embeddings by replacing `HashEmbedding.embed()`.
- Hash embeddings are sufficient for: keyword matching, document deduplication, coarse clustering.
- BM25-style reranking (in `document_agent_native.py`) compensates for semantic weakness.
