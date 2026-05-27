# ADR-005: In-Memory State Management (No Redis/Neo4j/FAISS)

## Status
Accepted

## Context
Multi-agent systems need shared state: KV store for config, vector DB for RAG, graph DB for knowledge, temporal store for audit. Standard solutions: Redis ($$$), Neo4j (complex), FAISS (GPU-optimized but external process).

## Decision
Build all state backends in pure Python, in-memory, with optional JSON persistence. No external processes. No network calls.

## Backends

| Backend | File | Lines | Features |
|---|---|---|---|
| RedisLikeStore | `state_management_native.py` | ~300 | Strings, lists, hashes, sets, zsets, pub/sub, streams |
| VectorDB | `state_management_native.py` | ~100 | Cosine similarity, metadata filtering, 128-dim |
| GraphDB | `state_management_native.py` | ~200 | Nodes, edges, BFS, shortest path, Cypher-lite |
| TemporalStore | `state_management_native.py` | ~150 | Events, audit trail, checkpoint/restore |

## Consequences

**Positive:**
- Zero setup. No `docker run redis`. No `pip install neo4j`.
- Sub-microsecond latency (no network hop).
- Deterministic — no external service variance.
- All data structures are Python-native (dicts, sets, deques).

**Negative:**
- No persistence across process restarts (unless `save()` / `load()` called).
- No horizontal scaling — single-process only.
- Memory limit = RAM limit.
- Graph DB uses adjacency lists — O(V+E) but not optimized for billion-node graphs.

## Mitigations
- `save(path)` / `load(path)` for JSON snapshot persistence.
- `TemporalStore.export(path)` for audit trail archival.
- For horizontal scaling: future ADR will define network replication layer.
- For billion-node graphs: document slot-in points untuk Neo4j integration.
- All APIs are interface-compatible with real backends (Redis protocol, Cypher syntax subset).
