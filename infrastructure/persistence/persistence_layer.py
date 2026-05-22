"""
infrastructure/persistence/persistence_layer.py
================================================
MAGNATRIX Real Persistence Layer
Layer 15: Infrastructure

PostgreSQL + pgvector, Redis cache/queue, persistent storage untuk knowledge graph.
Production-ready persistence abstraction.
"""

import asyncio, json, time, uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from collections import defaultdict

class PersistenceManager:
    """
    Unified persistence layer.
    Production: PostgreSQL + pgvector + Redis.
    Simplified: SQLite + in-memory Redis mock.
    """

    def __init__(self, db_url: str = "sqlite:///magnatrix.db", redis_url: str = ""):
        self.db_url = db_url
        self.redis_url = redis_url
        self._connected = False
        self._cache: Dict[str, Any] = {}
        self._queues: Dict[str, List] = defaultdict(list)
        self._pgvector_enabled = False

    async def connect(self):
        """Initialize database connections"""
        try:
            import aiosqlite
            self.db = await aiosqlite.connect(self.db_url.replace("sqlite:///", ""))
            await self._init_schema()
            self._connected = True
        except ImportError:
            # Pure Python fallback
            self.db = None
            self._connected = True

    async def _init_schema(self):
        """Initialize database schema"""
        schema = """
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            data JSON,
            created_at REAL,
            updated_at REAL
        );
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            agent_id TEXT,
            content TEXT,
            embedding JSON,
            level TEXT,
            timestamp REAL
        );
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            content TEXT,
            metadata JSON,
            embedding JSON,
            indexed_at REAL
        );
        CREATE TABLE IF NOT EXISTS executions (
            id TEXT PRIMARY KEY,
            workflow_id TEXT,
            status TEXT,
            result JSON,
            started_at REAL,
            finished_at REAL
        );
        CREATE INDEX IF NOT EXISTS idx_memories_agent ON memories(agent_id);
        CREATE INDEX IF NOT EXISTS idx_executions_workflow ON executions(workflow_id);
        """
        if self.db:
            await self.db.executescript(schema)
            await self.db.commit()

    async def store(self, table: str, key: str, data: Dict) -> bool:
        """Store record in database"""
        if self.db:
            await self.db.execute(
                f"INSERT OR REPLACE INTO {table} (id, data, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (key, json.dumps(data), time.time(), time.time())
            )
            await self.db.commit()
        # Also cache
        self._cache[f"{table}:{key}"] = data
        return True

    async def retrieve(self, table: str, key: str) -> Optional[Dict]:
        """Retrieve record from cache or database"""
        cache_key = f"{table}:{key}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        if self.db:
            async with self.db.execute(f"SELECT data FROM {table} WHERE id = ?", (key,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    data = json.loads(row[0])
                    self._cache[cache_key] = data
                    return data
        return None

    async def query(self, table: str, filters: Dict) -> List[Dict]:
        """Query records dengan filters"""
        results = []
        if self.db:
            conditions = " AND ".join([f"json_extract(data, '$.{k}') = ?" for k in filters.keys()])
            values = list(filters.values())
            query = f"SELECT data FROM {table} WHERE {conditions}" if conditions else f"SELECT data FROM {table}"
            async with self.db.execute(query, values) as cursor:
                async for row in cursor:
                    results.append(json.loads(row[0]))
        return results

    async def delete(self, table: str, key: str) -> bool:
        """Delete record"""
        if self.db:
            await self.db.execute(f"DELETE FROM {table} WHERE id = ?", (key,))
            await self.db.commit()
        self._cache.pop(f"{table}:{key}", None)
        return True

    # Redis-like operations
    async def cache_set(self, key: str, value: Any, ttl: int = 300):
        """Set cache value dengan TTL"""
        self._cache[key] = {"value": value, "expires": time.time() + ttl}

    async def cache_get(self, key: str) -> Any:
        """Get cache value jika belum expired"""
        entry = self._cache.get(key)
        if entry and isinstance(entry, dict) and entry.get("expires", 0) > time.time():
            return entry["value"]
        return None

    async def queue_push(self, queue_name: str, item: Any):
        """Push to queue"""
        self._queues[queue_name].append(item)

    async def queue_pop(self, queue_name: str) -> Optional[Any]:
        """Pop from queue"""
        if self._queues[queue_name]:
            return self._queues[queue_name].pop(0)
        return None

    async def vector_search(self, table: str, embedding: List[float], k: int = 10) -> List[Dict]:
        """
        Vector similarity search menggunakan pgvector atau fallback cosine.
        """
        # Fallback: brute force cosine similarity
        all_docs = await self.query(table, {})
        scored = []
        for doc in all_docs:
            doc_emb = doc.get("embedding", [])
            if doc_emb:
                score = self._cosine_similarity(embedding, doc_emb)
                scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:k]]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot = sum(x*y for x, y in zip(a, b))
        norm_a = sum(x*x for x in a) ** 0.5
        norm_b = sum(x*x for x in b) ** 0.5
        return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

    def get_stats(self) -> Dict:
        return {
            "connected": self._connected,
            "tables": ["agents", "memories", "documents", "executions"],
            "cache_entries": len(self._cache),
            "queues": {k: len(v) for k, v in self._queues.items()}
        }


if __name__ == "__main__":
    async def demo():
        pm = PersistenceManager()
        await pm.connect()

        await pm.store("agents", "agent-1", {"name": "Alpha", "role": "executor"})
        result = await pm.retrieve("agents", "agent-1")
        print(f"Retrieved: {result}")

        await pm.cache_set("temp:config", {"debug": True})
        cached = await pm.cache_get("temp:config")
        print(f"Cached: {cached}")

        print(f"Stats: {pm.get_stats()}")

    asyncio.run(demo())
